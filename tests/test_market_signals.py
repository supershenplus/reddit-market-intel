"""Tests for market signal scorers."""

import pytest
from analysis.market_signals import (
    compute_monetization_score,
    compute_solution_simplicity,
    compute_market_size_score,
    compute_lienclear_relevance,
    classify_lienclear_phase,
)


class TestMonetizationScore:
    def test_would_pay_keyword_raises_score(self):
        s = compute_monetization_score("I would pay for this", "", "SaaS")
        assert s > 0.5

    def test_willing_to_pay_raises_score(self):
        s = compute_monetization_score("willing to pay for a solution", "", "smallbusiness")
        assert s > 0.5

    def test_free_keyword_lowers_score(self):
        s = compute_monetization_score("Looking for free open source tool", "", "productivity")
        assert s < 0.5

    def test_high_monetization_subreddit_boosts(self):
        base = compute_monetization_score("I need a tool", "", "productivity")
        high = compute_monetization_score("I need a tool", "", "smallbusiness")
        assert high > base

    def test_low_monetization_subreddit_reduces(self):
        base = compute_monetization_score("I need a tool", "", "SaaS")
        low = compute_monetization_score("I need a tool", "", "digitalnomad")
        assert low < base

    def test_score_in_range(self):
        s = compute_monetization_score("some random title", "some body", "Entrepreneur")
        assert 0.0 <= s <= 1.0

    def test_empty_text_returns_valid_score(self):
        s = compute_monetization_score("", "", "startups")
        assert 0.0 <= s <= 1.0


class TestSolutionSimplicity:
    def test_static_site_high_simplicity(self):
        s = compute_solution_simplicity("Need a simple static site for this", "")
        assert s > 0.5

    def test_directory_high_simplicity(self):
        s = compute_solution_simplicity("A directory of local services", "")
        assert s > 0.5

    def test_real_time_low_simplicity(self):
        s = compute_solution_simplicity("Need real-time collaboration features", "")
        assert s < 0.5

    def test_multi_tenant_low_simplicity(self):
        s = compute_solution_simplicity("Multi-tenant enterprise SaaS", "")
        assert s < 0.5

    def test_neutral_text_near_midpoint(self):
        s = compute_solution_simplicity("Looking for a tool to track expenses", "")
        assert 0.3 <= s <= 0.7

    def test_score_in_range(self):
        s = compute_solution_simplicity("any title", "any body")
        assert 0.0 <= s <= 1.0

    def test_score_never_negative(self):
        s = compute_solution_simplicity(
            "real-time multi-tenant enterprise microservices API sync machine learning",
            "complex scalable infra",
        )
        assert s >= 0.0

    def test_score_never_exceeds_one(self):
        s = compute_solution_simplicity(
            "static site directory aggregator newsletter simple form one-page no-code",
            "",
        )
        assert s <= 1.0


class TestMarketSizeScore:
    def test_large_subreddit_high_score(self):
        s = compute_market_size_score(subscribers=5_000_000, cross_sub_count=1)
        assert s >= 0.5

    def test_small_subreddit_low_score(self):
        s = compute_market_size_score(subscribers=10_000, cross_sub_count=1)
        assert s < 0.3

    def test_zero_subscribers_returns_default(self):
        s = compute_market_size_score(subscribers=0, cross_sub_count=1)
        assert 0.0 <= s <= 1.0

    def test_cross_sub_count_boosts_score(self):
        single = compute_market_size_score(subscribers=100_000, cross_sub_count=1)
        multi = compute_market_size_score(subscribers=100_000, cross_sub_count=4)
        assert multi > single

    def test_cross_sub_bonus_capped(self):
        many = compute_market_size_score(subscribers=100_000, cross_sub_count=100)
        assert many <= 1.0

    def test_score_in_range(self):
        s = compute_market_size_score(subscribers=500_000, cross_sub_count=2)
        assert 0.0 <= s <= 1.0


class TestLienclearRelevance:
    def test_off_topic_post_scores_zero(self):
        r = compute_lienclear_relevance("How do I bake bread", "any body", "Cooking")
        assert r["score"] == 0.0
        assert r["domain_hit"] is False

    def test_domain_keyword_drives_signal(self):
        r = compute_lienclear_relevance(
            "Need a lien waiver tool", "tired of doing them in Excel", "Construction"
        )
        assert r["domain_hit"] is True
        assert r["score"] > 0.3

    def test_aia_pay_app_recognized_as_domain(self):
        r = compute_lienclear_relevance(
            "Anyone have a good AIA G702 template?", "", "Construction"
        )
        assert r["domain_hit"] is True

    def test_beachhead_state_boosts_score(self):
        r_ca = compute_lienclear_relevance(
            "California lien waiver question", "Civ Code 8132", "Construction"
        )
        r_off = compute_lienclear_relevance(
            "Generic lien waiver question", "", "Construction"
        )
        assert r_ca["score"] > r_off["score"]
        assert any("California" in s or "CA" == s for s in r_ca["states"])

    def test_statutory_state_partial_boost(self):
        r_az = compute_lienclear_relevance(
            "Arizona lien waiver requirements", "", "Construction"
        )
        r_ca = compute_lienclear_relevance(
            "California lien waiver requirements", "", "Construction"
        )
        assert r_ca["score"] > r_az["score"]
        assert r_az["score"] > 0

    def test_dollar_anchor_detected(self):
        r = compute_lienclear_relevance(
            "Would pay $99/month for a lien waiver tool", "", "Construction"
        )
        assert len(r["dollar_anchors"]) >= 1

    def test_icp_role_office_manager_keeps_score(self):
        r = compute_lienclear_relevance(
            "As the office manager I'm tired of doing lien waivers in Word",
            "we have 12 active projects",
            "Construction",
        )
        assert r["role"] == "office_manager"
        assert r["score"] > 0.3

    def test_gc_role_downweights_score(self):
        r_gc = compute_lienclear_relevance(
            "As a GC I require lien waivers from all my subs",
            "California project",
            "ConstructionManagers",
        )
        r_sub = compute_lienclear_relevance(
            "I own a small plumbing company and lien waivers are killing me",
            "California project",
            "Plumbing",
        )
        # Same domain hit + state, but GC role multiplier should knock the score down.
        assert r_gc["role"] == "gc"
        assert r_gc["score"] < r_sub["score"]

    def test_homeowner_downweighted(self):
        r = compute_lienclear_relevance(
            "Homeowner here, contractor I hired wants me to sign a lien waiver",
            "California",
            "HomeImprovement",
        )
        assert r["role"] == "homeowner"
        assert r["score"] < 0.3

    def test_competitor_mention_captured(self):
        r = compute_lienclear_relevance(
            "Procore is way too expensive, looking at Levelset alternatives",
            "we're a small sub",
            "Construction",
        )
        assert "Procore" in r["competitor_mentions"]
        assert "Levelset" in r["competitor_mentions"]

    def test_score_in_range(self):
        r = compute_lienclear_relevance(
            "California lien waiver $99/mo Procore office manager AIA G702",
            "lots of signals",
            "Construction",
        )
        assert 0.0 <= r["score"] <= 1.0

    def test_empty_text_returns_zero(self):
        r = compute_lienclear_relevance("", "", "Construction")
        assert r["score"] == 0.0
        assert r["states"] == []
        assert r["competitor_mentions"] == []

    def test_returns_required_keys(self):
        r = compute_lienclear_relevance("test", "test", "Construction")
        for k in ("score", "states", "dollar_anchors", "role", "competitor_mentions", "domain_hit"):
            assert k in r

    def test_no_domain_hit_caps_below_threshold(self):
        # State + role + dollar + competitor coincidences without any lien/AIA/
        # waiver keyword must not clear the 0.30 export threshold.
        r = compute_lienclear_relevance(
            "Texas $99/month office manager Procore stuff",
            "we run a small business with bookkeeping needs",
            "smallbusiness",
        )
        assert r["domain_hit"] is False
        assert r["score"] <= 0.20

    def test_domain_hit_unlocks_full_score(self):
        # Same signals but a real domain keyword present — score should jump
        # well past the gated cap.
        r = compute_lienclear_relevance(
            "Texas lien waiver $99/month office manager Procore stuff",
            "we run a small business with bookkeeping needs",
            "smallbusiness",
        )
        assert r["domain_hit"] is True
        assert r["score"] >= 0.40

    def test_diy_evidence_excel_spreadsheet(self):
        r = compute_lienclear_relevance(
            "Looking for a better way than my Excel spreadsheet for lien waivers",
            "I built a spreadsheet to track all the waivers but it's getting out of hand",
            "Construction",
        )
        assert r["diy_evidence"]
        assert any("spreadsheet" in d.lower() for d in r["diy_evidence"])

    def test_diy_evidence_zapier(self):
        r = compute_lienclear_relevance(
            "Lien waiver automation with Zapier?",
            "Using Zapier to glue DocuSign + QuickBooks for waivers",
            "Construction",
        )
        assert any("Zapier" in d for d in r["diy_evidence"])

    def test_diy_evidence_manual_workflow(self):
        r = compute_lienclear_relevance(
            "Tired of manually creating lien waivers",
            "I manually fill out each waiver every month, hours of work",
            "Construction",
        )
        assert r["diy_evidence"]
        assert any("manually" in d.lower() for d in r["diy_evidence"])

    def test_diy_evidence_empty_when_absent(self):
        r = compute_lienclear_relevance(
            "Simple lien waiver question", "What form does CA require?", "Construction",
        )
        assert r["diy_evidence"] == []

    def test_urgency_blocking_money(self):
        r = compute_lienclear_relevance(
            "GC won't pay, blocking me from making payroll",
            "30 days overdue, cash flow getting tight",
            "Plumbing",
        )
        assert r["urgency"], "expected urgency facets to capture this post"
        joined = " ".join(r["urgency"]).lower()
        assert "blocking" in joined or "won't pay" in joined or "cash flow" in joined

    def test_urgency_dso_jargon(self):
        r = compute_lienclear_relevance(
            "Our DSO is creeping past 60 days late on AIA pay apps",
            "", "Construction",
        )
        assert any("DSO" in u for u in r["urgency"])

    def test_urgency_empty_when_chill(self):
        r = compute_lienclear_relevance(
            "Curious about lien waiver best practices someday", "", "Construction",
        )
        assert r["urgency"] == []

    def test_frequency_recurring_pain(self):
        r = compute_lienclear_relevance(
            "Every month we redo the lien waiver dance for each project",
            "Constantly hunting down signed waivers",
            "Construction",
        )
        assert r["frequency"], "expected recurring-pain frequency markers"
        joined = " ".join(r["frequency"]).lower()
        assert "every month" in joined or "constantly" in joined

    def test_frequency_empty_when_one_off(self):
        r = compute_lienclear_relevance(
            "One-time question about a specific lien waiver form", "", "Construction",
        )
        assert r["frequency"] == []

    def test_urgency_and_frequency_independent_of_score(self):
        # Both facets are diagnostic-only — adding them should not change score.
        r_with = compute_lienclear_relevance(
            "Lien waiver template", "every month, GC won't pay, blocking us",
            "Construction",
        )
        r_without = compute_lienclear_relevance(
            "Lien waiver template", "", "Construction",
        )
        assert r_with["score"] == r_without["score"]

    def test_diy_evidence_does_not_perturb_score(self):
        # DIY hits are a diagnostic facet, not a scoring component. A post
        # with DIY signal should score the same as one without (modulo the
        # actual lien/state/role signals).
        r_with = compute_lienclear_relevance(
            "Lien waiver template", "I built a spreadsheet for our pay apps", "Construction",
        )
        r_without = compute_lienclear_relevance(
            "Lien waiver template", "", "Construction",
        )
        assert r_with["score"] == r_without["score"]

    def test_phase_1_lien_waiver_only(self):
        # Waiver/lien-only post is Phase 1 (foundational layer).
        assert classify_lienclear_phase(
            "Need a lien waiver template", "California conditional progress waiver"
        ) == 1

    def test_phase_2_aia_pay_app(self):
        assert classify_lienclear_phase(
            "AIA G702 pay app rejected by GC",
            "schedule of values doesn't tie out",
        ) == 2

    def test_phase_3_docusign_or_gc_portal(self):
        assert classify_lienclear_phase(
            "Anyone integrate DocuSign with lien waiver workflow?", "",
        ) == 3
        assert classify_lienclear_phase(
            "GC portal access for subs", "submit pay apps through their portal"
        ) == 3

    def test_highest_phase_wins_on_multi_hit(self):
        # Waiver (Phase 1) + G702 (Phase 2) — should classify as Phase 2.
        assert classify_lienclear_phase(
            "Lien waiver and AIA G702 workflow",
            "we generate the waiver after the pay app is approved",
        ) == 2

    def test_no_phase_pattern_returns_none(self):
        assert classify_lienclear_phase("Bread baking tips", "yeast and flour") is None

    def test_empty_text_returns_none(self):
        assert classify_lienclear_phase("", "") is None

    def test_bookkeeping_texas_role_does_not_leak(self):
        # Regression for the 2026-05-12 smoke test false positive:
        # Bookkeeping/Texas/bookkeeper-role post scored 0.32 with 0% domain hits.
        r = compute_lienclear_relevance(
            "If you build it, they won't come",
            "as a bookkeeper in Texas I see this all the time",
            "Bookkeeping",
        )
        assert r["domain_hit"] is False
        assert r["score"] < 0.30
