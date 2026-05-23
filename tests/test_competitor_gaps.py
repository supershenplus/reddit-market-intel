"""Tests for export/competitor_gaps.py (W5-7)."""

import json
import time

import pytest
from click.testing import CliRunner

import main
from export.competitor_gaps import CompetitorGapReport
from storage.db import Database


@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "cg.db"
    d = Database(db_path=db_file)
    yield d
    d.close()


def _insert_post(db, reddit_id, subreddit="Construction", title="Test", body="", score=10):
    db.insert_post({
        "reddit_id": reddit_id,
        "subreddit": subreddit,
        "title": title,
        "body": body,
        "author": "u1",
        "url": f"https://reddit.com/r/{subreddit}/{reddit_id}",
        "score": score,
        "num_comments": 0,
        "created_utc": time.time(),
    })
    return db.get_post_by_reddit_id(reddit_id)


def _insert_pp(db, post_id, competitors=None, lc_score=0.5, opp_score=0.5):
    lc = {
        "score": lc_score,
        "states": [],
        "dollar_anchors": [],
        "role": None,
        "competitor_mentions": competitors or [],
        "domain_hit": True,
    }
    db.insert_pain_point({
        "post_id": post_id,
        "matched_patterns": json.dumps({"intent": ["seeking_tool"], "lienclear": lc}),
        "intent_category": "seeking_tool",
        "opportunity_score": opp_score,
        "sentiment_intensity": 0.4,
        "validation_score": 0.3,
        "recency_weight": 0.9,
        "cross_sub_count": 1,
        "cluster_id": None,
        "monetization_score": 0.5,
        "solution_simplicity": 0.5,
        "market_size_score": 0.3,
    })


def _insert_comment(db, post_reddit_id, body, score=5, product_negative=1, reddit_id=None):
    db.insert_comment({
        "reddit_id": reddit_id or f"t1_{body[:8]}",
        "post_reddit_id": post_reddit_id,
        "parent_reddit_id": post_reddit_id,
        "author": "c1",
        "body": body,
        "score": score,
        "created_utc": time.time(),
        "is_me_too": 0,
        "links_product": 0,
        "product_negative": product_negative,
    })


# --- aggregation ----------------------------------------------------------------

def test_empty_db_returns_explanatory_report(db):
    out = CompetitorGapReport(db).generate()
    assert "No competitor mentions" in out


def test_single_competitor_mention_surfaces(db):
    p = _insert_post(db, "t3_a", title="Procore too expensive for my crew")
    _insert_pp(db, p["id"], competitors=["Procore"])

    out = CompetitorGapReport(db).generate()
    assert "Procore" in out
    assert "1 mention" in out
    assert "Procore too expensive for my crew" in out


def test_mention_counts_aggregate_across_posts(db):
    for i, comp in enumerate(["Procore", "Procore", "Levelset"]):
        p = _insert_post(db, f"t3_{i}", title=f"post {i}")
        _insert_pp(db, p["id"], competitors=[comp])

    out = CompetitorGapReport(db).generate()
    assert "Procore** — 2 mentions" in out
    assert "Levelset** — 1 mention" in out


def test_unknown_competitor_string_filtered(db):
    p = _insert_post(db, "t3_x")
    _insert_pp(db, p["id"], competitors=["NotAComp", "Procore"])

    counts = CompetitorGapReport(db)._mention_counts()
    assert counts["Procore"] == 1
    assert "NotAComp" not in counts


def test_canonical_casing_preserved(db):
    p = _insert_post(db, "t3_y")
    _insert_pp(db, p["id"], competitors=["procore"])  # lowercase from extraction

    out = CompetitorGapReport(db).generate()
    assert "## Procore" in out  # canonical casing from LIENCLEAR_COMPETITORS


# --- top posts ------------------------------------------------------------------

def test_top_posts_ordered_by_opportunity_score(db):
    p_lo = _insert_post(db, "t3_lo", title="low score post")
    _insert_pp(db, p_lo["id"], competitors=["Procore"], opp_score=0.1)
    p_hi = _insert_post(db, "t3_hi", title="high score post")
    _insert_pp(db, p_hi["id"], competitors=["Procore"], opp_score=0.9)

    posts = CompetitorGapReport(db)._top_posts_for_competitor("Procore")
    assert posts[0]["title"] == "high score post"


def test_posts_per_competitor_limit(db):
    for i in range(7):
        p = _insert_post(db, f"t3_{i}", title=f"post {i}")
        _insert_pp(db, p["id"], competitors=["Procore"])
    posts = CompetitorGapReport(db, posts_per_competitor=3)._top_posts_for_competitor("Procore")
    assert len(posts) == 3


# --- negative quotes ------------------------------------------------------------

def test_negative_quotes_word_boundary(db):
    p = _insert_post(db, "t3_q")
    _insert_pp(db, p["id"], competitors=["Handle.com"])
    _insert_comment(db, "t3_q", "Handle.com slow & buggy", reddit_id="t1_a", score=10)
    # 'handled' shouldn't match the 'Handle' competitor (word-boundary)
    _insert_comment(
        db, "t3_q", "I handled this myself with QuickBooks", reddit_id="t1_b", score=8,
    )

    quotes = CompetitorGapReport(db)._negative_quotes_for_competitor("Handle.com")
    bodies = [q["body"] for q in quotes]
    assert any("slow & buggy" in b for b in bodies)
    assert not any("handled this myself" in b for b in bodies)


def test_only_product_negative_comments_surface(db):
    p = _insert_post(db, "t3_n")
    _insert_pp(db, p["id"], competitors=["Procore"])
    _insert_comment(db, "t3_n", "Procore is great actually", reddit_id="t1_pos", product_negative=0)
    _insert_comment(db, "t3_n", "Procore broke our workflow", reddit_id="t1_neg", product_negative=1)

    quotes = CompetitorGapReport(db)._negative_quotes_for_competitor("Procore")
    bodies = [q["body"] for q in quotes]
    assert any("broke our workflow" in b for b in bodies)
    assert not any("great actually" in b for b in bodies)


# --- CLI integration ------------------------------------------------------------

@pytest.fixture
def cli_db(tmp_path, request):
    """Temp DB wired into the CLI via finalizer-based attr swap."""
    db_file = tmp_path / "cli.db"
    seed = Database(db_path=db_file)
    original = main.Database
    main.Database = lambda *a, **kw: Database(db_path=db_file)
    request.addfinalizer(lambda: setattr(main, "Database", original))
    yield seed
    seed.close()


def test_cli_writes_competitor_gap_report(cli_db, tmp_path):
    p = _insert_post(cli_db, "t3_cli", title="Procore is too expensive")
    _insert_pp(cli_db, p["id"], competitors=["Procore"])
    out = tmp_path / "gaps.md"

    result = CliRunner().invoke(
        main.cli, ["lienclear-competitor-gaps", "--output", str(out)],
    )
    assert result.exit_code == 0, result.output

    report = out.read_text()
    assert "# Lienclear Competitor Gap Report" in report
    assert "Procore" in report
