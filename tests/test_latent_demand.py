"""Tests for analysis/latent_demand.py — behavioral latent-demand (v4 signal,
v0.2 facets). Version-tolerant: blends over present sub-signals, renormalized."""

import json

import pytest

from analysis.latent_demand import compute_latent_demand_score

# Mirror config defaults.
WEIGHTS = {
    "workaround_effort": 0.35, "time_cost": 0.20, "solution_seeking": 0.20,
    "urgency": 0.15, "dollar_present": 0.10,
}
MANUAL = {
    "spreadsheet", "excel", "google sheet", "manual", "by hand",
    "pen and paper", "paper", "notebook", "hired", "outsourc",
    "virtual assistant", "assistant", "whiteboard", "sticky note",
}


def _facet(is_pain_point=1, current_solution=None, urgency=None, dollar=None,
           workaround_effort=None, time_cost=None, solution_seeking=None):
    f = {"is_pain_point": is_pain_point}
    if current_solution is not None:
        f["current_solution"] = current_solution
    if urgency is not None:
        f["urgency"] = urgency
    if dollar is not None:
        f["max_dollar_anchor"] = dollar
    if workaround_effort is not None:
        f["workaround_effort"] = workaround_effort
    if time_cost is not None:
        f["time_cost"] = time_cost
    if solution_seeking is not None:
        f["solution_seeking"] = solution_seeking
    return f


def _score(facets):
    return compute_latent_demand_score(facets, WEIGHTS, MANUAL)


# --- veto filter ----------------------------------------------------------

class TestVetoFilter:
    def test_vetoed_dropped(self):
        score, bd = _score([_facet(is_pain_point=0, workaround_effort="hired",
                                   urgency="blocking", dollar=500)])
        assert score == 0.0
        assert bd["eligible_count"] == 0

    def test_empty(self):
        score, bd = _score([])
        assert score == 0.0
        assert bd["workaround_count"] == 0


# --- v0.2 workaround_effort field -----------------------------------------

class TestWorkaroundField:
    def test_manual_and_hired_values(self):
        # manual=0.6, hired=1.0 → mean 0.8.
        _, bd = _score([_facet(workaround_effort="manual"),
                        _facet(workaround_effort="hired")])
        assert bd["workaround_mean"] == pytest.approx(0.8)
        assert bd["workaround_count"] == 2

    def test_none_counts_as_zero_not_dropped(self):
        # workaround_effort='none' is a real signal (no effort) → 0.0, in the mean.
        _, bd = _score([_facet(workaround_effort="none")])
        assert bd["workaround_mean"] == 0.0
        assert bd["workaround_count"] == 0

    def test_field_takes_precedence_over_current_solution(self):
        # v0.2 field present → current_solution ignored.
        _, bd = _score([_facet(workaround_effort="hired",
                               current_solution="nothing")])
        assert bd["workaround_mean"] == 1.0


# --- v0.1 fallback via current_solution -----------------------------------

class TestWorkaroundFallback:
    def test_manual_term_maps_to_manual(self):
        _, bd = _score([_facet(current_solution="excel spreadsheets")])
        assert bd["workaround_mean"] == pytest.approx(0.6)
        assert bd["workaround_count"] == 1

    def test_named_tool_is_zero(self):
        _, bd = _score([_facet(current_solution="Procore")])
        assert bd["workaround_mean"] == 0.0
        assert bd["workaround_count"] == 0

    def test_null_current_solution_dropped(self):
        # No workaround signal at all → workaround sub-signal absent (mean 0 in
        # breakdown display, but dropped from the blend denominator).
        score, bd = _score([_facet(current_solution=None, urgency="blocking")])
        assert bd["workaround_count"] == 0
        # workaround dropped (no signal); present = urgency(1.0) + dollar(0.0, always
        # present). score = (0.15*1.0 + 0.10*0.0)/(0.15+0.10) = 0.15/0.25 = 0.6
        assert score == pytest.approx(0.6)


# --- v0.2-only sub-signals (drop when absent) -----------------------------

class TestTimeCostAndSeeking:
    def test_time_cost_mapping_and_count(self):
        _, bd = _score([_facet(time_cost="heavy"), _facet(time_cost="light")])
        assert bd["time_cost_mean"] == pytest.approx((1.0 + 0.3) / 2)
        assert bd["time_cost_n"] == 2

    def test_solution_seeking_mapping(self):
        # switching=1.0, evaluating=1.0, asking=0.6
        _, bd = _score([_facet(solution_seeking="switching"),
                        _facet(solution_seeking="asking")])
        assert bd["solution_seeking_mean"] == pytest.approx(0.8)
        assert bd["solution_seeking_n"] == 2

    def test_absent_v02_fields_dropped_from_blend(self):
        # A pure-urgency v0.1 facet: time_cost/solution_seeking absent → they must
        # NOT drag the score toward 0. Score should equal the urgency value.
        score, bd = _score([_facet(urgency="recurring")])
        assert bd["time_cost_n"] == 0
        assert bd["solution_seeking_n"] == 0
        # present sub-signals: urgency(0.7) + dollar(0.0, always present).
        # score = (0.15*0.7 + 0.10*0.0)/(0.15+0.10) = 0.105/0.25 = 0.42
        assert score == pytest.approx(0.42)


# --- dollar (always present) ----------------------------------------------

class TestDollar:
    def test_dollar_present_frac(self):
        _, bd = _score([_facet(dollar=500), _facet(dollar=0),
                        _facet(dollar=None), _facet(dollar=1200)])
        assert bd["dollar_present_frac"] == 0.5


# --- composite + renormalization ------------------------------------------

class TestComposite:
    def test_full_v02_max(self):
        f = _facet(workaround_effort="hired", time_cost="heavy",
                   solution_seeking="switching", urgency="blocking", dollar=1000)
        score, _ = _score([f])
        assert score == pytest.approx(1.0)

    def test_v01_facet_renormalizes(self):
        # current_solution manual (0.6), urgency recurring (0.7), no dollar (0.0),
        # no v0.2 fields. Present: workaround(0.35), urgency(0.15), dollar(0.10).
        # score = (0.35*0.6 + 0.15*0.7 + 0.10*0.0)/0.60 = 0.315/0.60 = 0.525
        score, _ = _score([_facet(current_solution="manual", urgency="recurring")])
        assert score == pytest.approx(0.525)

    def test_bounded(self):
        score, _ = _score([_facet(workaround_effort="hired", time_cost="heavy",
                                  solution_seeking="evaluating",
                                  urgency="blocking", dollar=99999)])
        assert 0.0 <= score <= 1.0


# --- score_niche integration: in breakdown, display-only ------------------

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

        _r, _c, _rank, bd, _ = score_niche(self._facets(), 12, 0.3)
        assert "latent_demand" in bd
        assert bd["latent_demand"]["score"] > 0
        assert bd["latent_demand"]["workaround_count"] == 4

    def test_v02_field_lifts_latent_demand(self):
        from analysis.niche_scorer import score_niche

        v01 = self._facets()  # current_solution spreadsheet only
        v02 = self._facets(workaround_effort="hired", time_cost="heavy",
                           solution_seeking="switching")
        _, _, _, bd01, _ = score_niche(v01, 12, 0.3)
        _, _, _, bd02, _ = score_niche(v02, 12, 0.3)
        assert bd02["latent_demand"]["score"] > bd01["latent_demand"]["score"]

    def test_rank_unaffected_by_latent_demand(self):
        # Vary ONLY current_solution (spreadsheet vs nothing) — both non-tool, so
        # saturation identical and current_solution feeds neither revenue nor
        # complexity. Only latent_demand changes → rank must be identical.
        from analysis.niche_scorer import score_niche

        high = self._facets(current_solution="spreadsheet")
        zero = self._facets(current_solution="nothing")
        _, _, rank_high, bd_high, _ = score_niche(high, 12, 0.3)
        _, _, rank_zero, bd_zero, _ = score_niche(zero, 12, 0.3)
        assert bd_high["latent_demand"]["score"] > bd_zero["latent_demand"]["score"]
        assert rank_high == pytest.approx(rank_zero)
        assert "penalty_multiplier" not in bd_high["latent_demand"]
