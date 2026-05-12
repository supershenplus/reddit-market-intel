"""Opportunity scoring engine for pain points."""

import math
import time

from config import SCORING_WEIGHTS, INTENT_WEIGHTS, RECENCY_HALF_LIFE_DAYS


class OpportunityScorer:
    """Computes composite opportunity score for a pain point."""

    def __init__(self, max_reddit_score: int = 500):
        """
        Args:
            max_reddit_score: Used to normalize Reddit upvotes to 0-1 range.
                              Adjust based on subreddit size.
        """
        self.max_reddit_score = max_reddit_score

    def score(
        self,
        reddit_score: int,
        sentiment_intensity: float,
        validation_score: float,
        cross_sub_count: int,
        intent_category: str,
        created_utc: float,
    ) -> float:
        """Compute composite opportunity score.

        Returns float in [0.0, 1.0].
        """
        w = SCORING_WEIGHTS

        # Normalize reddit score (log scale to handle outliers)
        norm_reddit = min(1.0, math.log1p(max(0, reddit_score)) / math.log1p(self.max_reddit_score))

        # Cross-subreddit multiplier: 1 sub = 0.3, 2 = 0.6, 3+ = 1.0
        cross_sub_mult = min(1.0, 0.3 * cross_sub_count)

        # Intent weight
        intent_w = INTENT_WEIGHTS.get(intent_category, 0.5)

        # Recency weight: exponential decay with half-life
        days_old = (time.time() - created_utc) / 86400.0
        recency = math.exp(-0.693 * days_old / RECENCY_HALF_LIFE_DAYS)

        # Composite score
        score = (
            w["reddit_score"] * norm_reddit
            + w["sentiment_intensity"] * sentiment_intensity
            + w["validation_score"] * validation_score
            + w["cross_sub_multiplier"] * cross_sub_mult
            + w["intent_weight"] * intent_w
            + w["recency_weight"] * recency
        )

        return max(0.0, min(1.0, score))

    def compute_recency_weight(self, created_utc: float) -> float:
        """Compute just the recency weight for storage."""
        days_old = (time.time() - created_utc) / 86400.0
        return math.exp(-0.693 * days_old / RECENCY_HALF_LIFE_DAYS)
