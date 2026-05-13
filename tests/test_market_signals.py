"""Tests for market signal scorers."""

import pytest
from analysis.market_signals import (
    compute_monetization_score,
    compute_solution_simplicity,
    compute_market_size_score,
    compute_lienclear_relevance,
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
