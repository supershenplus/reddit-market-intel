"""CRUD tests for storage/db.py using an in-memory SQLite DB."""

import time
import pytest

from storage.db import Database


@pytest.fixture
def db(tmp_path):
    """Fresh in-memory-style DB in a temp dir for each test."""
    db_file = tmp_path / "test.db"
    d = Database(db_path=db_file)
    yield d
    d.close()


def _post(reddit_id="t3_abc123", subreddit="test", title="Test post", **kwargs):
    return {
        "reddit_id": reddit_id,
        "subreddit": subreddit,
        "title": title,
        "body": kwargs.get("body", ""),
        "author": kwargs.get("author", "user1"),
        "url": kwargs.get("url", "https://reddit.com/r/test/abc123"),
        "score": kwargs.get("score", 10),
        "num_comments": kwargs.get("num_comments", 0),
        "created_utc": kwargs.get("created_utc", time.time()),
    }


def _comment(reddit_id="t1_xyz", post_reddit_id="t3_abc123", **kwargs):
    return {
        "reddit_id": reddit_id,
        "post_reddit_id": post_reddit_id,
        "parent_reddit_id": kwargs.get("parent_reddit_id", post_reddit_id),
        "author": kwargs.get("author", "commenter1"),
        "body": kwargs.get("body", "great post"),
        "score": kwargs.get("score", 5),
        "created_utc": kwargs.get("created_utc", time.time()),
        "is_me_too": kwargs.get("is_me_too", 0),
        "links_product": kwargs.get("links_product", 0),
        "product_negative": kwargs.get("product_negative", 0),
    }


class TestPostCRUD:
    def test_insert_returns_true_for_new_post(self, db):
        assert db.insert_post(_post()) is True

    def test_insert_returns_false_for_duplicate(self, db):
        db.insert_post(_post())
        assert db.insert_post(_post()) is False

    def test_post_exists_true_after_insert(self, db):
        db.insert_post(_post())
        assert db.post_exists("t3_abc123") is True

    def test_post_exists_false_for_unknown(self, db):
        assert db.post_exists("t3_unknown") is False

    def test_get_post_by_reddit_id(self, db):
        db.insert_post(_post(title="Hello world"))
        row = db.get_post_by_reddit_id("t3_abc123")
        assert row is not None
        assert row["title"] == "Hello world"

    def test_get_post_returns_none_for_missing(self, db):
        assert db.get_post_by_reddit_id("t3_missing") is None

    def test_get_posts_without_pain_points(self, db):
        db.insert_post(_post())
        posts = db.get_posts_without_pain_points()
        assert len(posts) == 1

    def test_get_posts_without_pain_points_excludes_analyzed(self, db):
        db.insert_post(_post())
        post = db.get_post_by_reddit_id("t3_abc123")
        db.insert_pain_point({
            "post_id": post["id"],
            "matched_patterns": '["seeking_tool"]',
            "intent_category": "seeking_tool",
            "opportunity_score": 0.5,
            "sentiment_intensity": 0.4,
            "validation_score": 0.3,
            "recency_weight": 0.9,
            "cross_sub_count": 1,
            "cluster_id": None,
        })
        assert db.get_posts_without_pain_points() == []


class TestCommentCRUD:
    def test_insert_comment_returns_true(self, db):
        db.insert_post(_post())
        assert db.insert_comment(_comment()) is True

    def test_insert_comment_duplicate_returns_false(self, db):
        db.insert_post(_post())
        db.insert_comment(_comment())
        assert db.insert_comment(_comment()) is False

    def test_get_comments_for_post(self, db):
        db.insert_post(_post())
        db.insert_comment(_comment(reddit_id="t1_a", score=10))
        db.insert_comment(_comment(reddit_id="t1_b", score=5))
        comments = db.get_comments_for_post("t3_abc123")
        assert len(comments) == 2
        assert comments[0]["score"] >= comments[1]["score"]  # sorted by score desc

    def test_get_comments_for_wrong_post(self, db):
        db.insert_post(_post())
        db.insert_comment(_comment())
        assert db.get_comments_for_post("t3_other") == []


class TestPainPointCRUD:
    def _insert_pain_point(self, db, post_id, score=0.5, category="seeking_tool"):
        db.insert_pain_point({
            "post_id": post_id,
            "matched_patterns": '["seeking_tool"]',
            "intent_category": category,
            "opportunity_score": score,
            "sentiment_intensity": 0.4,
            "validation_score": 0.3,
            "recency_weight": 0.9,
            "cross_sub_count": 1,
            "cluster_id": None,
        })

    def test_insert_and_get_all_pain_points(self, db):
        db.insert_post(_post())
        post = db.get_post_by_reddit_id("t3_abc123")
        self._insert_pain_point(db, post["id"])
        pps = db.get_all_pain_points()
        assert len(pps) == 1

    def test_pain_points_ordered_by_score_desc(self, db):
        db.insert_post(_post(reddit_id="t3_a"))
        db.insert_post(_post(reddit_id="t3_b"))
        post_a = db.get_post_by_reddit_id("t3_a")
        post_b = db.get_post_by_reddit_id("t3_b")
        self._insert_pain_point(db, post_a["id"], score=0.3)
        self._insert_pain_point(db, post_b["id"], score=0.8)
        pps = db.get_all_pain_points()
        assert pps[0]["opportunity_score"] >= pps[1]["opportunity_score"]

    def test_update_pain_point_score(self, db):
        db.insert_post(_post())
        post = db.get_post_by_reddit_id("t3_abc123")
        self._insert_pain_point(db, post["id"], score=0.3)
        pp_id = db.get_all_pain_points()[0]["id"]
        db.update_pain_point_score(pp_id, 0.9)
        assert db.get_all_pain_points()[0]["opportunity_score"] == pytest.approx(0.9)


class TestStats:
    def test_stats_counts(self, db):
        db.insert_post(_post())
        db.insert_comment(_comment())
        stats = db.get_stats()
        assert stats["posts"] == 1
        assert stats["comments"] == 1
        assert stats["pain_points"] == 0

    def test_stats_top_score_zero_when_no_pain_points(self, db):
        stats = db.get_stats()
        assert stats["top_score"] == 0.0
