"""Tests for export/seo_phrases.py (W5-8)."""

import csv
import io
import time

import pytest
from click.testing import CliRunner

import main
from export.seo_phrases import SEOPhraseReport
from storage.db import Database


@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "seo.db"
    d = Database(db_path=db_file)
    yield d
    d.close()


def _insert_post(db, reddit_id, subreddit="Construction", title="", body="", score=10):
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


def _parse_csv(text):
    return list(csv.DictReader(io.StringIO(text)))


# A small bank of lienclear domain-hit titles/bodies that share the bigram
# "lien waiver" so it surfaces as the top phrase.
_DOMAIN_POSTS = [
    ("t3_1", "California lien waiver form question",
     "Need a conditional progress lien waiver for my pay app this month"),
    ("t3_2", "Lien waiver workflow in QuickBooks",
     "We do lien waivers manually every month, slow"),
    ("t3_3", "Texas mechanics lien waiver requirements",
     "What lien waiver form does Texas require for progress payments"),
    ("t3_4", "AIA G702 pay app template",
     "Looking for a Schedule of Values template that integrates lien waiver"),
]


# --- empty / no-signal cases ---------------------------------------------------

def test_empty_corpus_returns_only_header(db):
    out = SEOPhraseReport(db).generate()
    rows = _parse_csv(out)
    assert rows == []
    assert out.startswith("phrase,frequency,avg_relevance")


def test_no_domain_hit_posts_returns_only_header(db):
    _insert_post(db, "t3_x", title="How do I bake bread", body="something")
    out = SEOPhraseReport(db).generate()
    assert _parse_csv(out) == []


# --- phrase extraction ---------------------------------------------------------

def test_lien_waiver_surfaces_as_top_phrase(db):
    for reddit_id, title, body in _DOMAIN_POSTS:
        _insert_post(db, reddit_id, title=title, body=body)

    out = SEOPhraseReport(db, min_relevance=0.1).generate()
    rows = _parse_csv(out)
    assert rows, out
    phrases = [r["phrase"] for r in rows]
    assert "lien waiver" in phrases


def test_csv_columns_present(db):
    for reddit_id, title, body in _DOMAIN_POSTS:
        _insert_post(db, reddit_id, title=title, body=body)
    out = SEOPhraseReport(db, min_relevance=0.1).generate()
    rows = _parse_csv(out)
    assert rows
    for col in ("phrase", "frequency", "avg_relevance", "sample_post_title", "sample_url"):
        assert col in rows[0]


def test_phrases_ranked_by_freq_times_relevance(db):
    for reddit_id, title, body in _DOMAIN_POSTS:
        _insert_post(db, reddit_id, title=title, body=body)
    out = SEOPhraseReport(db, min_relevance=0.1).generate()
    rows = _parse_csv(out)
    # Computed rank score = freq * avg_relevance; should be monotonically non-increasing.
    scores = [int(r["frequency"]) * float(r["avg_relevance"]) for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_top_n_limit_respected(db):
    for reddit_id, title, body in _DOMAIN_POSTS:
        _insert_post(db, reddit_id, title=title, body=body)
    out = SEOPhraseReport(db, min_relevance=0.1, top_n=3).generate()
    rows = _parse_csv(out)
    assert len(rows) <= 3


def test_min_relevance_filters_marginal_posts(db):
    # Post below threshold should not contribute its phrases.
    _insert_post(db, "t3_marginal",
                 title="Off-topic post about bread baking",
                 body="bread bread bread bread")
    for reddit_id, title, body in _DOMAIN_POSTS:
        _insert_post(db, reddit_id, title=title, body=body)

    out = SEOPhraseReport(db, min_relevance=0.30).generate()
    rows = _parse_csv(out)
    phrases = [r["phrase"] for r in rows]
    assert not any("bread" in p for p in phrases)


def test_sample_post_url_round_trips(db):
    for reddit_id, title, body in _DOMAIN_POSTS:
        _insert_post(db, reddit_id, title=title, body=body)
    out = SEOPhraseReport(db, min_relevance=0.1).generate()
    rows = _parse_csv(out)
    assert rows
    # Every row's sample_url should reference one of the seeded reddit_ids
    seeded_ids = {p[0] for p in _DOMAIN_POSTS}
    for r in rows:
        assert any(rid in r["sample_url"] for rid in seeded_ids)


# --- CLI integration -----------------------------------------------------------

@pytest.fixture
def cli_db(tmp_path, request):
    db_file = tmp_path / "cli.db"
    seed = Database(db_path=db_file)
    original = main.Database
    main.Database = lambda *a, **kw: Database(db_path=db_file)
    request.addfinalizer(lambda: setattr(main, "Database", original))
    yield seed
    seed.close()


def test_cli_writes_seo_phrase_csv(cli_db, tmp_path):
    for reddit_id, title, body in _DOMAIN_POSTS:
        _insert_post(cli_db, reddit_id, title=title, body=body)
    out = tmp_path / "seo.csv"

    result = CliRunner().invoke(
        main.cli,
        ["lienclear-seo-phrases", "--output", str(out), "--min-relevance", "0.1"],
    )
    assert result.exit_code == 0, result.output

    text = out.read_text()
    assert text.startswith("phrase,frequency,avg_relevance")
    rows = _parse_csv(text)
    assert any("lien waiver" in r["phrase"] for r in rows)
