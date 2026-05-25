"""Phase 5 — corpus-internal saturation: distinct integrations referenced
across a niche's facets.

Display-only this phase (per DECISIONS.md 2026-05-25 — corpus-internal
saturation over external API). The Plan agent further recommended no
threshold/tier logic: the operator's eyes do the heavy/light judgment.
Output is a flat sorted list of distinct tool/service names, ready to
render as a digest chip.

Inherits Phase 4's `is_pain_point=1` filter pattern — vetoed facets
get their integrations dropped (the LLM may guess integrations for
off-topic posts; counting those would inflate fake saturation).
"""

import json


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
