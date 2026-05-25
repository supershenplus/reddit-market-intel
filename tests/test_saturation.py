"""Tests for analysis/saturation.py — corpus-internal saturation display."""

import json

import pytest

from analysis.saturation import compute_saturation


def _facet(is_pain_point=1, integrations=None):
    return {
        "is_pain_point": is_pain_point,
        "integrations_mentioned": json.dumps(integrations or []),
    }


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
