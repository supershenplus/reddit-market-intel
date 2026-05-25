"""Integration tests for Phase 5 — verdict capture roundtrip + digest filtering."""

import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

import main
from storage.db import Database


# --- fixtures --------------------------------------------------------------

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    db_file = tmp_path / "phase5.db"
    seed = Database(db_path=db_file)
    monkeypatch.setattr(main, "Database", lambda *a, **k: Database(db_path=db_file))
    # The digest CLI calls NicheBuilder.rebuild() which needs real clusters
    # + members + sentence-transformers. These integration tests seed
    # niches directly to focus on the verdict/kill/watch logic, so stub
    # rebuild to a no-op that reports "1 niche written" so the digest
    # command proceeds past its early-return guard.
    class _StubBuilder:
        def __init__(self, db, n_niches=15):
            pass

        def rebuild(self):
            return 1

    monkeypatch.setattr(main, "NicheBuilder", _StubBuilder)
    yield seed
    seed.close()


def _seed_niche(db, label, stable_key, rank=0.5, post_count=5, centroid_blob=None):
    """Insert a niche directly with a known stable_key."""
    return db.insert_niche({
        "label": label,
        "description": None,
        "post_count": post_count,
        "cluster_count": 1,
        "sub_count": 1,
        "complexity_score": 0.5,
        "revenue_score": rank * 1.5,
        "rank_score": rank,
        "saturation_note": None,
        "first_seen": "2026-05-25",
        "last_seen": "2026-05-25",
        "centroid": centroid_blob,
        "score_breakdown": json.dumps({"mode": "dumb_fallback"}),
        "stable_key": stable_key,
    })


# --- digest CLI: hide killed by default -----------------------------------

class TestDigestHidesKilled:
    def test_killed_niche_hidden_by_default(self, runner, cli_db, tmp_path):
        _seed_niche(cli_db, "alive A", "fp_a", rank=0.9)
        _seed_niche(cli_db, "killed B", "fp_b", rank=0.7)
        _seed_niche(cli_db, "alive C", "fp_c", rank=0.5)
        cli_db.insert_verdict({
            "subject_type": "niche", "subject_label": "killed B",
            "subject_fingerprint": "fp_b", "decision": "kill",
            "note": "noise", "snapshot_json": None,
        })
        out = tmp_path / "d.md"
        result = runner.invoke(main.cli, ["digest", "--output", str(out), "--top", "5"])
        assert result.exit_code == 0, result.output
        content = out.read_text()
        assert "alive A" in content
        assert "alive C" in content
        assert "killed B" not in content
        # Header summary mentions the hidden count
        assert "hidden: 1 killed" in content

    def test_include_killed_flag_surfaces(self, runner, cli_db, tmp_path):
        _seed_niche(cli_db, "alive A", "fp_a", rank=0.9)
        _seed_niche(cli_db, "killed B", "fp_b", rank=0.7)
        cli_db.insert_verdict({
            "subject_type": "niche", "subject_label": "killed B",
            "subject_fingerprint": "fp_b", "decision": "kill",
            "note": "noise", "snapshot_json": None,
        })
        out = tmp_path / "d.md"
        result = runner.invoke(main.cli, [
            "digest", "--include-killed", "--output", str(out), "--top", "5",
        ])
        assert result.exit_code == 0, result.output
        content = out.read_text()
        assert "killed B" in content
        assert "💀 KILLED" in content


# --- digest CLI: format v3 contents ---------------------------------------

class TestDigestV3Format:
    def test_emits_format_v3_header(self, runner, cli_db, tmp_path):
        _seed_niche(cli_db, "n1", "fp_x", rank=0.5)
        out = tmp_path / "d.md"
        result = runner.invoke(main.cli, ["digest", "--output", str(out)])
        assert result.exit_code == 0, result.output
        content = out.read_text()
        assert "<!-- digest_format: v3 -->" in content
        # Each niche gets the checkbox block + fingerprint line
        assert "[ ] build  [ ] watch  [ ] kill" in content
        assert "fingerprint: fp_x" in content


# --- digest-record CLI: roundtrip + idempotency --------------------------

class TestDigestRecordRoundtrip:
    def _digest_v3(self, niche_blocks: str) -> str:
        return (
            "<!-- digest_format: v3 -->\n"
            "# Week of 2026-05-25 — Top Niches\n\n"
            + niche_blocks
        )

    def test_kill_verdict_roundtrips(self, runner, cli_db, tmp_path):
        path = tmp_path / "edited.md"
        path.write_text(self._digest_v3(
            "## 1. doomed niche — score 0.5\n"
            "- Pain: noise\n"
            "- [ ] build  [ ] watch  [x] kill   notes: clearly noise\n"
            "- fingerprint: fp_doomed\n"
        ))
        result = runner.invoke(main.cli, ["digest-record", str(path)])
        assert result.exit_code == 0, result.output
        assert "1 new verdicts" in result.output
        latest = cli_db.get_latest_verdict_for_fingerprint("fp_doomed")
        assert latest is not None
        assert latest["decision"] == "kill"
        assert latest["note"] == "clearly noise"

    def test_replay_is_no_op(self, runner, cli_db, tmp_path):
        path = tmp_path / "edited.md"
        path.write_text(self._digest_v3(
            "## 1. niche — score 0.5\n"
            "- [x] build  [ ] watch  [ ] kill   notes: yes\n"
            "- fingerprint: fp_replay\n"
        ))
        r1 = runner.invoke(main.cli, ["digest-record", str(path)])
        assert "1 new verdicts" in r1.output
        r2 = runner.invoke(main.cli, ["digest-record", str(path)])
        assert "0 new verdicts" in r2.output
        assert "1 ignored" in r2.output
        # Only one row exists
        count = cli_db.conn.execute(
            "SELECT COUNT(*) FROM verdicts WHERE subject_fingerprint=?",
            ("fp_replay",),
        ).fetchone()[0]
        assert count == 1

    def test_refuses_non_v3_file(self, runner, cli_db, tmp_path):
        path = tmp_path / "old.md"
        path.write_text(
            "<!-- digest_format: v2 -->\n"
            "## 1. niche — score 0.5\n"
            "- [x] build  [ ] watch  [ ] kill\n"
            "- fingerprint: fp_x\n"
        )
        result = runner.invoke(main.cli, ["digest-record", str(path)])
        assert result.exit_code == 1
        assert "Refused" in result.output

    def test_watch_verdict_snapshots_state(self, runner, cli_db, tmp_path):
        # Seed niche with known shape
        _seed_niche(cli_db, "watched niche", "fp_watched",
                    rank=0.4, post_count=30)
        path = tmp_path / "edited.md"
        path.write_text(self._digest_v3(
            "## 1. watched niche — score 0.4\n"
            "- [ ] build  [x] watch  [ ] kill   notes: see if it grows\n"
            "- fingerprint: fp_watched\n"
        ))
        result = runner.invoke(main.cli, ["digest-record", str(path)])
        assert result.exit_code == 0, result.output
        snap_rows = cli_db.get_watch_verdicts_with_snapshots()
        assert "fp_watched" in snap_rows
        snap = snap_rows["fp_watched"]["snapshot"]
        assert snap["post_count"] == 30
        assert snap["rank_score"] == 0.4
