"""Unit tests for analysis/niche_scorer.py.

Covers the headline correctness invariants:
- is_pain_point=0 filter (the critical bug guard — LLM populates facet fields
  even for vetoed posts, unfiltered aggregation would contaminate scores)
- Confidence clipping bounds
- Adaptive faceted-enough threshold + effective-N floor
- Fallback path returns the same shape as the faceted path
- Best-label-facet picks highest-confidence
- Each individual signal contribution direction
"""

import json
import math

import pytest

from analysis import niche_scorer
from analysis.niche_scorer import (
    BREAKDOWN_VERSION,
    best_label_facet,
    clipped_confidence,
    compute_complexity_score,
    compute_revenue_score,
    effective_n,
    filter_eligible,
    has_enough_facets,
    score_niche,
)


# --- fixtures --------------------------------------------------------------

def _facet(
    post_id=1, is_pain_point=1, wtp="would_pay", urgency="recurring",
    dollar=None, market="smb", role="owner",
    integrations=None, summary="example pain", confidence=0.7,
):
    return {
        "post_id": post_id,
        "is_pain_point": is_pain_point,
        "willingness_to_pay": wtp,
        "urgency": urgency,
        "max_dollar_anchor": dollar,
        "market_size_signal": market,
        "buyer_role": role,
        "integrations_mentioned": json.dumps(integrations or []),
        "pain_summary": summary,
        "confidence": confidence,
    }


# --- filter_eligible (critical bug guard) ----------------------------------

class TestFilterEligible:
    def test_keeps_is_pain_point_1(self):
        assert len(filter_eligible([_facet(is_pain_point=1)])) == 1

    def test_drops_is_pain_point_0(self):
        assert filter_eligible([_facet(is_pain_point=0)]) == []

    def test_drops_missing_is_pain_point(self):
        f = _facet()
        del f["is_pain_point"]
        assert filter_eligible([f]) == []

    def test_mixed_drops_only_zero(self):
        facets = [_facet(post_id=1, is_pain_point=1),
                  _facet(post_id=2, is_pain_point=0),
                  _facet(post_id=3, is_pain_point=1)]
        eligible = filter_eligible(facets)
        assert {f["post_id"] for f in eligible} == {1, 3}


# --- confidence clipping ---------------------------------------------------

class TestClippedConfidence:
    def test_below_floor_clamps(self):
        assert clipped_confidence({"confidence": 0.1}) == 0.3

    def test_above_ceiling_clamps(self):
        assert clipped_confidence({"confidence": 0.99}) == 0.85

    def test_inside_range_passes_through(self):
        assert clipped_confidence({"confidence": 0.5}) == 0.5

    def test_missing_confidence_defaults_to_0_5(self):
        assert clipped_confidence({}) == 0.5


# --- revenue score ---------------------------------------------------------

class TestComputeRevenueScore:
    def test_empty_returns_zero(self):
        score, bd = compute_revenue_score([])
        assert score == 0.0
        assert bd["_eligible_count"] == 0

    def test_vetoed_only_returns_zero(self):
        score, bd = compute_revenue_score([_facet(is_pain_point=0, wtp="would_pay")])
        assert score == 0.0
        assert bd["_eligible_count"] == 0

    def test_high_wtp_high_urgency_scores_high(self):
        facets = [_facet(wtp="would_pay", urgency="blocking",
                          dollar=200, market="enterprise", confidence=0.8)]
        score, _ = compute_revenue_score(facets)
        assert score > 0.6, f"got {score}"

    def test_low_wtp_low_urgency_scores_low(self):
        facets = [_facet(wtp="no_signal", urgency="none",
                          dollar=None, market="hobbyist", role=None,
                          confidence=0.8)]
        score, _ = compute_revenue_score(facets)
        assert score < 0.2, f"got {score}"

    def test_breakdown_carries_eligible_count_and_components(self):
        facets = [_facet(wtp="would_pay"), _facet(post_id=2, wtp="hesitant")]
        _, bd = compute_revenue_score(facets)
        assert bd["_eligible_count"] == 2
        assert "willingness_to_pay" in bd

    def test_missing_buyer_role_doesnt_zero_bias(self):
        # When buyer_role is None for every facet, the signal is dropped
        # rather than counted as 0 — otherwise no_signal niches would
        # always lose 10% off the top.
        facets = [_facet(role=None, wtp="would_pay")]
        score, bd = compute_revenue_score(facets)
        # buyer_role should be absent from breakdown (dropped via None return)
        assert "buyer_role" not in bd
        # Score should still be reasonable (not zero-biased)
        assert score > 0.4


# --- complexity score ------------------------------------------------------

class TestComputeComplexityScore:
    def test_empty_returns_neutral_default(self):
        score, _ = compute_complexity_score([])
        assert score == 0.5

    def test_many_integrations_is_complex(self):
        facets = [_facet(integrations=["QuickBooks", "Stripe", "Salesforce"])]
        score, _ = compute_complexity_score(facets)
        # integrations_count is 0.40 weight, value=1.0 for 3+ → contributes 0.40
        # alone. With market=smb (0.6 * 0.2) and 0 keywords, total ~ (0.4 + 0.12) / 1.0 ~ 0.52
        assert score >= 0.5

    def test_no_integrations_no_keywords_is_simpler(self):
        facets = [_facet(integrations=[], summary="something simple")]
        score, _ = compute_complexity_score(facets)
        assert score < 0.4

    def test_keyword_hits_increase_complexity(self):
        baseline = compute_complexity_score([_facet(summary="basic pain")])[0]
        complex_summary = compute_complexity_score(
            [_facet(summary="real-time compliance auth")]
        )[0]
        assert complex_summary > baseline


# --- adaptive threshold ----------------------------------------------------

class TestHasEnoughFacets:
    def test_empty_false(self):
        assert has_enough_facets([], cluster_post_count=10) is False

    def test_vetoed_only_false(self):
        assert has_enough_facets([_facet(is_pain_point=0)] * 5, 10) is False

    def test_small_cluster_needs_at_least_2(self):
        facets = [_facet()]
        assert has_enough_facets(facets, cluster_post_count=4) is False
        facets2 = [_facet(post_id=1, confidence=0.8),
                   _facet(post_id=2, confidence=0.8)]
        assert has_enough_facets(facets2, cluster_post_count=4) is True

    def test_large_cluster_scales_threshold(self):
        # ceil(0.25 * 100) = 25; 5 facets shouldn't be enough
        facets = [_facet(post_id=i, confidence=0.8) for i in range(5)]
        assert has_enough_facets(facets, cluster_post_count=100) is False

    def test_effective_n_floor_can_veto(self):
        # 3 facets at confidence=0.3 → effective_n = 0.9 < 1.5 → fail
        facets = [_facet(post_id=i, confidence=0.1) for i in range(3)]
        # Even though count > 2, effective_n (0.9) < 1.5 → False
        assert has_enough_facets(facets, cluster_post_count=8) is False


# --- score_niche top-level routing -----------------------------------------

class TestScoreNiche:
    def test_routes_to_faceted_when_enough(self):
        facets = [_facet(post_id=i, confidence=0.8) for i in range(3)]
        rev, comp, rank, bd, mode = score_niche(
            facets, cluster_post_count=8, fallback_opportunity_avg=0.3,
        )
        assert mode == "faceted"
        assert bd["mode"] == "faceted"
        assert bd["breakdown_version"] == BREAKDOWN_VERSION
        assert "revenue" in bd
        assert "complexity" in bd

    def test_routes_to_fallback_when_thin(self):
        facets = [_facet(post_id=1)]
        rev, comp, rank, bd, mode = score_niche(
            facets, cluster_post_count=10, fallback_opportunity_avg=0.42,
        )
        assert mode == "dumb_fallback"
        assert bd["mode"] == "dumb_fallback"
        assert rev == 0.42
        assert comp == 0.5
        assert "fallback_reason" in bd

    def test_fallback_when_all_vetoed(self):
        facets = [_facet(post_id=i, is_pain_point=0) for i in range(10)]
        rev, comp, rank, bd, mode = score_niche(
            facets, cluster_post_count=20, fallback_opportunity_avg=0.5,
        )
        assert mode == "dumb_fallback"
        # The critical check — vetoed facets must NOT have boosted revenue
        assert rev == 0.5  # exactly the fallback, not influenced by would_pay vetoes
        assert "no eligible facets" in bd["fallback_reason"]

    def test_breakdown_version_is_present(self):
        _, _, _, bd, _ = score_niche([], 5, 0.3)
        assert bd["breakdown_version"] == BREAKDOWN_VERSION

    def test_rank_formula_consistent(self):
        # rank = rev / (1 + comp); spot-check with simple inputs
        facets = [_facet(post_id=i, confidence=0.8) for i in range(3)]
        rev, comp, rank, _, _ = score_niche(facets, 8, 0.3)
        assert abs(rank - rev / (1 + comp)) < 1e-3


# --- best_label_facet ------------------------------------------------------

class TestBestLabelFacet:
    def test_empty_returns_none(self):
        assert best_label_facet([]) is None

    def test_all_vetoed_returns_none(self):
        assert best_label_facet([_facet(is_pain_point=0)] * 3) is None

    def test_picks_highest_confidence(self):
        facets = [
            _facet(post_id=1, confidence=0.4, summary="low"),
            _facet(post_id=2, confidence=0.8, summary="high"),
            _facet(post_id=3, confidence=0.6, summary="med"),
        ]
        winner = best_label_facet(facets)
        assert winner["post_id"] == 2

    def test_confidence_clipping_affects_tie_break(self):
        # 0.99 clips to 0.85; 0.85 stays 0.85; both equally weighted but
        # raw 0.99 wins the tie-break (raw confidence is the second sort key)
        facets = [
            _facet(post_id=1, confidence=0.85),
            _facet(post_id=2, confidence=0.99),
        ]
        winner = best_label_facet(facets)
        assert winner["post_id"] == 2


# --- coverage on effective_n -----------------------------------------------

class TestEffectiveN:
    def test_zero_for_empty(self):
        assert effective_n([]) == 0.0

    def test_clipped_sum(self):
        # 0.1 → 0.3, 0.5 → 0.5, 0.9 → 0.85; sum = 1.65
        facets = [_facet(confidence=0.1), _facet(post_id=2, confidence=0.5),
                  _facet(post_id=3, confidence=0.9)]
        assert math.isclose(effective_n(facets), 1.65, abs_tol=1e-6)


# --- monkeypatched-config test (clip range) --------------------------------

class TestConfigOverrides:
    def test_clip_range_respects_config(self, monkeypatch):
        monkeypatch.setattr(niche_scorer, "FACET_CONFIDENCE_CLIP", (0.5, 0.7))
        # 0.3 → clamps up to 0.5
        assert clipped_confidence({"confidence": 0.3}) == 0.5
        # 0.95 → clamps down to 0.7
        assert clipped_confidence({"confidence": 0.95}) == 0.7
