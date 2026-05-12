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
        assert result is not None
        assert result["intent_category"] == "seeking_tool"

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
        assert result is not None
        assert result["intent_category"] == "frustrated"

    def test_feature_request_wish_there_was(self, clf):
        result = clf.classify("I wish there was a simple way to track leads", "")
        assert result is not None
        assert result["intent_category"] == "feature_request"

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
    def test_generic_post_no_match(self, clf):
        result = clf.classify("Here is my monthly revenue update", "Doing okay this month.")
        assert result is None

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
