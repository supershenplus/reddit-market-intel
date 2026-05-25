"""Tests for the Phase 2 scrape-all CLI + its helpers."""

from datetime import datetime, timedelta, timezone

import pytest
from click.testing import CliRunner

import main
from config import SEED_SUBREDDITS
from storage.db import Database


# --- helpers ------------------------------------------------------------------

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    db_file = tmp_path / "scrape_all.db"
    seed = Database(db_path=db_file)
    monkeypatch.setattr(main, "Database", lambda *a, **k: Database(db_path=db_file))
    yield seed
    seed.close()


class _FakeScraper:
    """Records which subs were called; returns empty payloads to keep the
    test off the network and off PRAW. The CLI only cares that
    _scrape_one_subreddit ran for the right set of subs and that
    upsert_subreddit landed an ISO timestamp."""

    def __init__(self):
        self.fetched = []

    def fetch_posts(self, subreddit, limit=100, sort="hot"):
        self.fetched.append(subreddit)
        return []

    def fetch_comments(self, post_reddit_id, limit=200):
        return []

    def get_subreddit_info(self, subreddit):
        return {"name": subreddit, "subscribers": 1234}


# --- _flatten_seed_subreddits -------------------------------------------------

class TestFlatten:
    def test_returns_all_unique_subs(self):
        pairs = main._flatten_seed_subreddits()
        subs = [s for s, _ in pairs]
        # No dups
        assert len(subs) == len(set(subs))
        # All real seeds represented
        for category, subs_list in SEED_SUBREDDITS.items():
            for sub in subs_list:
                assert sub in subs

    def test_first_category_wins_on_dup(self, monkeypatch):
        monkeypatch.setattr(
            main, "SEED_SUBREDDITS",
            {"alpha": ["dupe", "a1"], "beta": ["dupe", "b1"]},
        )
        pairs = dict(main._flatten_seed_subreddits())
        assert pairs["dupe"] == "alpha"
        assert pairs["a1"] == "alpha"
        assert pairs["b1"] == "beta"


# --- _is_scraped_within -------------------------------------------------------

class TestIsScrapedWithin:
    def test_null_is_false(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert main._is_scraped_within(None, cutoff) is False
        assert main._is_scraped_within("", cutoff) is False

    def test_legacy_now_literal_is_false(self):
        # Pre-Phase-2 code wrote the literal string "now" — treat as never-scraped.
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert main._is_scraped_within("now", cutoff) is False

    def test_recent_iso_is_true(self):
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert main._is_scraped_within(recent, cutoff) is True

    def test_old_iso_is_false(self):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert main._is_scraped_within(old, cutoff) is False

    def test_naive_iso_treated_as_utc(self):
        # Older entries may lack a tz; assume UTC rather than rejecting.
        naive = (datetime.now() - timedelta(hours=1)).isoformat()
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert main._is_scraped_within(naive, cutoff) is True


# --- scrape-all CLI -----------------------------------------------------------

class TestScrapeAllCLI:
    def _patch_seed(self, monkeypatch, mapping):
        monkeypatch.setattr(main, "SEED_SUBREDDITS", mapping)

    def test_scrapes_every_sub_when_db_empty(self, runner, cli_db, monkeypatch):
        self._patch_seed(monkeypatch, {"v1": ["sub_a", "sub_b"], "v2": ["sub_c"]})
        fake = _FakeScraper()
        monkeypatch.setattr(main, "get_scraper", lambda: fake)

        result = runner.invoke(main.cli, ["scrape-all"])
        assert result.exit_code == 0, result.output
        assert set(fake.fetched) == {"sub_a", "sub_b", "sub_c"}

    def test_skips_recently_scraped(self, runner, cli_db, monkeypatch):
        self._patch_seed(monkeypatch, {"v1": ["fresh", "stale"]})
        # Seed: "fresh" was scraped 1 hour ago; "stale" was scraped 30 days ago.
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        cli_db.upsert_subreddit({
            "name": "fresh", "subscribers": 100, "category": "v1",
            "discovered_from": None, "last_scraped": recent, "active": 1,
        })
        cli_db.upsert_subreddit({
            "name": "stale", "subscribers": 100, "category": "v1",
            "discovered_from": None, "last_scraped": old, "active": 1,
        })
        fake = _FakeScraper()
        monkeypatch.setattr(main, "get_scraper", lambda: fake)

        result = runner.invoke(main.cli, ["scrape-all", "--max-age-days", "7"])
        assert result.exit_code == 0, result.output
        assert fake.fetched == ["stale"]

    def test_max_age_zero_scrapes_everything(self, runner, cli_db, monkeypatch):
        self._patch_seed(monkeypatch, {"v1": ["fresh"]})
        recent = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        cli_db.upsert_subreddit({
            "name": "fresh", "subscribers": 100, "category": "v1",
            "discovered_from": None, "last_scraped": recent, "active": 1,
        })
        fake = _FakeScraper()
        monkeypatch.setattr(main, "get_scraper", lambda: fake)

        result = runner.invoke(main.cli, ["scrape-all", "--max-age-days", "0"])
        assert result.exit_code == 0, result.output
        # max-age-days=0 → cutoff is now → any past timestamp is "older" → re-scrape.
        assert fake.fetched == ["fresh"]

    def test_persists_iso_timestamp_not_literal_now(self, runner, cli_db, monkeypatch):
        self._patch_seed(monkeypatch, {"v1": ["sub_a"]})
        fake = _FakeScraper()
        monkeypatch.setattr(main, "get_scraper", lambda: fake)

        result = runner.invoke(main.cli, ["scrape-all"])
        assert result.exit_code == 0, result.output

        info = cli_db.get_subreddit_info("sub_a")
        assert info is not None
        # Parses back as a real datetime, not the literal "now"
        ts = info["last_scraped"]
        assert ts != "now"
        parsed = datetime.fromisoformat(ts)
        # Stamped within the last minute
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        assert (datetime.now(timezone.utc) - parsed) < timedelta(minutes=1)

    def test_continues_past_scraper_errors(self, runner, cli_db, monkeypatch):
        self._patch_seed(monkeypatch, {"v1": ["ok_a", "boom", "ok_b"]})

        class _PartiallyBroken(_FakeScraper):
            def fetch_posts(self, subreddit, limit=100, sort="hot"):
                if subreddit == "boom":
                    raise RuntimeError("simulated failure")
                return super().fetch_posts(subreddit, limit=limit, sort=sort)

        fake = _PartiallyBroken()
        monkeypatch.setattr(main, "get_scraper", lambda: fake)

        result = runner.invoke(main.cli, ["scrape-all"])
        assert result.exit_code == 0, result.output
        # Both good subs were scraped despite the middle one blowing up.
        assert "ok_a" in fake.fetched
        assert "ok_b" in fake.fetched
        assert "boom" not in fake.fetched  # raised before append
        assert "Failed: boom" in result.output
