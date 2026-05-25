"""End-to-end roundtrip tests for Phase 3 batch I/O.

Exercises: export_batches → simulated operator session (write canned facets
JSON next to each batch) → import_facets → query the DB. Also covers
schema-fingerprint mismatch refusal, version-mismatch warning behavior,
idempotent re-import, partial-failure resilience, and digest veto.
"""

import json
import time
from pathlib import Path

import pytest

from analysis import llm_extractor
from analysis.llm_extractor import (
    export_batches,
    import_facets,
    schema_fingerprint,
    select_posts,
)
from export.digest import DigestWriter
from storage.db import Database


# --- shared fixtures -------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "roundtrip.db"
    d = Database(db_path=db_file)
    yield d
    d.close()


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


def _canned_facets(post_ids, *, is_pain_point=True, domain="b2b_saas"):
    """A minimal-valid facets array for the given post ids."""
    return [
        {
            "post_id": pid,
            "is_pain_point": is_pain_point,
            "pain_summary": f"summary for {pid}",
            "domain": domain,
            "current_solution": None,
            "integrations_mentioned": [],
            "dollar_anchors": [],
            "max_dollar_anchor": None,
            "willingness_to_pay": "no_signal",
            "urgency": "none",
            "buyer_role": None,
            "market_size_signal": None,
            "confidence": 0.7,
        }
        for pid in post_ids
    ]


def _write_facets_alongside(batch_dir: Path, facets: list[dict]):
    """Simulate the operator's Claude Code session: split facets by which
    batch their post_ids belong to, write batch_NNN_facets.json next to
    each batch_NNN.md."""
    manifest = json.loads((batch_dir / "manifest.json").read_text())
    for batch in manifest["batches"]:
        relevant = [f for f in facets if f["post_id"] in batch["post_ids"]]
        if not relevant:
            continue
        out = batch_dir / batch["file"].replace(".md", "_facets.json")
        out.write_text(json.dumps(relevant, indent=2), encoding="utf-8")


# --- happy-path roundtrip --------------------------------------------------

class TestRoundtrip:
    def test_full_export_import_lifecycle(self, db, tmp_path):
        posts = [_seed_post(db, f"t3_{i}", f"pain {i}") for i in range(5)]
        selected = select_posts(db, prefilter="off")
        assert len(selected) == 5

        batch_dir = export_batches(
            selected, batch_size=2, output_root=tmp_path / "batches",
        )

        # Manifest exists, has the right shape
        manifest = json.loads((batch_dir / "manifest.json").read_text())
        assert manifest["total_posts"] == 5
        assert manifest["schema_fingerprint"] == schema_fingerprint()
        assert len(manifest["batches"]) == 3  # ceil(5/2)
        assert all(b["status"] == "pending" for b in manifest["batches"])

        # Operator session: write facets next to each batch
        _write_facets_alongside(
            batch_dir, _canned_facets([p["id"] for p in posts]),
        )

        result = import_facets(batch_dir, db)
        assert result["imported"] == 5
        assert result["errors"] == []
        assert result["warnings"] == []

        # Facets in DB
        for p in posts:
            facet = db.get_current_facet(p["id"], llm_extractor.LLM_PROMPT_VERSION)
            assert facet is not None
            assert facet["is_pain_point"] == 1
            assert facet["domain"] == "b2b_saas"
            assert facet["mode"] == "batch"

        # Manifest updated in place
        manifest = json.loads((batch_dir / "manifest.json").read_text())
        assert all(b["status"] == "imported" for b in manifest["batches"])

    def test_batch_files_have_correct_sha256_in_manifest(self, db, tmp_path):
        for i in range(3):
            _seed_post(db, f"t3_{i}", f"pain {i}")
        batch_dir = export_batches(
            select_posts(db, prefilter="off"),
            batch_size=10, output_root=tmp_path / "out",
        )
        manifest = json.loads((batch_dir / "manifest.json").read_text())
        for batch in manifest["batches"]:
            import hashlib
            content = (batch_dir / batch["file"]).read_bytes()
            assert hashlib.sha256(content).hexdigest() == batch["sha256"]


# --- import validation -----------------------------------------------------

class TestImportValidation:
    def test_refuses_wrong_schema_fingerprint(self, db, tmp_path):
        _seed_post(db, "t3_a", "x")
        batch_dir = export_batches(
            select_posts(db, prefilter="off"),
            output_root=tmp_path / "out",
        )
        # Tamper the manifest fingerprint
        manifest_path = batch_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["schema_fingerprint"] = "deadbeefdeadbeef"
        manifest_path.write_text(json.dumps(manifest))

        with pytest.raises(ValueError, match="Schema fingerprint mismatch"):
            import_facets(batch_dir, db)

    def test_warns_on_version_mismatch_but_persists(self, db, tmp_path, monkeypatch):
        p = _seed_post(db, "t3_a", "pain")
        # Export at v0.1
        monkeypatch.setattr(llm_extractor, "LLM_PROMPT_VERSION", "v0.1")
        batch_dir = export_batches(
            select_posts(db, prefilter="off"),
            output_root=tmp_path / "out",
        )
        _write_facets_alongside(batch_dir, _canned_facets([p["id"]]))

        # Operator/config bumps to v0.2 before importing
        monkeypatch.setattr(llm_extractor, "LLM_PROMPT_VERSION", "v0.2")
        result = import_facets(batch_dir, db)
        assert result["imported"] == 1
        assert any("prompt_version" in w for w in result["warnings"])
        # Persisted under the manifest's v0.1, not the current v0.2
        assert db.get_current_facet(p["id"], "v0.1") is not None
        assert db.get_current_facet(p["id"], "v0.2") is None

    def test_invalid_json_facets_logs_error_continues(self, db, tmp_path):
        ids = [_seed_post(db, f"t3_{i}", f"x{i}")["id"] for i in range(2)]
        batch_dir = export_batches(
            select_posts(db, prefilter="off"),
            batch_size=1, output_root=tmp_path / "out",
        )
        # Write valid facets for batch 1, garbage for batch 2
        manifest = json.loads((batch_dir / "manifest.json").read_text())
        valid_batch = next(b for b in manifest["batches"] if ids[0] in b["post_ids"])
        bad_batch = next(b for b in manifest["batches"] if ids[1] in b["post_ids"])
        (batch_dir / valid_batch["file"].replace(".md", "_facets.json")).write_text(
            json.dumps(_canned_facets([ids[0]]))
        )
        (batch_dir / bad_batch["file"].replace(".md", "_facets.json")).write_text(
            "{not json}"
        )

        result = import_facets(batch_dir, db)
        assert result["imported"] == 1
        assert any("invalid JSON" in e for e in result["errors"])

    def test_missing_facets_file_logs_error_continues(self, db, tmp_path):
        ids = [_seed_post(db, f"t3_{i}", f"x{i}")["id"] for i in range(2)]
        batch_dir = export_batches(
            select_posts(db, prefilter="off"),
            batch_size=1, output_root=tmp_path / "out",
        )
        # Only write facets for the first batch; second is "still in progress"
        manifest = json.loads((batch_dir / "manifest.json").read_text())
        first_batch = next(b for b in manifest["batches"] if ids[0] in b["post_ids"])
        (batch_dir / first_batch["file"].replace(".md", "_facets.json")).write_text(
            json.dumps(_canned_facets([ids[0]]))
        )

        result = import_facets(batch_dir, db)
        assert result["imported"] == 1
        assert any("facets missing" in e for e in result["errors"])

    def test_sha256_mismatch_skips_batch(self, db, tmp_path):
        ids = [_seed_post(db, f"t3_{i}", f"x{i}")["id"] for i in range(1)]
        batch_dir = export_batches(
            select_posts(db, prefilter="off"),
            batch_size=10, output_root=tmp_path / "out",
        )
        # Tamper a batch file after export
        manifest = json.loads((batch_dir / "manifest.json").read_text())
        first = manifest["batches"][0]
        (batch_dir / first["file"]).write_text("CORRUPTED")
        (batch_dir / first["file"].replace(".md", "_facets.json")).write_text(
            json.dumps(_canned_facets(ids))
        )

        result = import_facets(batch_dir, db)
        assert result["imported"] == 0
        assert any("sha256 mismatch" in e for e in result["errors"])

    def test_facets_array_must_be_a_list(self, db, tmp_path):
        ids = [_seed_post(db, "t3_a", "x")["id"]]
        batch_dir = export_batches(
            select_posts(db, prefilter="off"),
            output_root=tmp_path / "out",
        )
        manifest = json.loads((batch_dir / "manifest.json").read_text())
        first = manifest["batches"][0]
        (batch_dir / first["file"].replace(".md", "_facets.json")).write_text(
            json.dumps({"not": "a list"})
        )

        result = import_facets(batch_dir, db)
        assert result["imported"] == 0
        assert any("expected a JSON array" in e for e in result["errors"])


# --- idempotency -----------------------------------------------------------

class TestImportIdempotency:
    def test_replay_does_not_duplicate(self, db, tmp_path):
        p = _seed_post(db, "t3_a", "pain")
        batch_dir = export_batches(
            select_posts(db, prefilter="off"),
            output_root=tmp_path / "out",
        )
        _write_facets_alongside(batch_dir, _canned_facets([p["id"]]))

        import_facets(batch_dir, db)
        import_facets(batch_dir, db)  # second run

        # Only one row exists per (post_id, prompt_version)
        rows = list(db.conn.execute("SELECT COUNT(*) FROM pain_facets"))
        assert rows[0][0] == 1


# --- digest veto -----------------------------------------------------------

class TestDigestVeto:
    """Phase 3's headline integration: when a current-version facet says
    is_pain_point=0, the digest hides the underlying pain_point. Pre-Phase-3
    pain_points without any facet still surface as before."""

    def _seed_full_chain(self, db, title="cluster post", veto=False):
        """Seed: post → pain_point → cluster → niche. Optionally also seed
        a current-version facet with is_pain_point=0 (the veto)."""
        post = _seed_post(db, f"t3_{title[:5]}", title)
        db.insert_pain_point({
            "post_id": post["id"],
            "matched_patterns": "[]",
            "intent_category": "frustrated",
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
        cur = db.conn.execute(
            "INSERT INTO clusters (label, post_count, avg_opportunity_score, "
            "subreddits, first_seen, last_seen, trending) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, 1, 0.5, "[]", "2026-05-25", "2026-05-25", 0),
        )
        cluster_id = cur.lastrowid
        db.conn.execute(
            "UPDATE pain_points SET cluster_id = ? WHERE post_id = ?",
            (cluster_id, post["id"]),
        )
        niche_id = db.insert_niche({
            "label": title, "description": title, "post_count": 1,
            "cluster_count": 1, "sub_count": 1,
            "complexity_score": 0.5, "revenue_score": 0.5,
            "rank_score": 0.5, "saturation_note": None,
            "first_seen": "2026-05-25", "last_seen": "2026-05-25",
            "centroid": None,
        })
        db.update_cluster_niche(cluster_id, niche_id)
        db.conn.commit()
        if veto:
            db.upsert_pain_facet({
                "post_id": post["id"],
                "prompt_version": llm_extractor.LLM_PROMPT_VERSION,
                "is_pain_point": 0,
                "pain_summary": "vetoed",
                "domain": "other", "current_solution": None,
                "integrations_mentioned": "[]", "dollar_anchors": "[]",
                "max_dollar_anchor": None, "willingness_to_pay": "no_signal",
                "urgency": "none", "buyer_role": None,
                "market_size_signal": None, "confidence": 0.9,
                "raw_response": "{}", "model": "stub",
                "input_tokens": None, "output_tokens": None,
                "mode": "batch", "prefilter_source": "no_filter",
            })
        return post, niche_id

    def test_unvetoed_pain_point_surfaces(self, db):
        self._seed_full_chain(db, title="visible_niche", veto=False)
        md = DigestWriter(db).generate(top_n=5)
        assert "visible_niche" in md
        # Has member posts in the rendered output (no "no member posts" tag)
        assert "no member posts" not in md

    def test_vetoed_pain_point_hidden_from_digest(self, db):
        self._seed_full_chain(db, title="hidden_niche", veto=True)
        md = DigestWriter(db).generate(top_n=5)
        # Niche header still renders (it's just empty now)
        assert "hidden_niche" in md
        # But its only member was vetoed, so digest renders the "no members" tag
        assert "no member posts" in md

    def test_facet_at_other_version_does_not_veto(self, db, monkeypatch):
        # Veto written at v0.0 but current version is v0.1 → no veto applies
        monkeypatch.setattr(llm_extractor, "LLM_PROMPT_VERSION", "v0.0")
        post, _ = self._seed_full_chain(db, title="version_test", veto=True)
        monkeypatch.setattr(llm_extractor, "LLM_PROMPT_VERSION", "v0.1")
        # Also bump the digest's view of "current"
        import export.digest as digest_mod
        monkeypatch.setattr(digest_mod, "LLM_PROMPT_VERSION", "v0.1")
        md = DigestWriter(db).generate(top_n=5)
        assert "no member posts" not in md
