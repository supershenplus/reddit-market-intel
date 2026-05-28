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


def test_export_profile_lienclear_partitions_by_phase(runner, cli_db, tmp_path):
    # One Phase 1 post (waiver only), one Phase 2 post (G702), one Phase 3
    # (DocuSign + waiver). Highest-phase-wins means the DocuSign+waiver post
    # buckets under Phase 3, not Phase 1.
    _seed_post(cli_db, reddit_id="t3_p1", subreddit="Plumbing",
               title="Need a California lien waiver template for my crew")
    _seed_post(cli_db, reddit_id="t3_p2", subreddit="Construction",
               title="AIA G702 pay app rejected — schedule of values issue")
    _seed_post(cli_db, reddit_id="t3_p3", subreddit="Electricians",
               title="DocuSign for lien waivers — anyone wired it up?")
    out = tmp_path / "phases.md"

    result = runner.invoke(
        main.cli, ["export", "--profile", "lienclear", "--output", str(out)]
    )
    assert result.exit_code == 0, result.output

    report = out.read_text()
    assert "Phase 1 — Free waiver gen + SEO" in report
    assert "Phase 2 — Paid AIA pay-app + dashboard" in report
    assert "Phase 3 — Notifications + DocuSign + GC portal" in report
    # The DocuSign post bucketed into Phase 3, not Phase 1 (highest wins).
    p3_idx = report.find("Phase 3 — Notifications")
    p1_idx = report.find("Phase 1 — Free waiver gen")
    assert p3_idx > p1_idx  # phases rendered in 1,2,3 order
    docusign_idx = report.find("DocuSign for lien waivers")
    assert docusign_idx > p3_idx  # the DocuSign post appears under Phase 3


def test_analyze_rescore_niches_updates_scores(runner, cli_db):
    """Phase 4 --rescore-niches: re-runs the scorer over existing niches
    without touching the classify/cluster path. With no facets present, all
    niches route to dumb_fallback and pick up the Phase-1 score shape.
    """
    import json

    # Seed: post → pain_point → cluster → niche
    _seed_post(cli_db, reddit_id="t3_n1", subreddit="x", title="t")
    post = cli_db.get_post_by_reddit_id("t3_n1")
    _seed_pain_point(cli_db, post["id"])
    cur = cli_db.conn.execute(
        "INSERT INTO clusters (label, post_count, avg_opportunity_score, "
        "subreddits, first_seen, last_seen, trending) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("c1", 1, 0.5, "[]", "2026-05-25", "2026-05-25", 0),
    )
    cluster_id = cur.lastrowid
    cli_db.conn.execute(
        "UPDATE pain_points SET cluster_id = ? WHERE post_id = ?",
        (cluster_id, post["id"]),
    )
    niche_id = cli_db.insert_niche({
        "label": "stale label",
        "description": None, "post_count": 1, "cluster_count": 1, "sub_count": 1,
        "complexity_score": 0.99, "revenue_score": 0.99, "rank_score": 0.99,
        "saturation_note": None, "first_seen": "2026-05-25", "last_seen": "2026-05-25",
        "centroid": None,
    })
    cli_db.update_cluster_niche(cluster_id, niche_id)

    result = runner.invoke(main.cli, ["analyze", "--rescore-niches"])
    assert result.exit_code == 0, result.output
    assert "Rescored 1 niches" in result.output

    # Niche was rescored — complexity dropped from 0.99 stale → 0.5 fallback
    niche = dict(cli_db.conn.execute(
        "SELECT * FROM niches WHERE id = ?", (niche_id,),
    ).fetchone())
    assert niche["complexity_score"] == 0.5  # dumb-fallback constant
    bd = json.loads(niche["score_breakdown"])
    assert bd["mode"] == "dumb_fallback"
    from analysis.niche_scorer import BREAKDOWN_VERSION
    assert bd["breakdown_version"] == BREAKDOWN_VERSION


def test_export_profile_default_omits_domain_hit(runner, cli_db, tmp_path):
    _seed_post(cli_db, reddit_id="t3_lien", subreddit="Contractor", title=_DOMAIN_TITLE)
    out = tmp_path / "default.md"

    result = runner.invoke(main.cli, ["export", "--output", str(out)])
    assert result.exit_code == 0, result.output

    report = out.read_text()
    # Default profile is untouched by the lienclear domain-hit scan.
    assert "Domain-Hit Posts" not in report
