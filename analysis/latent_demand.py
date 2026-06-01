"""Latent-demand signal: behavioral/economic evidence of demand that does NOT
show up as verbalized willingness_to_pay.

The 2026-05-31 green-field probe proved would_pay is ~0 in under-tooled operator
markets — they vent pain but don't tool-shop ([[feedback-greenfield-wtp-absent]]).
But the same posts often reveal demand behaviorally: a manual/labor workaround in
`current_solution` ("spreadsheet", "by hand", "hired a VA") means the author is
already PAYING in effort; recurring/blocking urgency means ongoing pain; a dollar
anchor means the problem has economic magnitude. Those signals are all captured in
pain_facets but feed the opportunity score NOWHERE (`current_solution` is read only
by `saturation.py`, to EXCLUDE tools from the saturation count).

`compute_latent_demand_score` mirrors `analysis.saturation`: same is_pain_point=1
veto filter, same (score, breakdown) shape. DISPLAY-ONLY this pass — it does not
affect rank; the digest surfaces it as a tag + an off-diagonal "green-field
candidate" section. The off-diagonal (high latent demand + low saturation) is the
quadrant the would_pay-driven scorer is blind to.

Self-contained (no import from niche_scorer) to avoid a circular import — the
urgency map below mirrors `niche_scorer._URGENCY_VALUE` intentionally.
"""

_URGENCY_VALUE = {
    "blocking": 1.0, "recurring": 0.7, "nice_to_have": 0.3, "none": 0.0,
}


def compute_latent_demand_score(
    facets: list[dict], weights: dict, manual_terms: set,
) -> tuple[float, dict]:
    """Returns (score, breakdown) over is_pain_point=1 facets.

    score is a weighted blend (weights sum to 1.0 → score in [0,1]) of three
    behavioral sub-signals:
      - manual_workaround_frac: fraction whose current_solution names a manual/
        labor workaround (substring match against `manual_terms`). "nothing"/
        null do NOT match → genuine no-signal, correctly excluded.
      - urgency_mean: mean urgency value over facets that carry an urgency.
      - dollar_present_frac: fraction with a positive max_dollar_anchor.

    Breakdown fields: score, manual_workaround_frac, manual_count, urgency_mean,
    dollar_present_frac, eligible_count. 0.0 when no eligible facets
    (greenfield-safe default).
    """
    eligible = [f for f in facets if f.get("is_pain_point") == 1]
    if not eligible:
        return 0.0, {
            "manual_workaround_frac": 0.0,
            "manual_count": 0,
            "urgency_mean": 0.0,
            "dollar_present_frac": 0.0,
            "eligible_count": 0,
        }

    n = len(eligible)

    manual_count = 0
    for f in eligible:
        sol = (f.get("current_solution") or "").strip().lower()
        if sol and any(term in sol for term in manual_terms):
            manual_count += 1
    manual_frac = manual_count / n

    urgency_vals = [
        _URGENCY_VALUE[f["urgency"]]
        for f in eligible
        if f.get("urgency") in _URGENCY_VALUE
    ]
    urgency_mean = sum(urgency_vals) / len(urgency_vals) if urgency_vals else 0.0

    dollar_present = sum(
        1 for f in eligible if (f.get("max_dollar_anchor") or 0) > 0
    )
    dollar_frac = dollar_present / n

    score = (
        weights["manual_workaround"] * manual_frac
        + weights["urgency"] * urgency_mean
        + weights["dollar_present"] * dollar_frac
    )
    score = max(0.0, min(1.0, score))

    return round(score, 4), {
        "manual_workaround_frac": round(manual_frac, 4),
        "manual_count": manual_count,
        "urgency_mean": round(urgency_mean, 4),
        "dollar_present_frac": round(dollar_frac, 4),
        "eligible_count": n,
    }
