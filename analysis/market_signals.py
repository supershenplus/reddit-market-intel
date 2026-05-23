"""Market signal scorers: monetization potential, solution simplicity, market size."""

import re

from config import (
    MONETIZATION_HIGH_KEYWORDS,
    MONETIZATION_LOW_KEYWORDS,
    MONETIZATION_HIGH_SUBREDDITS,
    MONETIZATION_LOW_SUBREDDITS,
    SIMPLICITY_HIGH_KEYWORDS,
    SIMPLICITY_LOW_KEYWORDS,
    MARKET_SIZE_CEILING_SUBSCRIBERS,
    LIENCLEAR_BEACHHEAD_STATES,
    LIENCLEAR_STATUTORY_STATES,
    LIENCLEAR_DOLLAR_ANCHORS,
    LIENCLEAR_ROLE_PATTERNS,
    LIENCLEAR_COMPETITORS,
    LIENCLEAR_DOMAIN_KEYWORDS,
    LIENCLEAR_RELEVANCE_WEIGHTS,
    LIENCLEAR_ROLE_MULTIPLIERS,
    LIENCLEAR_PHASE_PATTERNS,
)

_MONO_HIGH = [re.compile(p, re.IGNORECASE) for p in MONETIZATION_HIGH_KEYWORDS]
_MONO_LOW = [re.compile(p, re.IGNORECASE) for p in MONETIZATION_LOW_KEYWORDS]
_SIMP_HIGH = [re.compile(p, re.IGNORECASE) for p in SIMPLICITY_HIGH_KEYWORDS]
_SIMP_LOW = [re.compile(p, re.IGNORECASE) for p in SIMPLICITY_LOW_KEYWORDS]

# Lienclear-profile precompiled patterns
_LC_BEACHHEAD = [re.compile(p) for p in LIENCLEAR_BEACHHEAD_STATES]
_LC_STATUTORY = [re.compile(p) for p in LIENCLEAR_STATUTORY_STATES]
_LC_DOLLAR = [re.compile(p, re.IGNORECASE) for p in LIENCLEAR_DOLLAR_ANCHORS]
_LC_DOMAIN = [re.compile(p, re.IGNORECASE) for p in LIENCLEAR_DOMAIN_KEYWORDS]
_LC_ROLES = {
    role: [re.compile(p, re.IGNORECASE) for p in patterns]
    for role, patterns in LIENCLEAR_ROLE_PATTERNS.items()
}
_LC_COMPETITORS = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in LIENCLEAR_COMPETITORS) + r")\b",
    re.IGNORECASE,
)
_LC_PHASES = {
    phase: [re.compile(p, re.IGNORECASE) for p in patterns]
    for phase, patterns in LIENCLEAR_PHASE_PATTERNS.items()
}

# Role priority order — most specific buyer role wins. Kept as an explicit list
# (not derived from dict key order) because match priority differs from config
# insertion order. The assert keeps it locked to the config dicts: a role added
# to LIENCLEAR_ROLE_PATTERNS but missed in LIENCLEAR_ROLE_MULTIPLIERS would
# otherwise score silently at the 1.0x .get() default.
_ROLE_ORDER = ["office_manager", "bookkeeper", "owner_operator", "gc", "homeowner"]
assert set(_ROLE_ORDER) == set(LIENCLEAR_ROLE_PATTERNS) == set(LIENCLEAR_ROLE_MULTIPLIERS), (
    "Lienclear role facets out of sync — _ROLE_ORDER, LIENCLEAR_ROLE_PATTERNS and "
    "LIENCLEAR_ROLE_MULTIPLIERS must share identical keys"
)


def compute_monetization_score(title: str, body: str, subreddit: str) -> float:
    """Score [0.0, 1.0] — likelihood audience will pay for a solution."""
    text = f"{title} {body}".strip()
    score = 0.5  # neutral base

    high_hits = sum(1 for p in _MONO_HIGH if p.search(text))
    low_hits = sum(1 for p in _MONO_LOW if p.search(text))

    score += min(0.4, high_hits * 0.10)
    score -= min(0.3, low_hits * 0.10)

    sub = subreddit.lower()
    if sub in {s.lower() for s in MONETIZATION_HIGH_SUBREDDITS}:
        score += 0.10
    elif sub in {s.lower() for s in MONETIZATION_LOW_SUBREDDITS}:
        score -= 0.10

    return max(0.0, min(1.0, score))


def compute_solution_simplicity(title: str, body: str) -> float:
    """Score [0.0, 1.0] — how easy to ship a solution (high = simpler = faster MVP)."""
    text = f"{title} {body}".strip()
    score = 0.5  # neutral base

    high_hits = sum(1 for p in _SIMP_HIGH if p.search(text))
    low_hits = sum(1 for p in _SIMP_LOW if p.search(text))

    score += min(0.4, high_hits * 0.10)
    score -= min(0.4, low_hits * 0.10)

    return max(0.0, min(1.0, score))


def compute_market_size_score(subscribers: int, cross_sub_count: int) -> float:
    """Score [0.0, 1.0] — proxy for TAM using subreddit subscriber count."""
    if not subscribers:
        base = 0.2
    else:
        base = min(1.0, subscribers / MARKET_SIZE_CEILING_SUBSCRIBERS)

    # Cross-sub signal: each additional subreddit adds 0.10, capped at 0.30
    cross_bonus = min(0.30, (cross_sub_count - 1) * 0.10)

    return max(0.0, min(1.0, base + cross_bonus))


def classify_lienclear_phase(title: str, body: str) -> int | None:
    """Bucket a post into a Lienclear build phase (1/2/3) by pattern hit.

    Returns None if the text matches no phase pattern (caller can default
    to Phase 1 if the post is already known to be domain-hit). Highest
    matched phase wins on multi-hit — a post mentioning AIA G702 alongside
    lien waivers is really a Phase-2 ask (the waiver layer is assumed
    to already exist when the user reaches for the pay-app form).
    """
    text = f"{title} {body}".strip()
    if not text:
        return None
    hit_phases = []
    for phase, patterns in _LC_PHASES.items():
        if any(p.search(text) for p in patterns):
            hit_phases.append(phase)
    return max(hit_phases) if hit_phases else None


def compute_lienclear_relevance(title: str, body: str, subreddit: str) -> dict:
    """Score how on-topic a post is for the Lienclear research profile.

    Returns a dict with overall score plus extracted metadata so the export
    layer can surface state/role/dollar/competitor breakdowns.
    """
    text = f"{title} {body}".strip()
    out = {
        "score": 0.0,
        "states": [],
        "dollar_anchors": [],
        "role": None,
        "competitor_mentions": [],
        "domain_hit": False,
    }
    if not text:
        return out

    w = LIENCLEAR_RELEVANCE_WEIGHTS
    components = {}

    # Domain — required signal. Without a hit, the post is off-topic.
    domain_hits = [p.pattern for p in _LC_DOMAIN if p.search(text)]
    out["domain_hit"] = bool(domain_hits)
    components["domain_hit"] = 1.0 if domain_hits else 0.0

    # State mentions — beachhead first, fall back to other statutory states.
    matched_beachhead = sorted({m.group(0) for p in _LC_BEACHHEAD for m in [p.search(text)] if m})
    matched_statutory = sorted({m.group(0) for p in _LC_STATUTORY for m in [p.search(text)] if m})
    out["states"] = matched_beachhead + matched_statutory
    if matched_beachhead:
        components["state_match"] = 1.0
    elif matched_statutory:
        components["state_match"] = 0.6
    else:
        components["state_match"] = 0.0

    # Dollar anchors near Lienclear pricing
    dollar_hits = sorted({m.group(0) for p in _LC_DOLLAR for m in p.finditer(text)})
    out["dollar_anchors"] = dollar_hits
    components["dollar_anchor"] = min(1.0, len(dollar_hits) * 0.5) if dollar_hits else 0.0

    # ICP role detection — prefer most specific buyer role found
    detected_role = None
    for role in _ROLE_ORDER:
        if any(p.search(text) for p in _LC_ROLES[role]):
            detected_role = role
            break
    out["role"] = detected_role
    if detected_role in ("office_manager", "bookkeeper", "owner_operator"):
        components["icp_role"] = 1.0
    elif detected_role in ("gc", "homeowner"):
        components["icp_role"] = 0.0
    else:
        components["icp_role"] = 0.0

    # Named competitor mentions
    comp_hits = sorted({m.group(1) for m in _LC_COMPETITORS.finditer(text)})
    out["competitor_mentions"] = comp_hits
    components["competitor_mention"] = min(1.0, len(comp_hits) * 0.5) if comp_hits else 0.0

    raw_score = sum(w[k] * v for k, v in components.items())

    # Domain keywords are the precondition signal. Without lien/AIA/waiver/retainage
    # context, state+role+dollar coincidences are noise — cap so the post can't
    # clear the export threshold while keeping the facet breakdown intact.
    if not domain_hits:
        raw_score = min(raw_score, 0.20)

    # Role multiplier — downweight GC/homeowner posts even if domain-hit
    multiplier = LIENCLEAR_ROLE_MULTIPLIERS.get(detected_role, 1.0)
    out["score"] = round(max(0.0, min(1.0, raw_score * multiplier)), 4)

    return out
