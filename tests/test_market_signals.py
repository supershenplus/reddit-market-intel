"""Tests for market signal scorers."""

import pytest
from analysis.market_signals import (
    compute_monetization_score,
    compute_solution_simplicity,
    compute_market_size_score,
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
