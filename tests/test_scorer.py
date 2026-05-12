"""Tests for OpportunityScorer — verifies output range and weight behavior."""

import time
import pytest
from analysis.scorer import OpportunityScorer


@pytest.fixture
def scorer():
    return OpportunityScorer(max_reddit_score=500)


def _score(scorer, **kwargs):
    defaults = {
        "reddit_score": 100,
        "sentiment_intensity": 0.5,
        "validation_score": 0.5,
        "cross_sub_count": 1,
        "intent_category": "seeking_tool",
        "created_utc": time.time(),
    }
    defaults.update(kwargs)
    return scorer.score(**defaults)


class TestScorerRange:
    def test_score_in_zero_to_one(self, scorer):
        s = _score(scorer)
        assert 0.0 <= s <= 1.0

    def test_score_high_inputs_near_one(self, scorer):
        s = _score(scorer,
            reddit_score=500,
            sentiment_intensity=1.0,
            validation_score=1.0,
            cross_sub_count=10,
            intent_category="would_pay",
        )
        assert s <= 1.0
        assert s > 0.5

    def test_score_zero_inputs_low(self, scorer):
        s = _score(scorer,
            reddit_score=0,
            sentiment_intensity=0.0,
            validation_score=0.0,
            cross_sub_count=0,
            intent_category="feature_request",
            created_utc=time.time() - (365 * 86400),
        )
        assert s >= 0.0
        assert s < 0.5

    def test_score_never_negative(self, scorer):
        s = _score(scorer,
            reddit_score=-10,
            sentiment_intensity=0.0,
            validation_score=0.0,
            cross_sub_count=0,
        )
        assert s >= 0.0

    def test_score_never_exceeds_one(self, scorer):
        s = _score(scorer,
            reddit_score=999999,
            sentiment_intensity=2.0,
            validation_score=2.0,
            cross_sub_count=100,
        )
        assert s <= 1.0


class TestScorerBehavior:
    def test_higher_reddit_score_increases_result(self, scorer):
        low = _score(scorer, reddit_score=10)
        high = _score(scorer, reddit_score=400)
        assert high > low

    def test_would_pay_beats_feature_request(self, scorer):
        pay = _score(scorer, intent_category="would_pay")
        req = _score(scorer, intent_category="feature_request")
        assert pay > req

    def test_fresh_post_beats_old_post(self, scorer):
        fresh = _score(scorer, created_utc=time.time())
        old = _score(scorer, created_utc=time.time() - (180 * 86400))
        assert fresh > old

    def test_cross_sub_count_3_beats_1(self, scorer):
        single = _score(scorer, cross_sub_count=1)
        multi = _score(scorer, cross_sub_count=3)
        assert multi > single


class TestRecencyWeight:
    def test_recency_weight_in_range(self, scorer):
        w = scorer.compute_recency_weight(time.time())
        assert 0.0 <= w <= 1.0

    def test_fresh_post_recency_near_one(self, scorer):
        w = scorer.compute_recency_weight(time.time())
        assert w > 0.9

    def test_old_post_recency_near_zero(self, scorer):
        old_utc = time.time() - (365 * 86400 * 5)
        w = scorer.compute_recency_weight(old_utc)
        assert w < 0.1
