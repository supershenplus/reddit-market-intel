"""Buyer-side validation gate: is a niche's pain coming from the people who
control spend, or only from the operators who feel it?

The lesson behind this module is `[[feedback-buyer-side-validation-mandatory]]`
and `[[feedback-construction-buyer-operator-split]]`: on Reddit the loudest
pain comes from individual_contributors / managers (employees, PMs), but the
purchase decision sits with owners. A niche whose `would_pay` signal is all
operator-side is a mirage — desire without authority. Lienclear died on exactly
this (41 facets, zero buyer-side).

`compute_buyer_side_score` mirrors `analysis.saturation.compute_saturation_score`:
same `is_pain_point=1` veto filter, same (score, breakdown) shape, same
multiplicative-penalty-with-floor contract feeding `score_niche`. It adds a
discrete `gate_state` so the digest can render three tiers:

    pass          — enough owner/finance would-pay evidence; no effect
    operator_only — clears the evidence bar but operator-dominated; 🚩 + penalty
    unvalidated   — too few buyer-side would-pay facets; ⛔ hard block

Inherits Phase 4's `is_pain_point=1` filter — vetoed facets (off-topic posts the
LLM still guessed a buyer_role for) must not contaminate the ratio.
"""


def compute_buyer_side_score(
    facets: list[dict],
    floor: float,
    min_buyer_evidence: int,
    buyer_roles: set[str],
    operator_roles: set[str],
    tag_threshold: float,
) -> tuple[float, dict]:
    """Returns (buyer_ratio, breakdown).

    `buyer_ratio` ∈ [0,1] is the share of role-identified pain facets that come
    from spend-controlling roles. It doubles as the breakdown `score` (mirrors
    saturation's score-in-breakdown convention).

    Breakdown fields: gate_state, buyer_ratio, n_buyer, n_operator,
    buyer_wp_count, penalty_multiplier.

    penalty_multiplier:
      - no role signal at all (n_buyer + n_operator == 0) → 1.0. We don't know,
        so we don't cut rank — the `unvalidated` gate_state carries the warning
        instead. Avoids double-punishing un-role-faceted niches.
      - else max(floor, buyer_ratio): pure-operator bottoms at floor,
        pure-buyer is 1.0 (no penalty).

    gate_state (the tiered gate):
      - 'unvalidated'   if buyer_wp_count < min_buyer_evidence (HARD block)
      - 'operator_only' elif buyer_ratio < tag_threshold        (soft tag)
      - 'pass'          otherwise
    """
    n_buyer = 0
    n_operator = 0
    buyer_wp_count = 0

    for f in facets:
        if f.get("is_pain_point") != 1:
            continue
        role = (f.get("buyer_role") or "").strip().lower()
        if role in buyer_roles:
            n_buyer += 1
            if (f.get("willingness_to_pay") or "").strip().lower() == "would_pay":
                buyer_wp_count += 1
        elif role in operator_roles:
            n_operator += 1

    denom = n_buyer + n_operator
    if denom == 0:
        buyer_ratio = 0.0
        penalty = 1.0
    else:
        buyer_ratio = n_buyer / denom
        penalty = max(floor, buyer_ratio)

    if buyer_wp_count < min_buyer_evidence:
        gate_state = "unvalidated"
    elif buyer_ratio < tag_threshold:
        gate_state = "operator_only"
    else:
        gate_state = "pass"

    return round(buyer_ratio, 4), {
        "gate_state": gate_state,
        "buyer_ratio": round(buyer_ratio, 4),
        "n_buyer": n_buyer,
        "n_operator": n_operator,
        "buyer_wp_count": buyer_wp_count,
        "penalty_multiplier": round(penalty, 4),
    }


def format_buyer_side_note(breakdown: dict | None) -> str | None:
    """Human-readable summary for any stored-column / digest body use. Returns
    None for fallback-mode breakdowns (no buyer_side entry) and for niches that
    pass cleanly with no operator presence worth noting."""
    if not breakdown:
        return None
    state = breakdown.get("gate_state")
    if state not in ("unvalidated", "operator_only"):
        return None
    n_buyer = breakdown.get("n_buyer", 0)
    n_operator = breakdown.get("n_operator", 0)
    wp = breakdown.get("buyer_wp_count", 0)
    ratio = breakdown.get("buyer_ratio", 0.0)
    if state == "unvalidated":
        return (
            f"⛔ buyer-side unvalidated: {wp} owner/finance would-pay facet(s), "
            f"{n_buyer} buyer vs {n_operator} operator"
        )
    return (
        f"🚩 operator-dominated: {ratio:.0%} buyer-side "
        f"({n_buyer} buyer vs {n_operator} operator)"
    )
