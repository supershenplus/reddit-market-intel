"""Tests for analysis/cluster_delta.py (W5-11)."""

import json
import time

import pytest
from click.testing import CliRunner

import main
from analysis.cluster_delta import (
    save_snapshot,
    load_snapshot,
    snapshot_path,
    compute_delta,
    render_delta_report,
    SCORE_DELTA_THRESHOLD,
)
from storage.db import Database


@pytest.fixture
def db(tmp_path, temp_snapshot_dir):
    db_file = tmp_path / "delta.db"
    d = Database(db_path=db_file)
    yield d
    d.close()


@pytest.fixture
def temp_snapshot_dir(tmp_path, request):
    """Redirect SNAPSHOT_DIR so tests don't touch real data/ directory."""
    import analysis.cluster_delta as cd
    original = cd.SNAPSHOT_DIR
    cd.SNAPSHOT_DIR = tmp_path / "cluster_snapshots"
    request.addfinalizer(lambda: setattr(cd, "SNAPSHOT_DIR", original))
    yield cd.SNAPSHOT_DIR


def _seed_cluster(db, label, post_count=3, avg_score=0.5, subreddits='["Construction"]'):
    db.conn.execute(
        """INSERT INTO clusters (label, post_count, avg_opportunity_score,
           subreddits, first_seen, last_seen, trending)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (label, post_count, avg_score, subreddits, "2026-05-01", "2026-05-23", 0),
    )
    db.conn.commit()


# --- snapshot save/load ----------------------------------------------------------

def test_save_snapshot_creates_file(db, temp_snapshot_dir):
    _seed_cluster(db, "lien waiver template")
    path = save_snapshot(db, "2026-05-23")
    assert path.exists()
    payload = json.loads(path.read_text())
    assert "snapshotted_at" in payload
    assert len(payload["clusters"]) == 1
    assert payload["clusters"][0]["label"] == "lien waiver template"


def test_snapshot_path_defaults_to_today(temp_snapshot_dir):
    from datetime import date
    p = snapshot_path()
    assert p.name == f"{date.today().isoformat()}.json"


def test_load_snapshot_missing_file_returns_empty(temp_snapshot_dir, tmp_path):
    assert load_snapshot(tmp_path / "nonexistent.json") == []


def test_save_then_load_round_trips(db, temp_snapshot_dir):
    _seed_cluster(db, "AIA G702", post_count=5, avg_score=0.7)
    path = save_snapshot(db, "2026-05-23")
    loaded = load_snapshot(path)
    assert len(loaded) == 1
    assert loaded[0]["label"] == "AIA G702"
    assert loaded[0]["post_count"] == 5


# --- compute_delta ---------------------------------------------------------------

def test_new_cluster_in_current_only(db):
    baseline = []
    current = [{"label": "new pain", "post_count": 3, "avg_opportunity_score": 0.4}]
    delta = compute_delta(current, baseline)
    assert len(delta["new"]) == 1
    assert delta["new"][0]["label"] == "new pain"


def test_dead_cluster_in_baseline_only(db):
    baseline = [{"label": "old pain", "post_count": 3, "avg_opportunity_score": 0.4}]
    current = []
    delta = compute_delta(current, baseline)
    assert len(delta["dead"]) == 1
    assert delta["dead"][0]["label"] == "old pain"


def test_grown_cluster_post_count_increased(db):
    baseline = [{"label": "lien waiver", "post_count": 3, "avg_opportunity_score": 0.4}]
    current = [{"label": "lien waiver", "post_count": 8, "avg_opportunity_score": 0.4}]
    delta = compute_delta(current, baseline)
    assert len(delta["grown"]) == 1
    assert delta["grown"][0]["delta_posts"] == 5
    assert delta["grown"][0]["baseline_posts"] == 3
    assert delta["grown"][0]["current_posts"] == 8


def test_unchanged_post_count_not_grown(db):
    baseline = [{"label": "lien waiver", "post_count": 3, "avg_opportunity_score": 0.4}]
    current = [{"label": "lien waiver", "post_count": 3, "avg_opportunity_score": 0.4}]
    delta = compute_delta(current, baseline)
    assert delta["grown"] == []


def test_score_movement_above_threshold(db):
    base_score = 0.3
    current_score = base_score + SCORE_DELTA_THRESHOLD + 0.01
    baseline = [{"label": "lien waiver", "post_count": 3, "avg_opportunity_score": base_score}]
    current = [{"label": "lien waiver", "post_count": 3, "avg_opportunity_score": current_score}]
    delta = compute_delta(current, baseline)
    assert len(delta["score_changed"]) == 1
    assert delta["score_changed"][0]["delta_score"] > 0


def test_score_movement_below_threshold_ignored(db):
    baseline = [{"label": "lien waiver", "post_count": 3, "avg_opportunity_score": 0.30}]
    current = [{"label": "lien waiver", "post_count": 3, "avg_opportunity_score": 0.35}]
    delta = compute_delta(current, baseline)
    assert delta["score_changed"] == []


def test_buckets_ordered_descending(db):
    baseline = [
        {"label": "a", "post_count": 1, "avg_opportunity_score": 0.1},
        {"label": "b", "post_count": 1, "avg_opportunity_score": 0.1},
    ]
    current = [
        {"label": "a", "post_count": 5, "avg_opportunity_score": 0.1},   # +4
        {"label": "b", "post_count": 10, "avg_opportunity_score": 0.1},  # +9
    ]
    delta = compute_delta(current, baseline)
    assert [g["label"] for g in delta["grown"]] == ["b", "a"]


# --- render_delta_report --------------------------------------------------------

def test_empty_delta_renders_no_changes_message():
    delta = {"new": [], "grown": [], "dead": [], "score_changed": []}
    report = render_delta_report(delta, baseline_date="2026-05-01")
    assert "No cluster changes since baseline" in report


def test_report_includes_all_section_headers_when_populated():
    delta = {
        "new": [{"label": "new lien tool", "post_count": 4, "avg_opportunity_score": 0.55}],
        "grown": [{"label": "lien waiver", "baseline_posts": 2, "current_posts": 7,
                   "delta_posts": 5, "current_score": 0.6}],
        "dead": [{"label": "old cluster", "post_count": 3, "avg_opportunity_score": 0.45}],
        "score_changed": [{"label": "AIA pay app", "baseline_score": 0.3,
                           "current_score": 0.5, "delta_score": 0.2}],
    }
    report = render_delta_report(delta, baseline_date="2026-04-01")
    assert "## New Clusters" in report
    assert "## Grown Clusters" in report
    assert "## Dead Clusters" in report
    assert "## Score Movement" in report
    assert "new lien tool" in report
    assert "+5" in report
    assert "old cluster" in report
    assert "↑ 0.20" in report or "↑ 0.2" in report


# --- CLI integration ------------------------------------------------------------

@pytest.fixture
def cli_db(tmp_path, request):
    db_file = tmp_path / "cli.db"
    seed = Database(db_path=db_file)
    original = main.Database
    main.Database = lambda *a, **kw: Database(db_path=db_file)
    request.addfinalizer(lambda: setattr(main, "Database", original))
    yield seed
    seed.close()


def test_snapshot_cli_writes_file(cli_db, temp_snapshot_dir):
    _seed_cluster(cli_db, "lien waiver")
    result = CliRunner().invoke(main.cli, ["snapshot", "--date", "2026-05-23"])
    assert result.exit_code == 0, result.output
    assert (temp_snapshot_dir / "2026-05-23.json").exists()


def test_delta_cli_against_baseline(cli_db, temp_snapshot_dir, tmp_path):
    # Snapshot baseline with one cluster.
    _seed_cluster(cli_db, "lien waiver", post_count=2)
    runner = CliRunner()
    res1 = runner.invoke(main.cli, ["snapshot", "--date", "2026-04-01"])
    assert res1.exit_code == 0, res1.output

    # Add a new cluster; grow the existing one.
    cli_db.conn.execute("UPDATE clusters SET post_count = 6 WHERE label = ?", ("lien waiver",))
    _seed_cluster(cli_db, "AIA pay app", post_count=4, avg_score=0.55)
    cli_db.conn.commit()

    out = tmp_path / "delta.md"
    res2 = runner.invoke(
        main.cli, ["delta", "--baseline", "2026-04-01", "--output", str(out)],
    )
    assert res2.exit_code == 0, res2.output

    report = out.read_text()
    assert "AIA pay app" in report  # new
    assert "lien waiver" in report  # grown
    assert "+4" in report  # delta_posts


def test_delta_cli_missing_baseline_fails_gracefully(cli_db, temp_snapshot_dir, tmp_path):
    out = tmp_path / "delta.md"
    result = CliRunner().invoke(
        main.cli, ["delta", "--baseline", "1999-01-01", "--output", str(out)],
    )
    assert result.exit_code == 0  # graceful exit, not crash
    assert "not found" in result.output.lower()
