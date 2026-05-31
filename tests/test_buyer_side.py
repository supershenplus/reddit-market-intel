"""Tests for analysis/buyer_side.py — the buyer-side validation gate (v3).

Mirrors test_saturation.py: unit-level gate logic + score_niche integration.
"""

import json

import pytest

from analysis.buyer_side import (
    compute_buyer_side_score,
    format_buyer_side_note,
)

# Mirror config defaults so the tests pin the documented behavior.
FLOOR = 0.5
MIN_EVID = 3
TAG = 0.40
BUYER = {"owner", "finance"}
OPERATOR = {"individual_contributor", "manager"}


def _facet(role=None, wtp=None, is_pain_point=1):
    f = {"is_pain_point": is_pain_point}
    if role is not None:
        f["buyer_role"] = role
    if wtp is not None:
        f["willingness_to_pay"] = wtp
    return f


def _score(facets):
    return compute_buyer_side_score(
        facets, FLOOR, MIN_EVID, BUYER, OPERATOR, TAG,
    )


# --- is_pain_point veto filter (critical-bug pattern) ---------------------

class TestVetoFilter:
    def test_vetoed_facets_dropped(self):
        # 4 owner would_pay but all vetoed → no buyer evidence counted.
        facets = [_facet("owner", "would_pay", is_pain_point=0) for _ in range(4)]
        _, bd = _score(facets)
        assert bd["n_buyer"] == 0
        assert bd["buyer_wp_count"] == 0
        assert bd["gate_state"] == "unvalidated"

    def test_missing_is_pain_point_drops(self):
        facets = [{"buyer_role": "owner", "willingness_to_pay": "would_pay"}]
        _, bd = _score(facets)
        assert bd["n_buyer"] == 0


# --- gate state: pass -----------------------------------------------------

class TestPass:
    def test_pure_buyer_would_pay_passes_no_penalty(self):
        facets = [_facet("owner", "would_pay") for _ in range(3)]
        score, bd = _score(facets)
        assert bd["gate_state"] == "pass"
        assert bd["penalty_multiplier"] == 1.0  # buyer_ratio == 1.0
        assert score == 1.0
        assert bd["buyer_wp_count"] == 3

    def test_finance_counts_as_buyer(self):
        facets = (
            [_facet("finance", "would_pay") for _ in range(2)]
            + [_facet("owner", "would_pay")]
        )
        _, bd = _score(facets)
        assert bd["n_buyer"] == 3
        assert bd["gate_state"] == "pass"

    def test_mixed_but_buyer_dominated_passes(self):
        # 4 owner would_pay (clears evidence bar) + 1 operator → ratio 0.8 ≥ tag.
        facets = (
            [_facet("owner", "would_pay") for _ in range(4)]
            + [_facet("individual_contributor", "would_pay")]
        )
        _, bd = _score(facets)
        assert bd["gate_state"] == "pass"
        assert bd["buyer_ratio"] == pytest.approx(0.8)
        assert bd["penalty_multiplier"] == pytest.approx(0.8)


# --- gate state: operator_only --------------------------------------------

class TestOperatorOnly:
    def test_clears_evidence_but_operator_dominated(self):
        # 3 owner would_pay (clears bar) but 10 operators → ratio 0.23 < 0.40.
        facets = (
            [_facet("owner", "would_pay") for _ in range(3)]
            + [_facet("individual_contributor", "would_pay") for _ in range(10)]
        )
        _, bd = _score(facets)
        assert bd["gate_state"] == "operator_only"
        assert bd["buyer_ratio"] < TAG
        # Penalty floored (raw ratio 0.23 < 0.5 floor).
        assert bd["penalty_multiplier"] == FLOOR

    def test_just_below_tag_threshold(self):
        # ratio exactly under 0.40: 3 buyer / 5 operator = 0.375.
        facets = (
            [_facet("owner", "would_pay") for _ in range(3)]
            + [_facet("manager", "would_pay") for _ in range(5)]
        )
        _, bd = _score(facets)
        assert bd["buyer_ratio"] == pytest.approx(0.375)
        assert bd["gate_state"] == "operator_only"


# --- gate state: unvalidated (hard block) ---------------------------------

class TestUnvalidated:
    def test_pure_operator_is_unvalidated(self):
        facets = [_facet("individual_contributor", "would_pay") for _ in range(8)]
        _, bd = _score(facets)
        assert bd["gate_state"] == "unvalidated"
        assert bd["buyer_wp_count"] == 0
        assert bd["buyer_ratio"] == 0.0
        assert bd["penalty_multiplier"] == FLOOR  # ratio 0.0 → floor

    def test_two_buyer_would_pay_under_min(self):
        # 2 < MIN_EVID(3) → unvalidated even though ratio is perfect.
        facets = [_facet("owner", "would_pay") for _ in range(2)]
        _, bd = _score(facets)
        assert bd["gate_state"] == "unvalidated"
        assert bd["buyer_wp_count"] == 2

    def test_buyer_present_but_not_would_pay(self):
        # Owners who are hesitant/no_signal don't count toward evidence.
        facets = [_facet("owner", "hesitant") for _ in range(5)]
        _, bd = _score(facets)
        assert bd["buyer_wp_count"] == 0
        assert bd["gate_state"] == "unvalidated"
        assert bd["n_buyer"] == 5  # still counted in the ratio

    def test_no_role_data_no_penalty_but_blocked(self):
        # No buyer_role at all → we don't know; don't cut rank, but block build.
        facets = [_facet(role=None, wtp="would_pay") for _ in range(5)]
        _, bd = _score(facets)
        assert bd["n_buyer"] == 0
        assert bd["n_operator"] == 0
        assert bd["penalty_multiplier"] == 1.0  # no double-punishment
        assert bd["gate_state"] == "unvalidated"


# --- boundary at MIN_BUYER_EVIDENCE ---------------------------------------

class TestEvidenceBoundary:
    def test_exactly_min_clears(self):
        facets = [_facet("owner", "would_pay") for _ in range(MIN_EVID)]
        _, bd = _score(facets)
        assert bd["gate_state"] == "pass"

    def test_one_under_min_blocks(self):
        facets = [_facet("owner", "would_pay") for _ in range(MIN_EVID - 1)]
        _, bd = _score(facets)
        assert bd["gate_state"] == "unvalidated"


# --- malformed / empty ----------------------------------------------------

class TestMalformed:
    def test_empty_facets(self):
        _, bd = _score([])
        assert bd["gate_state"] == "unvalidated"
        assert bd["penalty_multiplier"] == 1.0

    def test_role_case_insensitive(self):
        facets = [_facet("OWNER", "WOULD_PAY") for _ in range(3)]
        _, bd = _score(facets)
        assert bd["n_buyer"] == 3
        assert bd["gate_state"] == "pass"

    def test_unknown_role_ignored(self):
        # 'it'/'other' are neither buyer nor operator → excluded from ratio.
        facets = (
            [_facet("owner", "would_pay") for _ in range(3)]
            + [_facet("it", "would_pay"), _facet("other", "would_pay")]
        )
        _, bd = _score(facets)
        assert bd["n_buyer"] == 3
        assert bd["n_operator"] == 0
        assert bd["buyer_ratio"] == 1.0


# --- format_buyer_side_note -----------------------------------------------

class TestFormatNote:
    def test_none_for_pass(self):
        _, bd = _score([_facet("owner", "would_pay") for _ in range(3)])
        assert format_buyer_side_note(bd) is None

    def test_none_for_none_input(self):
        assert format_buyer_side_note(None) is None

    def test_none_for_fallback_breakdown(self):
        assert format_buyer_side_note({}) is None

    def test_unvalidated_note(self):
        _, bd = _score([_facet("owner", "would_pay") for _ in range(2)])
        note = format_buyer_side_note(bd)
        assert note is not None and note.startswith("⛔")

    def test_operator_only_note(self):
        facets = (
            [_facet("owner", "would_pay") for _ in range(3)]
            + [_facet("individual_contributor", "would_pay") for _ in range(10)]
        )
        _, bd = _score(facets)
        note = format_buyer_side_note(bd)
        assert note is not None and note.startswith("🚩")


# --- score_niche integration: buyer-side penalty flows into rank ----------

class TestScoreNicheRankApplied:
    def _facets(self, role, n=5):
        return [
            {
                "post_id": i, "is_pain_point": 1,
                "willingness_to_pay": "would_pay", "urgency": "recurring",
                "max_dollar_anchor": 100.0, "market_size_signal": "smb",
                "buyer_role": role,
                "integrations_mentioned": json.dumps([]),
                "pain_summary": "x", "confidence": 0.8,
            }
            for i in range(n)
        ]

    def test_owner_niche_no_buyer_penalty(self):
        from analysis.niche_scorer import score_niche

        rev, comp, rank, bd, _ = score_niche(self._facets("owner"), 12, 0.3)
        assert bd["buyer_side"]["gate_state"] == "pass"
        assert bd["buyer_side"]["penalty_multiplier"] == 1.0
        # No saturation tools either → rank == rev/(1+comp).
        assert abs(rank - rev / (1 + comp)) < 1e-3

    def test_operator_niche_drops_rank(self):
        from analysis.niche_scorer import score_niche

        rev, comp, rank, bd, _ = score_niche(
            self._facets("individual_contributor"), 12, 0.3,
        )
        unpenalized = rev / (1 + comp)
        assert bd["buyer_side"]["gate_state"] == "unvalidated"
        assert rank < unpenalized
        assert bd["buyer_side"]["penalty_multiplier"] == FLOOR
        assert abs(rank - unpenalized * FLOOR) < 1e-3
