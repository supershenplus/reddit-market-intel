"""Unit tests for analysis/llm_extractor.py.

Covers: schema fingerprint stability, post selection (resume + 3-state
pre-filter), and facet validation. RAG is stubbed (no sentence-transformers
load in CI). Roundtrip + import tests live in test_llm_batch_roundtrip.py.
"""

import json
import time

import pytest

from analysis import llm_extractor
from analysis.llm_extractor import (
    FACET_FIELDS,
    _validate_and_normalize,
    schema_fingerprint,
    select_posts,
)
from storage.db import Database


# --- fixtures + stubs ------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "extractor.db"
    d = Database(db_path=db_file)
    yield d
    d.close()


class _StubRag:
    """RAG stub — classifies post as a hit when its title is in accept_titles."""

    def __init__(self, accept_titles=None):
        self.accept_titles = set(accept_titles or [])
        self.calls = 0

    def classify(self, title, body):
        self.calls += 1
        if title in self.accept_titles:
            return {
                "matched_patterns": "[]",
                "intent_category": "frustrated",
                "sentiment_intensity": 0.5,
            }
        return None


def _seed_post(db, reddit_id, title, body="", subreddit="test"):
    db.insert_post({
        "reddit_id": reddit_id,
        "subreddit": subreddit,
        "title": title,
        "body": body,
        "author": "user1",
        "url": f"https://reddit.com/{reddit_id}",
        "score": 5,
        "num_comments": 0,
        "created_utc": time.time(),
    })
    return db.get_post_by_reddit_id(reddit_id)


def _seed_facet(db, post_id, prompt_version, is_pain_point=1):
    db.upsert_pain_facet({
        "post_id": post_id,
        "prompt_version": prompt_version,
        "is_pain_point": is_pain_point,
        "pain_summary": "stub",
        "domain": "other",
        "current_solution": None,
        "integrations_mentioned": "[]",
        "dollar_anchors": "[]",
        "max_dollar_anchor": None,
        "willingness_to_pay": "no_signal",
        "urgency": "none",
        "buyer_role": None,
        "market_size_signal": None,
        "confidence": 0.5,
        "raw_response": "{}",
        "model": "stub",
        "input_tokens": None,
        "output_tokens": None,
        "mode": "batch",
        "prefilter_source": "no_filter",
    })


# --- schema fingerprint ----------------------------------------------------

class TestSchemaFingerprint:
    def test_is_deterministic(self):
        assert schema_fingerprint() == schema_fingerprint()

    def test_changes_when_fields_change(self, monkeypatch):
        baseline = schema_fingerprint()
        monkeypatch.setattr(
            llm_extractor, "FACET_FIELDS",
            FACET_FIELDS + [("new_field", "str", "added")],
        )
        assert schema_fingerprint() != baseline


# --- select_posts: resume + re-extract -------------------------------------

class TestSelectPostsResume:
    def test_skips_posts_with_current_version_facet(self, db, monkeypatch):
        # Two posts; one has a facet at current version, the other doesn't.
        p1 = _seed_post(db, "t3_a", "pain post A")
        p2 = _seed_post(db, "t3_b", "pain post B")
        monkeypatch.setattr(llm_extractor, "LLM_PROMPT_VERSION", "v0.1")
        _seed_facet(db, p1["id"], "v0.1")

        result = select_posts(db, prefilter="off", rag_classifier=None)
        ids = {p["id"] for p in result}
        assert p1["id"] not in ids
        assert p2["id"] in ids

    def test_re_extract_includes_all(self, db, monkeypatch):
        p1 = _seed_post(db, "t3_a", "pain A")
        _seed_post(db, "t3_b", "pain B")
        monkeypatch.setattr(llm_extractor, "LLM_PROMPT_VERSION", "v0.1")
        _seed_facet(db, p1["id"], "v0.1")

        result = select_posts(db, prefilter="off", re_extract=True)
        assert len(result) == 2

    def test_version_bump_widens_set(self, db, monkeypatch):
        p1 = _seed_post(db, "t3_a", "pain")
        _seed_facet(db, p1["id"], "v0.1")
        # Bump current version → post becomes "stale" → reselected
        monkeypatch.setattr(llm_extractor, "LLM_PROMPT_VERSION", "v0.2")

        result = select_posts(db, prefilter="off")
        assert any(p["id"] == p1["id"] for p in result)


# --- select_posts: 3-state pre-filter --------------------------------------

class TestSelectPostsPrefilter:
    def test_off_includes_all_candidates(self, db):
        _seed_post(db, "t3_a", "pain")
        _seed_post(db, "t3_b", "off-topic")
        result = select_posts(db, prefilter="off")
        assert len(result) == 2
        assert all(p["_prefilter"] == "no_filter" for p in result)

    def test_strict_only_rag_passing(self, db):
        _seed_post(db, "t3_a", "PAIN HIT")
        _seed_post(db, "t3_b", "noise")
        rag = _StubRag(accept_titles=["PAIN HIT"])
        result = select_posts(db, prefilter="strict", rag_classifier=rag)
        assert len(result) == 1
        assert result[0]["title"] == "PAIN HIT"
        assert result[0]["_prefilter"] == "rag_pass"

    def test_sampled_mixes_pass_and_fail(self, db):
        # 1 pass + 20 fail → sampled at 0.10 includes the pass + ~2 of fails
        _seed_post(db, "t3_pass", "PAIN HIT")
        for i in range(20):
            _seed_post(db, f"t3_fail_{i}", f"noise {i}")
        rag = _StubRag(accept_titles=["PAIN HIT"])
        result = select_posts(db, prefilter="sampled", rag_classifier=rag, sample_rate=0.10)
        sources = {p["_prefilter"] for p in result}
        assert "rag_pass" in sources
        assert "rag_fail_sampled" in sources

    def test_unknown_prefilter_raises(self, db):
        _seed_post(db, "t3_a", "x")
        with pytest.raises(ValueError, match="Unknown prefilter"):
            select_posts(db, prefilter="lol", rag_classifier=_StubRag())

    def test_max_posts_caps_result(self, db):
        for i in range(5):
            _seed_post(db, f"t3_{i}", f"post {i}")
        result = select_posts(db, prefilter="off", max_posts=2)
        assert len(result) == 2


# --- select_posts: --category filter (thesis-targeted batching) -----------

class TestCategoryFilter:
    """Verifies `--category construction` (and equivalents) intersect the
    candidate pool with SEED_SUBREDDITS[category] before prefilter applies.
    Reusable infra for any thesis-targeted batch."""

    def test_category_intersects_with_seed_subreddits(self, db):
        # Seed posts across multiple verticals; only construction subs survive.
        _seed_post(db, "t3_con1", "lien waiver question", subreddit="Construction")
        _seed_post(db, "t3_con2", "AIA G702 issue", subreddit="ConstructionManagers")
        _seed_post(db, "t3_smb", "saas pricing", subreddit="SaaS")
        _seed_post(db, "t3_ecom", "shopify problem", subreddit="ecommerce")

        result = select_posts(db, prefilter="off", category="construction")
        ids = {p["subreddit"] for p in result}
        assert "Construction" in ids
        assert "ConstructionManagers" in ids
        assert "SaaS" not in ids
        assert "ecommerce" not in ids

    def test_unknown_category_raises_value_error(self, db):
        _seed_post(db, "t3_a", "x", subreddit="Construction")
        with pytest.raises(ValueError, match="Unknown category"):
            select_posts(db, prefilter="off", category="not_a_real_category")

    def test_category_none_no_filtering(self, db):
        # Backward-compat: default (no category) behaves exactly as before.
        _seed_post(db, "t3_con", "lien", subreddit="Construction")
        _seed_post(db, "t3_smb", "saas", subreddit="SaaS")
        result = select_posts(db, prefilter="off", category=None)
        subs = {p["subreddit"] for p in result}
        assert subs == {"Construction", "SaaS"}

    def test_category_composes_with_strict_prefilter(self, db):
        # Construction post with RAG-positive title + cross-vertical post.
        # Only the construction post should survive category + RAG.
        _seed_post(db, "t3_con", "PAIN HIT", subreddit="Construction")
        _seed_post(db, "t3_smb", "PAIN HIT", subreddit="SaaS")
        rag = _StubRag(accept_titles=["PAIN HIT"])
        result = select_posts(
            db, prefilter="strict", rag_classifier=rag, category="construction",
        )
        assert len(result) == 1
        assert result[0]["subreddit"] == "Construction"

    def test_category_with_no_matching_subs_returns_empty(self, db):
        # Seed only non-construction posts.
        _seed_post(db, "t3_smb", "saas", subreddit="SaaS")
        result = select_posts(db, prefilter="off", category="construction")
        assert result == []

    def test_empty_candidates_returns_empty(self, db):
        # No posts seeded
        assert select_posts(db, prefilter="off") == []


# --- _validate_and_normalize -----------------------------------------------

class TestValidateFacet:
    def _good(self, **overrides):
        base = {
            "post_id": 42,
            "is_pain_point": True,
            "pain_summary": "A summary",
            "domain": "b2b_saas",
            "current_solution": "Excel",
            "integrations_mentioned": ["QuickBooks"],
            "dollar_anchors": ["$50/mo"],
            "max_dollar_anchor": 50.0,
            "willingness_to_pay": "would_pay",
            "urgency": "recurring",
            "buyer_role": "owner",
            "market_size_signal": "smb",
            "confidence": 0.8,
        }
        base.update(overrides)
        return base

    def test_happy_path(self):
        row = _validate_and_normalize(self._good(), "v0.1")
        assert row["post_id"] == 42
        assert row["is_pain_point"] == 1
        assert row["prompt_version"] == "v0.1"
        # array fields are JSON-encoded
        assert json.loads(row["integrations_mentioned"]) == ["QuickBooks"]
        assert json.loads(row["dollar_anchors"]) == ["$50/mo"]

    def test_missing_post_id_raises(self):
        bad = self._good()
        del bad["post_id"]
        with pytest.raises(ValueError, match="post_id"):
            _validate_and_normalize(bad, "v0.1")

    def test_missing_is_pain_point_raises(self):
        bad = self._good()
        del bad["is_pain_point"]
        with pytest.raises(ValueError, match="is_pain_point"):
            _validate_and_normalize(bad, "v0.1")

    def test_invalid_wtp_raises(self):
        with pytest.raises(ValueError, match="willingness_to_pay"):
            _validate_and_normalize(self._good(willingness_to_pay="maybe"), "v0.1")

    def test_invalid_urgency_raises(self):
        with pytest.raises(ValueError, match="urgency"):
            _validate_and_normalize(self._good(urgency="kinda"), "v0.1")

    def test_unknown_domain_normalizes_to_other(self):
        row = _validate_and_normalize(self._good(domain="gardening"), "v0.1")
        assert row["domain"] == "other"

    def test_is_pain_point_false_persists_zero(self):
        row = _validate_and_normalize(self._good(is_pain_point=False), "v0.1")
        assert row["is_pain_point"] == 0

    def test_empty_arrays_persist_as_empty_json(self):
        row = _validate_and_normalize(
            self._good(integrations_mentioned=[], dollar_anchors=[]),
            "v0.1",
        )
        assert row["integrations_mentioned"] == "[]"
        assert row["dollar_anchors"] == "[]"

    def test_null_fields_pass_through(self):
        row = _validate_and_normalize(
            self._good(
                current_solution=None, max_dollar_anchor=None,
                buyer_role=None, market_size_signal=None,
            ),
            "v0.1",
        )
        assert row["current_solution"] is None
        assert row["max_dollar_anchor"] is None
        assert row["buyer_role"] is None
        assert row["market_size_signal"] is None
