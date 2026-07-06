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
    LIENCLEAR_DIY_PATTERNS,
    LIENCLEAR_URGENCY_PATTERNS,
    LIENCLEAR_FREQUENCY_PATTERNS,
    GAMING_TOOL_REQUEST_PATTERNS,
    GAMING_DIY_PATTERNS,
    GAMING_PATREON_PATTERNS,
    GAMING_KILL_PATTERNS,
    GAMING_URGENCY_PATTERNS,
    GAMING_AUDIENCE_REACH_CEILING,
    GAMING_PATREON_MULTIPLIER,
    GAMING_KILL_MULTIPLIER,
    FORZA_DOMAIN_KEYWORDS,
    FORZA_COMPETITORS,
    FORZA_TOPIC_PATTERNS,
    FORZA_PLAYER_PATTERNS,
    FORZA_PLAYER_MULTIPLIERS,
    FORZA_RELEVANCE_WEIGHTS,
    DAILYJAPANESE_DOMAIN_KEYWORDS,
    DAILYJAPANESE_COMPETITORS,
    DAILYJAPANESE_TOPIC_PATTERNS,
    DAILYJAPANESE_LEARNER_PATTERNS,
    DAILYJAPANESE_LEARNER_MULTIPLIERS,
    DAILYJAPANESE_RELEVANCE_WEIGHTS,
    DAILYJAPANESE_WTP_PATTERNS,
    DAILYJAPANESE_KILL_PATTERNS,
    DAILYJAPANESE_URGENCY_PATTERNS,
    DAILYJAPANESE_AUDIENCE_REACH_CEILING,
    DAILYJAPANESE_WTP_MULTIPLIER,
    DAILYJAPANESE_KILL_MULTIPLIER,
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
_LC_DIY = [re.compile(p, re.IGNORECASE) for p in LIENCLEAR_DIY_PATTERNS]
_LC_URGENCY = [re.compile(p, re.IGNORECASE) for p in LIENCLEAR_URGENCY_PATTERNS]
_LC_FREQUENCY = [re.compile(p, re.IGNORECASE) for p in LIENCLEAR_FREQUENCY_PATTERNS]

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

# Gaming-base precompiled patterns (game-agnostic; reused by per-game profiles)
_GAMING_TOOL_REQ = [re.compile(p, re.IGNORECASE) for p in GAMING_TOOL_REQUEST_PATTERNS]
_GAMING_DIY      = [re.compile(p, re.IGNORECASE) for p in GAMING_DIY_PATTERNS]
_GAMING_PATREON  = [re.compile(p, re.IGNORECASE) for p in GAMING_PATREON_PATTERNS]
_GAMING_KILL     = [re.compile(p, re.IGNORECASE) for p in GAMING_KILL_PATTERNS]
_GAMING_URGENCY  = [re.compile(p, re.IGNORECASE) for p in GAMING_URGENCY_PATTERNS]

# Forza-profile precompiled patterns
_FORZA_DOMAIN = [re.compile(p, re.IGNORECASE) for p in FORZA_DOMAIN_KEYWORDS]
_FORZA_COMPETITORS = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in FORZA_COMPETITORS) + r")\b",
    re.IGNORECASE,
)
_FORZA_TOPICS = {
    topic: [re.compile(p, re.IGNORECASE) for p in patterns]
    for topic, patterns in FORZA_TOPIC_PATTERNS.items()
}
_FORZA_PLAYERS = {
    role: [re.compile(p, re.IGNORECASE) for p in patterns]
    for role, patterns in FORZA_PLAYER_PATTERNS.items()
}

# Player-role priority. Sim-racer is most specific (paid-rig owner, FFB-curious,
# highest ad-engagement); then tuner / livery_artist (creator segments);
# casual last as the catch-all. Same lock-step assert pattern as lienclear.
_FORZA_PLAYER_ORDER = ["sim_racer", "tuner", "livery_artist", "casual"]
assert set(_FORZA_PLAYER_ORDER) == set(FORZA_PLAYER_PATTERNS) == set(FORZA_PLAYER_MULTIPLIERS), (
    "Forza player facets out of sync — _FORZA_PLAYER_ORDER, FORZA_PLAYER_PATTERNS "
    "and FORZA_PLAYER_MULTIPLIERS must share identical keys"
)

# Dailyjapanese-profile precompiled patterns. Tool-request and DIY intent
# reuse the gaming base (_GAMING_TOOL_REQ / _GAMING_DIY) — those patterns
# are app-agnostic ("is there an app…", "I made a spreadsheet…"); only the
# WTP / kill / urgency layers are learning-specific.
_DJ_DOMAIN = [re.compile(p, re.IGNORECASE) for p in DAILYJAPANESE_DOMAIN_KEYWORDS]
_DJ_COMPETITORS = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in DAILYJAPANESE_COMPETITORS) + r")\b",
    re.IGNORECASE,
)
_DJ_TOPICS = {
    topic: [re.compile(p, re.IGNORECASE) for p in patterns]
    for topic, patterns in DAILYJAPANESE_TOPIC_PATTERNS.items()
}
_DJ_LEARNERS = {
    role: [re.compile(p, re.IGNORECASE) for p in patterns]
    for role, patterns in DAILYJAPANESE_LEARNER_PATTERNS.items()
}
_DJ_WTP     = [re.compile(p, re.IGNORECASE) for p in DAILYJAPANESE_WTP_PATTERNS]
_DJ_KILL    = [re.compile(p, re.IGNORECASE) for p in DAILYJAPANESE_KILL_PATTERNS]
_DJ_URGENCY = [re.compile(p, re.IGNORECASE) for p in DAILYJAPANESE_URGENCY_PATTERNS]

# Learner-level priority. Explicit N-level mentions are the most specific
# signals: N5 first (ICP), then advanced (N1/N2 — explicit outgrow signal),
# then intermediate; casual_anime last as the motivational catch-all.
_DJ_LEARNER_ORDER = ["n5_beginner", "advanced", "intermediate", "casual_anime"]
assert set(_DJ_LEARNER_ORDER) == set(DAILYJAPANESE_LEARNER_PATTERNS) == set(DAILYJAPANESE_LEARNER_MULTIPLIERS), (
    "Dailyjapanese learner facets out of sync — _DJ_LEARNER_ORDER, "
    "DAILYJAPANESE_LEARNER_PATTERNS and DAILYJAPANESE_LEARNER_MULTIPLIERS "
    "must share identical keys"
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
        "diy_evidence": [],
        "urgency": [],
        "frequency": [],
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

    # DIY workaround evidence — facet only, doesn't enter the score weight.
    # Captured pattern matches go in the returned dict so the report can
    # surface them; weight tuning deferred until corpus signal is measured.
    diy_hits = sorted({
        m.group(0) for p in _LC_DIY for m in p.finditer(text)
    })
    out["diy_evidence"] = diy_hits

    # Urgency / frequency facets (W4-2, W4-6) — same facet-only treatment.
    # Urgency = "bleeding NOW", frequency = "recurring pain". Both inform
    # WTP without changing the existing relevance score.
    out["urgency"] = sorted({
        m.group(0) for p in _LC_URGENCY for m in p.finditer(text)
    })
    out["frequency"] = sorted({
        m.group(0) for p in _LC_FREQUENCY for m in p.finditer(text)
    })

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


# ---------------------------------------------------------------------------
# Gaming profile — companion-tool discovery for game communities.
# Monetization model is free-with-ads or micro-subs, NOT paid app sales —
# audience reach replaces per-user WTP as the viability proxy.
# ---------------------------------------------------------------------------


def compute_audience_reach(subreddit: str, subscribers: int) -> float:
    """Score [0.0, 1.0] — subreddit-scale viability proxy for the ad-revenue model.

    Replaces per-user WTP as the gaming relevance signal: a free ad-supported
    tool's value scales with eyeballs reachable in the source community, not
    with what any individual would pay. Mirrors compute_market_size_score but
    recalibrated for gaming-sub scale (500K ceiling vs 10M for B2B).
    """
    if not subscribers:
        return 0.0
    return min(1.0, subscribers / GAMING_AUDIENCE_REACH_CEILING)


def compute_gaming_intent(title: str, body: str) -> dict:
    """Game-agnostic gaming-intent signals — reusable by every per-game profile.

    Returns raw pattern hits without scoring. Per-game relevance functions
    (see compute_forza_relevance) compose these with their own domain
    matching and weighting. This split lets game #2 reuse the gaming base
    without recomputing tool-request / DIY / patreon logic.
    """
    text = f"{title} {body}".strip()
    if not text:
        return {
            "tool_request_hit": False, "tool_request_matches": [],
            "diy_hit": False, "diy_matches": [],
            "patreon_hit": False, "kill_hit": False,
            "urgency_matches": [],
        }
    tool_req = sorted({m.group(0) for p in _GAMING_TOOL_REQ for m in p.finditer(text)})
    diy = sorted({m.group(0) for p in _GAMING_DIY for m in p.finditer(text)})
    patreon = any(p.search(text) for p in _GAMING_PATREON)
    kill = any(p.search(text) for p in _GAMING_KILL)
    urgency = sorted({m.group(0) for p in _GAMING_URGENCY for m in p.finditer(text)})
    return {
        "tool_request_hit": bool(tool_req),
        "tool_request_matches": tool_req,
        "diy_hit": bool(diy),
        "diy_matches": diy,
        "patreon_hit": patreon,
        "kill_hit": kill,
        "urgency_matches": urgency,
    }


def classify_forza_topic(title: str, body: str) -> int | None:
    """Bucket a post into a Forza topic (1=tuning, 2=cosmetic, 3=online, 4=progression).

    Highest-topic-wins on multi-hit — a post mentioning livery design alongside
    online championships is really a Topic-3 ask (the cosmetic layer is assumed
    already familiar by the time the user reaches for competition tools).
    Returns None if no pattern matches; the caller can default to Topic 1
    (tuning) for domain-hit posts, mirroring classify_lienclear_phase's
    Phase-1-default convention.
    """
    text = f"{title} {body}".strip()
    if not text:
        return None
    hit_topics = []
    for topic, patterns in _FORZA_TOPICS.items():
        if any(p.search(text) for p in patterns):
            hit_topics.append(topic)
    return max(hit_topics) if hit_topics else None


def compute_forza_relevance(
    title: str, body: str, subreddit: str, subscribers: int,
) -> dict:
    """Score how on-topic a post is for the Forza gaming profile.

    Parallel structure to compute_lienclear_relevance — composes shared
    gaming-intent signals with Forza-specific domain + topic + competitor
    matching. The subscribers argument feeds audience_reach (the ad-revenue
    viability proxy that replaces per-user WTP). Without a Forza-domain hit,
    the score is capped at 0.20 so generic gaming-intent posts about other
    games can't clear the export threshold.
    """
    text = f"{title} {body}".strip()
    intent = compute_gaming_intent(title, body)
    reach = compute_audience_reach(subreddit, subscribers)

    out = {
        "score": 0.0,
        "domain_hit": False,
        "domain_matches": [],
        "topic": None,
        "player_role": None,
        "competitor_mentions": [],
        "tool_request_hit": intent["tool_request_hit"],
        "tool_request_matches": intent["tool_request_matches"],
        "diy_hit": intent["diy_hit"],
        "diy_matches": intent["diy_matches"],
        "patreon_hit": intent["patreon_hit"],
        "kill_hit": intent["kill_hit"],
        "audience_reach": round(reach, 3),
        "urgency_matches": intent["urgency_matches"],
    }
    if not text:
        return out

    w = FORZA_RELEVANCE_WEIGHTS
    components: dict[str, float] = {}

    # Forza domain — required signal. Without it, score is capped (same gate
    # as compute_lienclear_relevance's domain check at the end of the function).
    domain_hits = sorted({m.group(0) for p in _FORZA_DOMAIN for m in p.finditer(text)})
    out["domain_hit"] = bool(domain_hits)
    out["domain_matches"] = domain_hits
    components["domain_hit"] = 1.0 if domain_hits else 0.0

    # Tool-request — primary signal under the ad model
    components["tool_request"] = 1.0 if intent["tool_request_hit"] else 0.0

    # DIY evidence — highest-conviction ICP signal (spreadsheet-builder = future user)
    components["diy_evidence"] = 1.0 if intent["diy_hit"] else 0.0

    # Audience reach — replaces per-user monetization weight
    components["audience_reach"] = reach

    # Named competitor mentions — light positive (active tool market = ad CPMs exist)
    comp_hits = sorted({m.group(1) for m in _FORZA_COMPETITORS.finditer(text)})
    out["competitor_mentions"] = comp_hits
    components["competitor_mention"] = min(1.0, len(comp_hits) * 0.5) if comp_hits else 0.0

    # Topic + player-role classification (facets, not weight components)
    out["topic"] = classify_forza_topic(title, body)
    detected_role = None
    for role in _FORZA_PLAYER_ORDER:
        if any(p.search(text) for p in _FORZA_PLAYERS[role]):
            detected_role = role
            break
    out["player_role"] = detected_role

    raw_score = sum(w[k] * v for k, v in components.items())

    # Domain-hit gate — without Forza vocab, the gaming-intent signals
    # could fit any game. Cap so off-domain posts can't clear the export
    # threshold while keeping the facet breakdown intact.
    if not domain_hits:
        raw_score = min(raw_score, 0.20)

    # Multipliers — applied in compounding order. Player-role first (casual
    # downweight), then Patreon bonus, then kill penalty (which dominates).
    multiplier = 1.0
    if detected_role:
        multiplier *= FORZA_PLAYER_MULTIPLIERS.get(detected_role, 1.0)
    if intent["patreon_hit"]:
        multiplier *= GAMING_PATREON_MULTIPLIER
    if intent["kill_hit"]:
        multiplier *= GAMING_KILL_MULTIPLIER

    out["score"] = round(max(0.0, min(1.0, raw_score * multiplier)), 4)
    return out


# ---------------------------------------------------------------------------
# DailyJapanese profile — learning-app overlay (validation-mode thesis).
# See the DAILYJAPANESE_* block in config.py for the model rationale.
# ---------------------------------------------------------------------------


def classify_dailyjapanese_topic(title: str, body: str) -> int | None:
    """Bucket a post into a DailyJapanese topic (1=kanji … 5=habit).

    Highest-topic-wins on multi-hit (same convention as classify_forza_topic)
    — habit & motivation is deliberately Topic 5 so a post mixing "kanji"
    with "can't stay consistent" lands on the product-defining topic for a
    daily-habit app. Returns None when no pattern matches; callers default
    domain-hit posts to Topic 1 (kanji & reading).
    """
    text = f"{title} {body}".strip()
    if not text:
        return None
    hit_topics = []
    for topic, patterns in _DJ_TOPICS.items():
        if any(p.search(text) for p in patterns):
            hit_topics.append(topic)
    return max(hit_topics) if hit_topics else None


def compute_dailyjapanese_relevance(
    title: str, body: str, subreddit: str, subscribers: int,
) -> dict:
    """Score how on-topic a post is for the DailyJapanese learning profile.

    Parallel structure to compute_forza_relevance — reuses the app-agnostic
    gaming-intent base (tool-request / DIY / urgency patterns) and composes
    it with Japanese-learning domain matching, incumbent-app mentions,
    learner-level classification, and learning-specific WTP / kill layers.
    Audience reach uses the 1M language-learning ceiling. Without a
    Japanese-learning domain hit the score is capped at 0.20 so generic
    "is there an app" posts about other subjects can't clear the export
    threshold.
    """
    text = f"{title} {body}".strip()
    intent = compute_gaming_intent(title, body)
    reach = min(1.0, subscribers / DAILYJAPANESE_AUDIENCE_REACH_CEILING) if subscribers else 0.0

    out = {
        "score": 0.0,
        "domain_hit": False,
        "domain_matches": [],
        "topic": None,
        "learner_level": None,
        "competitor_mentions": [],
        "tool_request_hit": intent["tool_request_hit"],
        "tool_request_matches": intent["tool_request_matches"],
        "diy_hit": intent["diy_hit"],
        "diy_matches": intent["diy_matches"],
        "wtp_hit": False,
        "kill_hit": False,
        "audience_reach": round(reach, 3),
        "urgency_matches": [],
    }
    if not text:
        return out

    w = DAILYJAPANESE_RELEVANCE_WEIGHTS
    components: dict[str, float] = {}

    # Japanese-learning domain — required signal (same gate as forza).
    domain_hits = sorted({m.group(0) for p in _DJ_DOMAIN for m in p.finditer(text)})
    out["domain_hit"] = bool(domain_hits)
    out["domain_matches"] = domain_hits
    components["domain_hit"] = 1.0 if domain_hits else 0.0

    # Tool-request — primary signal (every "is there an app for X" is a
    # future DailyJapanese user).
    components["tool_request"] = 1.0 if intent["tool_request_hit"] else 0.0

    # DIY evidence — highest-conviction ICP signal (custom Anki decks /
    # study spreadsheets = someone already doing the app's job by hand).
    components["diy_evidence"] = 1.0 if intent["diy_hit"] else 0.0

    # Audience reach — consumer-freemium viability proxy
    components["audience_reach"] = reach

    # Incumbent-app mentions — light positive (active app market = users
    # who already pay attention to learning apps).
    comp_hits = sorted({m.group(1) for m in _DJ_COMPETITORS.finditer(text)})
    out["competitor_mentions"] = comp_hits
    components["competitor_mention"] = min(1.0, len(comp_hits) * 0.5) if comp_hits else 0.0

    # Topic + learner-level classification (facets, not weight components)
    out["topic"] = classify_dailyjapanese_topic(title, body)
    detected_level = None
    for level in _DJ_LEARNER_ORDER:
        if any(p.search(text) for p in _DJ_LEARNERS[level]):
            detected_level = level
            break
    out["learner_level"] = detected_level

    # Learning-specific intent layers
    out["wtp_hit"] = any(p.search(text) for p in _DJ_WTP)
    out["kill_hit"] = any(p.search(text) for p in _DJ_KILL)
    out["urgency_matches"] = sorted({
        m.group(0) for p in _DJ_URGENCY for m in p.finditer(text)
    })

    raw_score = sum(w[k] * v for k, v in components.items())

    # Domain-hit gate — without Japanese-learning vocab, tool-request / DIY
    # signals fit any subject. Cap so off-domain posts can't clear the
    # export threshold while keeping the facet breakdown intact.
    if not domain_hits:
        raw_score = min(raw_score, 0.20)

    # Multipliers — learner-level first (ICP weighting), then WTP bonus,
    # then the no-app-purist kill penalty (which dominates).
    multiplier = 1.0
    if detected_level:
        multiplier *= DAILYJAPANESE_LEARNER_MULTIPLIERS.get(detected_level, 1.0)
    if out["wtp_hit"]:
        multiplier *= DAILYJAPANESE_WTP_MULTIPLIER
    if out["kill_hit"]:
        multiplier *= DAILYJAPANESE_KILL_MULTIPLIER

    out["score"] = round(max(0.0, min(1.0, raw_score * multiplier)), 4)
    return out
