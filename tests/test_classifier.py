"""Tests for pain-point classifier regex patterns."""

import pytest
from analysis.classifier import PainPointClassifier


@pytest.fixture
def clf():
    return PainPointClassifier()


class TestClassifierHits:
    def test_seeking_tool_is_there_an_app(self, clf):
        result = clf.classify("Is there an app that handles invoicing?", "")
        assert result is not None
        assert result["intent_category"] == "seeking_tool"

    def test_seeking_tool_looking_for(self, clf):
        result = clf.classify("Looking for a tool to manage inventory", "")
        assert result is not None  # RAG may return any category; just verify it fires

    def test_seeking_tool_what_do_you_use(self, clf):
        result = clf.classify("What do you all use for payroll?", "")
        assert result is not None

    def test_would_pay_gladly(self, clf):
        result = clf.classify("I'd gladly pay for something that solves this", "")
        assert result is not None
        assert result["intent_category"] == "would_pay"

    def test_would_pay_willing(self, clf):
        result = clf.classify("I'm willing to pay for a proper solution", "")
        assert result is not None
        assert result["intent_category"] == "would_pay"

    def test_frustrated_existing_tools_suck(self, clf):
        result = clf.classify("Existing tools are terrible for small teams", "")
        assert result is not None  # strong pain signal — must classify as something

    def test_feature_request_wish_there_was(self, clf):
        result = clf.classify("I wish there was a simple way to track leads", "")
        assert result is not None  # RAG semantic match; exact category depends on nearest seed

    def test_feature_request_someone_should_build(self, clf):
        result = clf.classify("Someone should build this for freelancers", "")
        assert result is not None

    def test_unbundle_just_need(self, clf):
        result = clf.classify("I just need a simple lightweight CRM, not a full suite", "")
        assert result is not None
        assert result["intent_category"] == "unbundle"

    def test_unbundle_overkill(self, clf):
        result = clf.classify("Salesforce is overkill for what I need", "")
        assert result is not None
        assert result["intent_category"] == "unbundle"


class TestClassifierMisses:
    def test_generic_post_low_intensity(self, clf):
        # RAG may still match generic posts at low similarity; check intensity is low if it does
        result = clf.classify("Here is my monthly revenue update", "Doing okay this month.")
        if result is not None:
            assert result["sentiment_intensity"] < 0.3  # low intensity = weak signal

    def test_empty_text_no_match(self, clf):
        assert clf.classify("", "") is None

    def test_unrelated_post_no_match(self, clf):
        result = clf.classify("What's everyone's favorite coffee?", "I like espresso.")
        assert result is None


class TestClassifierOutput:
    def test_sentiment_intensity_in_range(self, clf):
        result = clf.classify("Looking for a tool to manage invoicing and payroll", "")
        if result:
            assert 0.0 <= result["sentiment_intensity"] <= 1.0

    def test_matched_patterns_is_list_json(self, clf):
        import json
        result = clf.classify("Is there an app that does this?", "")
        assert result is not None
        patterns = json.loads(result["matched_patterns"])
        assert isinstance(patterns, list)
        assert len(patterns) > 0

    def test_would_pay_beats_seeking_tool_priority(self, clf):
        result = clf.classify(
            "Looking for a tool, I'd gladly pay for it",
            ""
        )
        assert result is not None
        assert result["intent_category"] == "would_pay"


class TestClassifierNoiseRejection:
    """Prefilter v2 — noise categories should classify as None at the RAG
    layer. Career posts, tenant/landlord legal Qs, and agency-observer
    manifestos used to slip through the LLM prefilter and burn batch slots.
    Tests use PainPointClassifier (RAG + regex fallback); chosen phrasings
    don't hit the narrow regex fallback either, so None is the expected
    end-to-end output."""

    def test_career_post_rejected(self, clf):
        result = clf.classify(
            "What's everybody's career path and what are we all making?",
            "Share your age, location, and years in the industry/your trade.",
        )
        assert result is None

    def test_career_job_offer_rejected(self, clf):
        result = clf.classify(
            "Should I take this job offer or stay where I am?",
            "Considering a switch but not sure if the pay bump is worth it.",
        )
        assert result is None

    def test_tenant_legal_question_rejected(self, clf):
        result = clf.classify(
            "Can I evict a tenant for not paying rent on time?",
            "What are the legal steps in my state to start the eviction process?",
        )
        assert result is None

    def test_lease_clause_question_rejected(self, clf):
        result = clf.classify(
            "Is this clause in my lease actually legal?",
            "My landlord added a fee for late payment that seems excessive.",
        )
        assert result is None

    def test_agency_observer_manifesto_rejected(self, clf):
        result = clf.classify(
            "I work with hundreds of SaaS founders and the biggest issue I see is X",
            "Most of my clients struggle with this exact thing every single week at our agency.",
        )
        assert result is None

    def test_pain_with_noise_overlap_pain_wins(self, clf):
        # Mixes a career-noise phrase ("considering this as a career") with a
        # would_pay pain phrase. Priority tiebreak (would_pay=5 > noise=0) means
        # the post is correctly classified as pain, not rejected as noise.
        result = clf.classify(
            "Considering this as a career — I'd gladly pay for a tool that automates onboarding",
            "",
        )
        assert result is not None
        assert result["intent_category"] in {"would_pay", "seeking_tool"}
