"""Latent-demand signal: behavioral/economic evidence of demand that does NOT
show up as verbalized willingness_to_pay.

The 2026-05-31 green-field probe proved would_pay is ~0 in under-tooled operator
markets — they vent pain but don't tool-shop ([[feedback-greenfield-wtp-absent]]).
The same posts reveal demand behaviorally. Tier 1 inferred it from `current_solution`
(a fragile substring match). Tier 2 (v0.2 facets) MEASURES it via explicit fields:
`workaround_effort` (manual/hired = effort/money already spent), `time_cost` (ongoing
burden), `solution_seeking` (asking/evaluating/switching = active intent). Combined
with urgency + a dollar anchor.

`compute_latent_demand_score` mirrors `analysis.saturation`: same is_pain_point=1
veto filter, same (score, breakdown) shape. DISPLAY-ONLY — it does not affect rank;
the digest surfaces it as a tag + an off-diagonal "green-field candidate" section.

Version-tolerant: each sub-signal is a mean over the facets that CARRY it, and the
blend renormalizes weights over the sub-signals that have any data. So v0.1 facets
(missing the v0.2 fields) still score sanely on {workaround-via-current_solution,
urgency, dollar} instead of being zero-dragged, and v0.2 facets use all five.

Self-contained (no import from niche_scorer) to avoid a circular import.
"""

_URGENCY_VALUE = {
    "blocking": 1.0, "recurring": 0.7, "nice_to_have": 0.3, "none": 0.0,
}
_WORKAROUND_VALUE = {"none": 0.0, "manual": 0.6, "hired": 1.0}
_TIME_COST_VALUE = {"none": 0.0, "light": 0.3, "moderate": 0.6, "heavy": 1.0}
_SEEKING_VALUE = {
    "none": 0.0, "asking": 0.6, "evaluating": 1.0, "switching": 1.0,
}


def _workaround_value(f, manual_terms):
    """v0.2 workaround_effort when present; else fall back to a manual-term match
    on current_solution (v0.1). Returns None when neither yields a signal."""
    w = f.get("workaround_effort")
    if w in _WORKAROUND_VALUE:
        return _WORKAROUND_VALUE[w]
    sol = (f.get("current_solution") or "").strip().lower()
    if not sol:
        return None
    if any(term in sol for term in manual_terms):
        return _WORKAROUND_VALUE["manual"]
    return 0.0  # a named tool or "nothing" → no manual/labor workaround signal


def _mean(values):
    present = [v for v in values if v is not None]
    return (sum(present) / len(present)) if present else None


def compute_latent_demand_score(
    facets: list[dict], weights: dict, manual_terms: set,
) -> tuple[float, dict]:
    """Returns (score, breakdown) over is_pain_point=1 facets.

    score blends five sub-signals, renormalizing over those with any data:
    workaround_effort, time_cost, solution_seeking (v0.2 fields; the last two
    drop out on v0.1 facets), urgency, dollar_present. 0.0 when no eligible facets.
    """
    eligible = [f for f in facets if f.get("is_pain_point") == 1]
    if not eligible:
        return 0.0, {
            "workaround_mean": 0.0, "workaround_count": 0,
            "time_cost_mean": 0.0, "time_cost_n": 0,
            "solution_seeking_mean": 0.0, "solution_seeking_n": 0,
            "urgency_mean": 0.0, "dollar_present_frac": 0.0,
            "eligible_count": 0,
        }

    workaround_vals = [_workaround_value(f, manual_terms) for f in eligible]
    time_cost_vals = [_TIME_COST_VALUE.get(f.get("time_cost")) for f in eligible]
    seeking_vals = [_SEEKING_VALUE.get(f.get("solution_seeking")) for f in eligible]
    urgency_vals = [_URGENCY_VALUE.get(f.get("urgency")) for f in eligible]
    # dollar is defined for every facet (max_dollar_anchor present or not).
    dollar_vals = [1.0 if (f.get("max_dollar_anchor") or 0) > 0 else 0.0
                   for f in eligible]

    sub_means = {
        "workaround_effort": _mean(workaround_vals),
        "time_cost": _mean(time_cost_vals),
        "solution_seeking": _mean(seeking_vals),
        "urgency": _mean(urgency_vals),
        "dollar_present": _mean(dollar_vals),
    }

    num = 0.0
    den = 0.0
    for name, m in sub_means.items():
        if m is None:
            continue
        num += weights[name] * m
        den += weights[name]
    score = (num / den) if den > 0 else 0.0
    score = max(0.0, min(1.0, score))

    return round(score, 4), {
        "workaround_mean": round(sub_means["workaround_effort"] or 0.0, 4),
        "workaround_count": sum(1 for v in workaround_vals if v and v > 0),
        "time_cost_mean": round(sub_means["time_cost"] or 0.0, 4),
        "time_cost_n": sum(1 for v in time_cost_vals if v is not None),
        "solution_seeking_mean": round(sub_means["solution_seeking"] or 0.0, 4),
        "solution_seeking_n": sum(1 for v in seeking_vals if v is not None),
        "urgency_mean": round(sub_means["urgency"] or 0.0, 4),
        "dollar_present_frac": round(sub_means["dollar_present"] or 0.0, 4),
        "eligible_count": len(eligible),
    }
