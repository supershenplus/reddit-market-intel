"""Corpus-internal saturation: distinct integrations referenced across a
niche's facets.

`compute_saturation` is the original display-only Phase-5 surface (still
used by the digest's body chip). `compute_saturation_score` is the W4-1
escalation: same data source, with mention-frequency weighting and a
log-decay normalization that feeds a multiplicative penalty on rank_score.

Inherits Phase 4's `is_pain_point=1` filter pattern — vetoed facets get
their integrations dropped (the LLM may guess integrations for off-topic
posts; counting those would inflate fake saturation).
"""

import json
import math
from collections import Counter


# Generic non-tool answers we sometimes get back in `current_solution`.
# Counting these as competitors would inflate saturation on every niche
# where authors say "I'm using a spreadsheet" — that's *anti*-saturation
# evidence (no incumbent tool), so it should not contribute.
_NON_TOOL_SOLUTIONS = {
    "", "nothing", "none", "n/a", "na", "manual", "manually",
    "spreadsheet", "spreadsheets", "excel", "google sheets",
    "paper", "pen and paper", "by hand",
}


def _parse_integrations(facet: dict) -> list[str]:
    raw = facet.get("integrations_mentioned")
    if not raw:
        return []
    try:
        items = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(items, list):
        return []
    return [str(x).strip() for x in items if x and str(x).strip()]


def compute_saturation(facets: list[dict]) -> dict:
    """Returns {integrations: sorted list of distinct names, count: int}.

    Filters facets to is_pain_point=1 first. Case-insensitive dedupe
    (preserves the first-seen casing for display)."""
    seen_lower = {}  # lowercase key -> first-seen original casing
    for f in facets:
        if f.get("is_pain_point") != 1:
            continue
        for name in _parse_integrations(f):
            key = name.lower()
            if key not in seen_lower:
                seen_lower[key] = name
    sorted_names = sorted(seen_lower.values(), key=lambda s: s.lower())
    return {"integrations": sorted_names, "count": len(sorted_names)}


def compute_saturation_score(
    facets: list[dict], k: float, floor: float,
) -> tuple[float, dict]:
    """W4-1 scoring surface. Log-decay over distinct tool count.

    Reads integrations_mentioned + current_solution from each is_pain_point=1
    facet. Mention frequency is preserved (a tool named in 5 posts counts
    as 5, not 1) but the saturation score is driven by *distinct* count —
    frequency only feeds the human-readable breakdown.

    Returns (score, breakdown). When no tool data exists the score is 0.0
    (no penalty), which is the right default for greenfield niches.

    Breakdown keys: distinct_count, weighted_count, top_tools (list of
    [name, count] for the 8 most-mentioned), penalty_multiplier.
    """
    counts: Counter = Counter()
    casing: dict[str, str] = {}  # lowercase → first-seen original casing

    for f in facets:
        if f.get("is_pain_point") != 1:
            continue
        for tool in _parse_integrations(f):
            key = tool.lower()
            counts[key] += 1
            if key not in casing:
                casing[key] = tool
        sol = (f.get("current_solution") or "").strip()
        if sol and sol.lower() not in _NON_TOOL_SOLUTIONS:
            key = sol.lower()
            counts[key] += 1
            if key not in casing:
                casing[key] = sol

    n_distinct = len(counts)
    weighted_count = sum(counts.values())

    if n_distinct == 0:
        return 0.0, {
            "distinct_count": 0,
            "weighted_count": 0,
            "top_tools": [],
            "penalty_multiplier": 1.0,
        }

    # n=0→0.00; n=1→0.17; n=3→0.29; n=5→0.35; n=10→0.42; n=20→0.48 (with k=0.3).
    raw = 1.0 - 1.0 / (1.0 + k * math.log(1.0 + n_distinct))
    score = max(0.0, min(1.0, raw))
    penalty = max(floor, 1.0 - score)

    top_tools = [
        [casing.get(name, name), count]
        for name, count in counts.most_common(8)
    ]

    return round(score, 4), {
        "distinct_count": n_distinct,
        "weighted_count": weighted_count,
        "top_tools": top_tools,
        "penalty_multiplier": round(penalty, 4),
    }


def format_saturation_note(breakdown: dict | None) -> str | None:
    """Human-readable summary for niches.saturation_note column. Returns
    None when no tool data exists so the column stays NULL."""
    if not breakdown or breakdown.get("distinct_count", 0) == 0:
        return None
    tools = breakdown.get("top_tools") or []
    if not tools:
        return None
    n = breakdown["distinct_count"]
    formatted = ", ".join(f"{name}({count})" for name, count in tools)
    suffix = "" if len(tools) >= n else f" +{n - len(tools)} more"
    return f"{n} distinct tools: {formatted}{suffix}"
