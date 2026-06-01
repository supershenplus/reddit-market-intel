"""Tests for analysis/latent_demand.py — the behavioral latent-demand signal (v4)."""

import json

import pytest

from analysis.latent_demand import compute_latent_demand_score

# Mirror config defaults.
WEIGHTS = {"manual_workaround": 0.5, "urgency": 0.3, "dollar_present": 0.2}
MANUAL = {
    "spreadsheet", "excel", "google sheet", "manual", "by hand",
    "pen and paper", "paper", "notebook", "hired", "outsourc",
    "virtual assistant", "assistant", "whiteboard", "sticky note",
}


def _facet(is_pain_point=1, current_solution=None, urgency=None, dollar=None):
    f = {"is_pain_point": is_pain_point}
    if current_solution is not None:
        f["current_solution"] = current_solution
    if urgency is not None:
        f["urgency"] = urgency
    if dollar is not None:
        f["max_dollar_anchor"] = dollar
    return f


def _score(facets):
    return compute_latent_demand_score(facets, WEIGHTS, MANUAL)


# --- veto filter ----------------------------------------------------------

class TestVetoFilter:
    def test_vetoed_facets_dropped(self):
        facets = [_facet(is_pain_point=0, current_solution="spreadsheet",
                         urgency="blocking", dollar=500)]
        score, bd = _score(facets)
        assert score == 0.0
        assert bd["eligible_count"] == 0

    def test_empty_facets(self):
        score, bd = _score([])
        assert score == 0.0
        assert bd["manual_count"] == 0


# --- the critical split: manual workaround vs "nothing" -------------------

class TestManualWorkaroundSplit:
    def test_spreadsheet_counts(self):
        _, bd = _score([_facet(current_solution="spreadsheet")])
        assert bd["manual_count"] == 1
        assert bd["manual_workaround_frac"] == 1.0

    def test_nothing_does_not_count(self):
        # "nothing"/"none" are genuine no-signal — must NOT count as workaround.
        _, bd = _score([
            _facet(current_solution="nothing"),
            _facet(current_solution="none"),
            _facet(current_solution=None),
        ])
        assert bd["manual_count"] == 0
        assert bd["manual_workaround_frac"] == 0.0

    def test_named_tool_does_not_count(self):
        # An incumbent SaaS tool is saturation evidence, not latent demand.
        _, bd = _score([_facet(current_solution="Procore"),
                        _facet(current_solution="QuickBooks")])
        assert bd["manual_count"] == 0

    def test_substring_match_multiword(self):
        # "excel spreadsheets", "manual process", "hired a VA" should all match.
        _, bd = _score([
            _facet(current_solution="excel spreadsheets"),
            _facet(current_solution="a manual process"),
            _facet(current_solution="hired a part-time bookkeeper"),
        ])
        assert bd["manual_count"] == 3

    def test_case_insensitive(self):
        _, bd = _score([_facet(current_solution="SPREADSHEET")])
        assert bd["manual_count"] == 1


# --- urgency + dollar sub-signals -----------------------------------------

class TestUrgencyAndDollar:
    def test_urgency_mean(self):
        facets = [_facet(urgency="blocking"), _facet(urgency="recurring")]
        _, bd = _score(facets)
        assert bd["urgency_mean"] == pytest.approx((1.0 + 0.7) / 2)

    def test_urgency_none_value_zero(self):
        _, bd = _score([_facet(urgency="none")])
        assert bd["urgency_mean"] == 0.0

    def test_unknown_urgency_ignored(self):
        # Facet with no urgency field doesn't drag the mean to 0.
        facets = [_facet(urgency="blocking"), _facet()]
        _, bd = _score(facets)
        assert bd["urgency_mean"] == 1.0

    def test_dollar_present_frac(self):
        facets = [_facet(dollar=500), _facet(dollar=0), _facet(dollar=None),
                  _facet(dollar=1200)]
        _, bd = _score(facets)
        assert bd["dollar_present_frac"] == 0.5  # 2 of 4 positive


# --- composite score ------------------------------------------------------

class TestCompositeScore:
    def test_all_signals_max(self):
        # Every facet: manual workaround, blocking urgency, $ present → 1.0.
        facets = [_facet(current_solution="spreadsheet", urgency="blocking",
                         dollar=1000) for _ in range(3)]
        score, _ = _score(facets)
        assert score == pytest.approx(1.0)

    def test_no_signals_zero(self):
        facets = [_facet(current_solution="nothing", urgency="none") for _ in range(3)]
        score, _ = _score(facets)
        assert score == 0.0

    def test_weighted_blend(self):
        # manual=1.0, urgency=0.7(recurring), dollar=0 → 0.5*1 + 0.3*0.7 + 0.2*0
        facets = [_facet(current_solution="manual", urgency="recurring")]
        score, _ = _score(facets)
        assert score == pytest.approx(0.5 + 0.3 * 0.7)

    def test_score_bounded(self):
        score, _ = _score([_facet(current_solution="spreadsheet",
                                  urgency="blocking", dollar=99999)])
        assert 0.0 <= score <= 1.0


# --- score_niche integration: latent_demand in breakdown, NO rank change --

class TestScoreNicheDisplayOnly:
    def _facets(self, **kw):
        base = {
            "post_id": 0, "is_pain_point": 1, "willingness_to_pay": "no_signal",
            "urgency": "recurring", "max_dollar_anchor": 100.0,
            "market_size_signal": "smb", "buyer_role": "owner",
            "integrations_mentioned": json.dumps([]),
            "current_solution": "spreadsheet",
            "pain_summary": "x", "confidence": 0.8,
        }
        base.update(kw)
        return [dict(base, post_id=i) for i in range(4)]

    def test_latent_demand_in_breakdown(self):
        from analysis.niche_scorer import score_niche

        _rev, _comp, _rank, bd, _ = score_niche(self._facets(), 12, 0.3)
        assert "latent_demand" in bd
        assert bd["latent_demand"]["score"] > 0
        assert bd["latent_demand"]["manual_count"] == 4

    def test_rank_unaffected_by_latent_demand(self):
        # Display-only invariant. Vary ONLY current_solution (spreadsheet vs
        # nothing): both are non-tool so saturation is identical, and
        # current_solution feeds neither revenue nor complexity. Only
        # latent_demand changes — so rank must be IDENTICAL.
        from analysis.niche_scorer import score_niche

        high = self._facets(current_solution="spreadsheet")
        zero = self._facets(current_solution="nothing")
        _, _, rank_high, bd_high, _ = score_niche(high, 12, 0.3)
        _, _, rank_zero, bd_zero, _ = score_niche(zero, 12, 0.3)
        assert bd_high["latent_demand"]["score"] > bd_zero["latent_demand"]["score"]
        assert rank_high == pytest.approx(rank_zero)
        # latent_demand carries no penalty_multiplier — it cannot touch rank.
        assert "penalty_multiplier" not in bd_high["latent_demand"]
