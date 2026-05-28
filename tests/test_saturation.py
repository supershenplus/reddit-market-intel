"""Tests for analysis/saturation.py — corpus-internal saturation display +
W4-1 scoring surface."""

import json

import pytest

from analysis.saturation import (
    compute_saturation,
    compute_saturation_score,
    format_saturation_note,
)


def _facet(is_pain_point=1, integrations=None, current_solution=None):
    f = {
        "is_pain_point": is_pain_point,
        "integrations_mentioned": json.dumps(integrations or []),
    }
    if current_solution is not None:
        f["current_solution"] = current_solution
    return f


# --- is_pain_point filter (critical-bug pattern) --------------------------

class TestVetoFilter:
    def test_vetoed_facets_dropped(self):
        facets = [
            _facet(is_pain_point=1, integrations=["A"]),
            _facet(is_pain_point=0, integrations=["B", "C"]),  # vetoed — must drop
            _facet(is_pain_point=1, integrations=["D"]),
        ]
        result = compute_saturation(facets)
        assert result["integrations"] == ["A", "D"]
        assert "B" not in result["integrations"]
        assert "C" not in result["integrations"]

    def test_all_vetoed_returns_empty(self):
        facets = [_facet(is_pain_point=0, integrations=["A", "B"])]
        assert compute_saturation(facets)["integrations"] == []

    def test_missing_is_pain_point_drops(self):
        # Defensive: missing field treated same as vetoed
        facets = [{"integrations_mentioned": json.dumps(["A"])}]
        assert compute_saturation(facets)["integrations"] == []


# --- dedup -----------------------------------------------------------------

class TestDedup:
    def test_case_insensitive_dedup(self):
        facets = [
            _facet(integrations=["QuickBooks"]),
            _facet(integrations=["quickbooks"]),
            _facet(integrations=["QUICKBOOKS"]),
        ]
        result = compute_saturation(facets)
        assert len(result["integrations"]) == 1
        # First-seen casing preserved
        assert result["integrations"][0] == "QuickBooks"

    def test_distinct_names_preserved(self):
        facets = [_facet(integrations=["A", "B", "C", "D"])]
        result = compute_saturation(facets)
        assert set(result["integrations"]) == {"A", "B", "C", "D"}
        assert result["count"] == 4


# --- malformed input ------------------------------------------------------

class TestMalformedInput:
    def test_empty_facets(self):
        assert compute_saturation([])["integrations"] == []

    def test_missing_integrations_field(self):
        assert compute_saturation([{"is_pain_point": 1}])["integrations"] == []

    def test_null_integrations(self):
        f = {"is_pain_point": 1, "integrations_mentioned": None}
        assert compute_saturation([f])["integrations"] == []

    def test_invalid_json_graceful(self):
        f = {"is_pain_point": 1, "integrations_mentioned": "not json"}
        assert compute_saturation([f])["integrations"] == []

    def test_non_list_json(self):
        f = {"is_pain_point": 1, "integrations_mentioned": json.dumps({"a": 1})}
        assert compute_saturation([f])["integrations"] == []

    def test_empty_strings_dropped(self):
        f = _facet(integrations=["", "  ", "Real"])
        assert compute_saturation([f])["integrations"] == ["Real"]


# --- sorting --------------------------------------------------------------

class TestSorting:
    def test_alphabetical_case_insensitive(self):
        facets = [_facet(integrations=["zebra", "Apple", "mango", "BANANA"])]
        result = compute_saturation(facets)
        # Sorted by lowercase: apple, banana, mango, zebra
        assert result["integrations"] == ["Apple", "BANANA", "mango", "zebra"]


# --- W4-1 scoring surface --------------------------------------------------

K = 0.3
FLOOR = 0.5


class TestComputeSaturationScore:
    def test_empty_returns_zero_score(self):
        score, bd = compute_saturation_score([], K, FLOOR)
        assert score == 0.0
        assert bd["distinct_count"] == 0
        assert bd["penalty_multiplier"] == 1.0
        assert bd["top_tools"] == []

    def test_vetoed_only_returns_zero_score(self):
        facets = [_facet(is_pain_point=0, integrations=["A", "B", "C"])]
        score, bd = compute_saturation_score(facets, K, FLOOR)
        assert score == 0.0
        assert bd["distinct_count"] == 0

    def test_one_distinct_tool_low_score(self):
        # n=1 → 1 - 1/(1 + 0.3*log(2)) ≈ 0.17
        facets = [_facet(integrations=["Doorloop"])]
        score, bd = compute_saturation_score(facets, K, FLOOR)
        assert 0.15 < score < 0.20
        assert bd["distinct_count"] == 1
        # Penalty hits floor with low score (1-0.17=0.83 > 0.5 floor)
        assert bd["penalty_multiplier"] == pytest.approx(1.0 - score, abs=1e-3)

    def test_many_distinct_tools_higher_score(self):
        # n=10 → ~0.42 saturation
        tools = [f"Tool{i}" for i in range(10)]
        facets = [_facet(integrations=tools)]
        score, bd = compute_saturation_score(facets, K, FLOOR)
        assert 0.40 < score < 0.45
        assert bd["distinct_count"] == 10

    def test_penalty_floored_for_extreme_saturation(self):
        # n=100 → very high saturation, but penalty bottoms at FLOOR
        tools = [f"Tool{i}" for i in range(100)]
        facets = [_facet(integrations=tools)]
        score, bd = compute_saturation_score(facets, K, FLOOR)
        assert bd["penalty_multiplier"] == FLOOR

    def test_frequency_weighting_in_breakdown(self):
        # Doorloop in 3 facets, Buildium in 2, AppFolio in 1 → distinct=3,
        # weighted=6. top_tools ordered by frequency desc.
        facets = [
            _facet(integrations=["Doorloop", "Buildium"]),
            _facet(integrations=["Doorloop", "Buildium", "AppFolio"]),
            _facet(integrations=["Doorloop"]),
        ]
        score, bd = compute_saturation_score(facets, K, FLOOR)
        assert bd["distinct_count"] == 3
        assert bd["weighted_count"] == 6
        # Doorloop first (3 mentions), Buildium second (2), AppFolio last (1)
        names = [t[0] for t in bd["top_tools"]]
        counts = [t[1] for t in bd["top_tools"]]
        assert names == ["Doorloop", "Buildium", "AppFolio"]
        assert counts == [3, 2, 1]

    def test_current_solution_contributes(self):
        # "I use Yardi" via current_solution should count alongside
        # integrations_mentioned.
        facets = [
            _facet(integrations=["Doorloop"], current_solution="Yardi"),
            _facet(integrations=["Doorloop"], current_solution="Buildium"),
        ]
        score, bd = compute_saturation_score(facets, K, FLOOR)
        # Distinct: doorloop, yardi, buildium → 3
        assert bd["distinct_count"] == 3
        # Doorloop=2, Yardi=1, Buildium=1
        names_to_counts = {t[0]: t[1] for t in bd["top_tools"]}
        assert names_to_counts["Doorloop"] == 2
        assert names_to_counts["Yardi"] == 1
        assert names_to_counts["Buildium"] == 1

    def test_non_tool_current_solutions_ignored(self):
        # "spreadsheet", "manual", etc are anti-saturation evidence — must
        # not inflate the score.
        facets = [
            _facet(current_solution="spreadsheet"),
            _facet(current_solution="Excel"),
            _facet(current_solution="nothing"),
            _facet(current_solution="Manual"),
        ]
        score, bd = compute_saturation_score(facets, K, FLOOR)
        assert bd["distinct_count"] == 0
        assert score == 0.0

    def test_case_insensitive_dedup(self):
        facets = [
            _facet(integrations=["QuickBooks"]),
            _facet(integrations=["quickbooks"]),
            _facet(integrations=["QUICKBOOKS"]),
        ]
        score, bd = compute_saturation_score(facets, K, FLOOR)
        assert bd["distinct_count"] == 1
        assert bd["weighted_count"] == 3
        # First-seen casing preserved
        assert bd["top_tools"][0][0] == "QuickBooks"

    def test_score_monotone_in_distinct_count(self):
        # Adding more distinct tools must never lower the score.
        scores = []
        for n in (1, 3, 5, 10, 20):
            tools = [f"Tool{i}" for i in range(n)]
            score, _ = compute_saturation_score(
                [_facet(integrations=tools)], K, FLOOR,
            )
            scores.append(score)
        assert scores == sorted(scores), f"monotonicity broken: {scores}"


class TestFormatSaturationNote:
    def test_none_when_no_tools(self):
        _, bd = compute_saturation_score([], K, FLOOR)
        assert format_saturation_note(bd) is None

    def test_none_for_none_input(self):
        assert format_saturation_note(None) is None

    def test_none_for_fallback_breakdown(self):
        # A fallback-mode breakdown has no saturation key — caller passes
        # None through. Defensive: empty dict also yields None.
        assert format_saturation_note({}) is None

    def test_formatted_with_counts(self):
        facets = [
            _facet(integrations=["Doorloop", "Buildium"]),
            _facet(integrations=["Doorloop"]),
        ]
        _, bd = compute_saturation_score(facets, K, FLOOR)
        note = format_saturation_note(bd)
        assert note is not None
        assert note.startswith("2 distinct tools:")
        assert "Doorloop(2)" in note
        assert "Buildium(1)" in note

    def test_more_suffix_when_truncated(self):
        # 10 distinct tools but top_tools only shows 8 — note includes "+2 more"
        tools = [f"Tool{i}" for i in range(10)]
        facets = [_facet(integrations=tools)]
        _, bd = compute_saturation_score(facets, K, FLOOR)
        note = format_saturation_note(bd)
        assert "+2 more" in note


# --- score_niche integration: saturation flows into rank ------------------

class TestScoreNicheRankApplied:
    """Sanity-check that score_niche applies the saturation penalty."""

    def test_no_tools_no_penalty(self):
        """Facets without integrations or current_solution → saturation=0,
        penalty=1.0, rank == rev/(1+comp). Backward-compat invariant."""
        from analysis.niche_scorer import score_niche

        facets = [
            {
                "post_id": i, "is_pain_point": 1,
                "willingness_to_pay": "would_pay", "urgency": "recurring",
                "max_dollar_anchor": 100.0, "market_size_signal": "smb",
                "buyer_role": "owner",
                "integrations_mentioned": json.dumps([]),
                "pain_summary": "x", "confidence": 0.8,
            }
            for i in range(3)
        ]
        rev, comp, rank, bd, _ = score_niche(facets, 8, 0.3)
        expected = rev / (1 + comp)
        assert abs(rank - expected) < 1e-3
        assert bd["saturation"]["score"] == 0.0
        assert bd["saturation"]["penalty_multiplier"] == 1.0

    def test_many_tools_drops_rank(self):
        """Same facets but with 8 distinct integrations → rank drops below
        rev/(1+comp)."""
        from analysis.niche_scorer import score_niche

        tools = ["Doorloop", "Buildium", "AppFolio", "Yardi",
                 "RentManager", "Avail", "Hemlane", "Stessa"]
        facets = [
            {
                "post_id": i, "is_pain_point": 1,
                "willingness_to_pay": "would_pay", "urgency": "recurring",
                "max_dollar_anchor": 100.0, "market_size_signal": "smb",
                "buyer_role": "owner",
                "integrations_mentioned": json.dumps(tools),
                "pain_summary": "x", "confidence": 0.8,
            }
            for i in range(3)
        ]
        rev, comp, rank, bd, _ = score_niche(facets, 8, 0.3)
        unpenalized = rev / (1 + comp)
        # n=8 distinct → saturation ≈ 0.40 → penalty ≈ 0.60
        assert rank < unpenalized
        assert bd["saturation"]["score"] > 0.30
        assert bd["saturation"]["penalty_multiplier"] < 0.70
