# DECISIONS.md — reddit-market-intel

Append-only ADR log. Add entries when non-obvious architectural choices are made.

---

## 2026-05-11: Dual-mode scraper — JSON fallback + PRAW primary

**Choice:** Built two scrapers (`json_scraper.py` + `praw_scraper.py`) with automatic fallback. JSON API is default (no credentials needed); PRAW activates when `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` env vars are set.
**Why:** Zero-setup operation is a hard requirement — the pipeline must work immediately without Reddit OAuth registration. PRAW gives 10x throughput but requires credential setup. Keeping both modes means the tool is immediately useful and optionally faster.
**Rejected:** PRAW-only (breaks zero-credential use case); JSON-only (too slow for large scrapes at scale).

## 2026-05-11: SQLite over Postgres

**Choice:** Local SQLite file (`data/market_intel.db`) as the storage backend.
**Why:** Single-user intelligence tool running locally. No server setup, no connection pooling, no devops. `sqlite-utils` gives a clean Python API. Schema is in `schema.sql` for reproducibility.
**Rejected:** Postgres (over-engineered for local solo use — adds server dependency with no multi-user benefit at current scale). Revisit if tool becomes multi-user or cloud-hosted.

## 2026-05-11: RAG classifier over LLM-based classification

**Choice:** `sentence-transformers` (all-MiniLM-L6-v2) + ChromaDB for semantic pain-point detection. Regex kept as fallback.
**Why:** Zero API cost, runs fully local, no latency. Hit rate went from 1.6% (regex-only) to 30%+ on same corpus. LLM would give better accuracy but adds cost per post and external dependency — incompatible with zero-credential design goal.
**Rejected:** OpenAI/Claude API classifier (cost + latency + breaks offline use); pure regex (too brittle, 1.6% hit rate).

## 2026-05-11: ALTER TABLE migration over drop-and-recreate

**Choice:** `_migrate_columns()` in `db.py` runs `ALTER TABLE pain_points ADD COLUMN` with exception fallback for existing columns. schema.sql updated for fresh installs.
**Why:** 333 scraped pain points already in DB when new scoring columns were added — dropping would lose all data. Exception-based check is idempotent and safe.
**Rejected:** Drop + recreate (data loss); conditional CREATE (SQLite doesn't support `ADD COLUMN IF NOT EXISTS`).

## 2026-05-11: Similarity threshold as tunable config value

**Choice:** `SIMILARITY_THRESHOLD = 0.35` in `config.py` — not hardcoded in classifier.
**Why:** Optimal threshold depends on corpus and seed quality; 0.35 is empirically reasonable but unvalidated. Making it config means it can be tuned without code changes once benchmarking data exists (W2-4).
**Rejected:** Hardcoded threshold (makes benchmarking iteration require code edits).
