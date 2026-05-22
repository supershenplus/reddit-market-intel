"""CLI integration tests — covers `analyze --force` and `export --profile`.

Uses Click's CliRunner against `main.cli`. `main.Database` is monkeypatched so
every command hits a temp DB; the classifier and clusterer are stubbed in the
analyze tests to keep them off the sentence-transformers / ChromaDB path.
"""

import time

import pytest
from click.testing import CliRunner

import main
from storage.db import Database


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Temp DB wired into the CLI — every main.Database() call hits this file."""
    db_file = tmp_path / "cli.db"
    seed = Database(db_path=db_file)  # creates the schema
    monkeypatch.setattr(main, "Database", lambda *a, **k: Database(db_path=db_file))
    yield seed
    seed.close()


class _StubClassifier:
    """Classifier that matches nothing — keeps analyze CLI tests off the model."""

    def classify(self, title, body):
        return None


class _StubClusterer:
    """No-op clusterer stub."""

    def __init__(self, db):
        self._db = db

    def cluster(self):
        return None


def _seed_post(db, reddit_id="t3_cli", subreddit="Contractor", title="Test post", body=""):
    db.insert_post({
        "reddit_id": reddit_id,
        "subreddit": subreddit,
        "title": title,
        "body": body,
        "author": "user1",
        "url": f"https://reddit.com/r/{subreddit}/{reddit_id}",
        "score": 12,
        "num_comments": 0,
        "created_utc": time.time(),
    })
    return db.get_post_by_reddit_id(reddit_id)


def _seed_pain_point(db, post_id):
    db.insert_pain_point({
        "post_id": post_id,
        "matched_patterns": '["seeking_tool"]',
        "intent_category": "seeking_tool",
        "opportunity_score": 0.5,
        "sentiment_intensity": 0.4,
        "validation_score": 0.3,
        "recency_weight": 0.9,
        "cross_sub_count": 1,
        "cluster_id": None,
        "monetization_score": 0.5,
        "solution_simplicity": 0.5,
        "market_size_score": 0.3,
    })


def _count(db, table):
    return db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# --- analyze --force ---------------------------------------------------------

def test_analyze_force_clears_tables(runner, cli_db, monkeypatch):
    monkeypatch.setattr(main, "PainPointClassifier", _StubClassifier)
    monkeypatch.setattr(main, "PainPointClusterer", _StubClusterer)
    post = _seed_post(cli_db)
    _seed_pain_point(cli_db, post["id"])
    cli_db.conn.execute(
        "INSERT INTO clusters (label, post_count, avg_opportunity_score) VALUES (?, ?, ?)",
        ("stale cluster", 1, 0.5),
    )
    cli_db.conn.commit()
    assert _count(cli_db, "pain_points") == 1
    assert _count(cli_db, "clusters") == 1

    result = runner.invoke(main.cli, ["analyze", "--force"])
    assert result.exit_code == 0, result.output

    # --force drops both tables; the stub classifier re-creates nothing.
    assert _count(cli_db, "pain_points") == 0
    assert _count(cli_db, "clusters") == 0


def test_analyze_no_force_keeps_tables(runner, cli_db, monkeypatch):
    monkeypatch.setattr(main, "PainPointClassifier", _StubClassifier)
    monkeypatch.setattr(main, "PainPointClusterer", _StubClusterer)
    post = _seed_post(cli_db)
    _seed_pain_point(cli_db, post["id"])
    assert _count(cli_db, "pain_points") == 1

    result = runner.invoke(main.cli, ["analyze"])
    assert result.exit_code == 0, result.output

    # Without --force the existing pain_point survives.
    assert _count(cli_db, "pain_points") == 1


# --- export --profile -------------------------------------------------------

_DOMAIN_TITLE = "Best tool for generating lien waivers and AIA G702 pay applications?"


def test_export_profile_lienclear_surfaces_domain_hit(runner, cli_db, tmp_path):
    _seed_post(cli_db, reddit_id="t3_lien", subreddit="Contractor", title=_DOMAIN_TITLE)
    out = tmp_path / "lc.md"

    result = runner.invoke(
        main.cli, ["export", "--profile", "lienclear", "--output", str(out)]
    )
    assert result.exit_code == 0, result.output

    report = out.read_text()
    # The lienclear overlay engaged and the domain-hit post surfaced even though
    # it was never classified into a pain_point / cluster.
    assert "Domain-Hit Posts" in report
    assert "lien waivers" in report


def test_export_profile_default_omits_domain_hit(runner, cli_db, tmp_path):
    _seed_post(cli_db, reddit_id="t3_lien", subreddit="Contractor", title=_DOMAIN_TITLE)
    out = tmp_path / "default.md"

    result = runner.invoke(main.cli, ["export", "--output", str(out)])
    assert result.exit_code == 0, result.output

    report = out.read_text()
    # Default profile is untouched by the lienclear domain-hit scan.
    assert "Domain-Hit Posts" not in report
