"""Phase 4 — rule-based niche scoring from pain_facets.

Pure functions consumed by `analysis/niches.py:NicheBuilder` and by the
`analyze --rescore-niches` CLI path. Confidence-weighted aggregation over
the LLM-extracted facets, with a Phase-1 dumb-scorer fallback when a niche
doesn't have enough faceted evidence yet.

CRITICAL: filter_eligible drops `is_pain_point=0` rows. The LLM populates
facet fields even on vetoed posts (off-topic posts often get a domain +
willingness_to_pay guess), and unfiltered aggregation would silently
contaminate score signals. Both compute_revenue_score and
compute_complexity_score call this filter first.
"""

import json
import math

from analysis.saturation import compute_saturation_score
from config import (
    COMPLEXITY_KEYWORDS,
    COMPLEXITY_SCORE_WEIGHTS,
    FACET_CONFIDENCE_CLIP,
    NICHE_MIN_EFFECTIVE_N,
    REVENUE_SCORE_WEIGHTS,
    SATURATION_K,
    SATURATION_PENALTY_FLOOR,
)


# v2 (2026-05-28): adds saturation key to breakdown + multiplicative penalty
# on rank. v1 breakdowns remain readable — verdict-parser tolerates drift.
BREAKDOWN_VERSION = "v2"

_WTP_VALUE = {"would_pay": 1.0, "hesitant": 0.5, "no_signal": 0.0}
_URGENCY_VALUE = {
    "blocking": 1.0, "recurring": 0.7, "nice_to_have": 0.3, "none": 0.0,
}
_MARKET_REVENUE_VALUE = {
    "enterprise": 1.0, "smb": 0.7, "prosumer": 0.3, "hobbyist": 0.1,
}
_MARKET_COMPLEXITY_VALUE = {
    "enterprise": 1.0, "smb": 0.6, "prosumer": 0.3, "hobbyist": 0.1,
}
_BUYER_ROLE_VALUE = {
    "owner": 1.0, "finance": 1.0, "it": 1.0, "manager": 1.0,
    "individual_contributor": 0.4,
}

# log10($) normalization for max_dollar_anchor. $10 -> 0.0, $10000+ -> 1.0.
_DOLLAR_LOG_MIN = math.log10(10.0)
_DOLLAR_LOG_MAX = math.log10(10000.0)


# --- core helpers ----------------------------------------------------------

def filter_eligible(facets: list[dict]) -> list[dict]:
    """Drop is_pain_point=0 facets. The critical-bug guard — see module docstring."""
    return [f for f in facets if f.get("is_pain_point") == 1]


def clipped_confidence(facet: dict) -> float:
    """Per-facet confidence clipped to FACET_CONFIDENCE_CLIP. Lower bound
    prevents low-confidence niches from being arbitrarily depressed; upper
    bound prevents a single confident outlier from dominating ten weaker
    agreements."""
    raw = facet.get("confidence")
    if raw is None:
        raw = 0.5
    lo, hi = FACET_CONFIDENCE_CLIP
    return max(lo, min(hi, raw))


def effective_n(facets: list[dict]) -> float:
    """Sum of clipped confidences. Used to gate fallback behavior — see
    NICHE_MIN_EFFECTIVE_N in config."""
    return sum(clipped_confidence(f) for f in facets)


def _confidence_weighted_mean(facets, value_fn):
    """value_fn: facet -> float | None. Returns None when no facet contributes
    so the caller can drop the missing signal from the weighted average
    without zero-biasing the overall score."""
    num = 0.0
    den = 0.0
    for f in facets:
        v = value_fn(f)
        if v is None:
            continue
        c = clipped_confidence(f)
        num += v * c
        den += c
    if den == 0:
        return None
    return num / den


# --- signal value functions (return None when not present so the
# weighted-mean drops them rather than zero-biasing) --------------------

def _wtp_value(f):
    return _WTP_VALUE.get(f.get("willingness_to_pay"))


def _urgency_value(f):
    return _URGENCY_VALUE.get(f.get("urgency"))


def _market_revenue(f):
    return _MARKET_REVENUE_VALUE.get(f.get("market_size_signal"))


def _market_complexity(f):
    return _MARKET_COMPLEXITY_VALUE.get(f.get("market_size_signal"))


def _buyer_role_value(f):
    role = f.get("buyer_role")
    if role is None:
        return None
    return _BUYER_ROLE_VALUE.get(role, 0.0)


def _dollar_value(f):
    v = f.get("max_dollar_anchor")
    if v is None or v <= 0:
        return None
    log_v = math.log10(v)
    norm = (log_v - _DOLLAR_LOG_MIN) / (_DOLLAR_LOG_MAX - _DOLLAR_LOG_MIN)
    return max(0.0, min(1.0, norm))


def _integrations_list(f):
    raw = f.get("integrations_mentioned")
    if not raw:
        return []
    try:
        items = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        return []
    return items if isinstance(items, list) else []


def _integrations_count_value(f):
    n = len(_integrations_list(f))
    if n >= 3:
        return 1.0
    if n == 2:
        return 0.7
    if n == 1:
        return 0.4
    return 0.0


def _keyword_value(f):
    """Scan integrations_mentioned (structured) + pain_summary for any of the
    small COMPLEXITY_KEYWORDS list. Each unique hit adds 0.2 (cap 1.0)."""
    summary = (f.get("pain_summary") or "").lower()
    ints_text = " ".join(str(x).lower() for x in _integrations_list(f))
    haystack = summary + " " + ints_text
    hits = sum(1 for kw in COMPLEXITY_KEYWORDS if kw.lower() in haystack)
    return min(1.0, hits * 0.2)


# --- public scoring functions ---------------------------------------------

def compute_revenue_score(facets: list[dict]) -> tuple[float, dict]:
    """Returns (score, breakdown). Filters is_pain_point=0 internally."""
    eligible = filter_eligible(facets)
    if not eligible:
        return 0.0, {"_eligible_count": 0, "_effective_n": 0.0}

    components = {
        "willingness_to_pay": _confidence_weighted_mean(eligible, _wtp_value),
        "max_dollar_anchor":  _confidence_weighted_mean(eligible, _dollar_value),
        "market_size_signal": _confidence_weighted_mean(eligible, _market_revenue),
        "urgency":            _confidence_weighted_mean(eligible, _urgency_value),
        "buyer_role":         _confidence_weighted_mean(eligible, _buyer_role_value),
    }

    weighted = 0.0
    weight_used = 0.0
    for name, weight in REVENUE_SCORE_WEIGHTS.items():
        v = components.get(name)
        if v is None:
            continue
        weighted += v * weight
        weight_used += weight

    score = weighted / weight_used if weight_used > 0 else 0.0
    breakdown = {
        "_eligible_count": len(eligible),
        "_effective_n": round(effective_n(eligible), 3),
        **{k: round(v, 3) for k, v in components.items() if v is not None},
    }
    return round(score, 4), breakdown


def compute_complexity_score(facets: list[dict]) -> tuple[float, dict]:
    eligible = filter_eligible(facets)
    if not eligible:
        return 0.5, {"_eligible_count": 0, "_effective_n": 0.0}  # neutral

    components = {
        "integrations_count":  _confidence_weighted_mean(eligible, _integrations_count_value),
        "market_size_signal":  _confidence_weighted_mean(eligible, _market_complexity),
        "complexity_keywords": _confidence_weighted_mean(eligible, _keyword_value),
    }

    weighted = 0.0
    weight_used = 0.0
    for name, weight in COMPLEXITY_SCORE_WEIGHTS.items():
        v = components.get(name)
        if v is None:
            continue
        weighted += v * weight
        weight_used += weight

    score = weighted / weight_used if weight_used > 0 else 0.5
    breakdown = {
        "_eligible_count": len(eligible),
        "_effective_n": round(effective_n(eligible), 3),
        **{k: round(v, 3) for k, v in components.items() if v is not None},
    }
    return round(score, 4), breakdown


def has_enough_facets(facets: list[dict], cluster_post_count: int) -> bool:
    """Adaptive threshold. Niche is faceted enough when eligible count
    >= max(2, ceil(0.25 * cluster_post_count)) AND sum of clipped confidences
    >= NICHE_MIN_EFFECTIVE_N. Both gates must pass."""
    eligible = filter_eligible(facets)
    if not eligible:
        return False
    needed = max(2, math.ceil(0.25 * cluster_post_count))
    if len(eligible) < needed:
        return False
    if effective_n(eligible) < NICHE_MIN_EFFECTIVE_N:
        return False
    return True


def _fallback_reason(facets, cluster_post_count) -> str:
    eligible = filter_eligible(facets)
    if not eligible:
        return (
            f"no eligible facets (have {len(facets)} total, "
            f"0 with is_pain_point=1)"
        )
    needed = max(2, math.ceil(0.25 * cluster_post_count))
    if len(eligible) < needed:
        return (
            f"eligible_count={len(eligible)} < threshold {needed} "
            f"for cluster_post_count={cluster_post_count}"
        )
    n = effective_n(eligible)
    if n < NICHE_MIN_EFFECTIVE_N:
        return (
            f"effective_n={n:.2f} < min {NICHE_MIN_EFFECTIVE_N}"
        )
    return "unknown"


def score_niche(
    facets: list[dict],
    cluster_post_count: int,
    fallback_opportunity_avg: float,
) -> tuple[float, float, float, dict, str]:
    """Top-level scorer. Returns (revenue, complexity, rank, breakdown, mode).

    `mode` is 'faceted' or 'dumb_fallback'. Breakdown always carries
    `breakdown_version` so Phase 5 verdict analysis can detect schema drift
    the same way `prompt_version` works for facets."""
    if has_enough_facets(facets, cluster_post_count):
        rev, rev_bd = compute_revenue_score(facets)
        comp, comp_bd = compute_complexity_score(facets)
        # W4-1: saturation penalty (multiplicative, floored). Greenfield
        # niches (no tools mentioned) get penalty_multiplier=1.0 and rank
        # is unchanged — additive feature, no behavior change for them.
        sat_score, sat_bd = compute_saturation_score(
            facets, SATURATION_K, SATURATION_PENALTY_FLOOR,
        )
        rank = (rev / (1 + comp)) * sat_bd["penalty_multiplier"]
        breakdown = {
            "breakdown_version": BREAKDOWN_VERSION,
            "mode": "faceted",
            "revenue": rev_bd,
            "complexity": comp_bd,
            "saturation": {"score": sat_score, **sat_bd},
        }
        mode = "faceted"
    else:
        # Phase-1 fallback: dumb constant complexity, opportunity-score
        # average as revenue proxy. Saturation is NOT applied here — without
        # facets there's no tool data to derive it from, and using the
        # fallback path means we're already in low-confidence territory.
        rev = fallback_opportunity_avg
        comp = 0.5
        rank = rev / (1 + comp)
        breakdown = {
            "breakdown_version": BREAKDOWN_VERSION,
            "mode": "dumb_fallback",
            "fallback_reason": _fallback_reason(facets, cluster_post_count),
            "fallback_opportunity_avg": round(fallback_opportunity_avg, 4),
        }
        mode = "dumb_fallback"
    return round(rev, 4), round(comp, 4), round(rank, 4), breakdown, mode


def best_label_facet(facets: list[dict]) -> dict | None:
    """Pick the faceted member whose pain_summary should be the niche label.
    Strategy: highest clipped_confidence among is_pain_point=1 facets.
    Tie-break by raw confidence then post_id for determinism.

    Phase 4 ships with this simpler heuristic instead of centroid-similarity
    — the Plan agent noted that's more representative but requires keeping
    per-post embeddings around. Highest-confidence is a per-post quality
    proxy, good-enough for labels that the operator scans, not parses."""
    eligible = filter_eligible(facets)
    if not eligible:
        return None
    decorated = [
        (clipped_confidence(f), f.get("confidence") or 0.0, -f.get("post_id", 0), f)
        for f in eligible
    ]
    decorated.sort(reverse=True)
    return decorated[0][3]
