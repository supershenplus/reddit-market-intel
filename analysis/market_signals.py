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
)

_MONO_HIGH = [re.compile(p, re.IGNORECASE) for p in MONETIZATION_HIGH_KEYWORDS]
_MONO_LOW = [re.compile(p, re.IGNORECASE) for p in MONETIZATION_LOW_KEYWORDS]
_SIMP_HIGH = [re.compile(p, re.IGNORECASE) for p in SIMPLICITY_HIGH_KEYWORDS]
_SIMP_LOW = [re.compile(p, re.IGNORECASE) for p in SIMPLICITY_LOW_KEYWORDS]


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
