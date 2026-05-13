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

## 2026-05-12: Profile overlays via PROFILES dict — no SCORING_WEIGHTS rebalance

**Choice:** Lienclear-specific scoring/filter behavior lives in a `PROFILES["lienclear"]` overlay dict in `config.py`. The Lienclear relevance score is computed alongside the generic opportunity score and stored inside the `matched_patterns` JSON column (no new schema columns). Profile is selected via `--profile lienclear` on export.
**Why:** Rebalancing the shared `SCORING_WEIGHTS` for one research profile would corrupt cross-profile comparability and require re-scoring all historical pain points whenever the weights drift. Overlay-only means generic and Lienclear reports stay byte-stable side-by-side, and adding more profiles later (e.g. another vertical) doesn't fight existing data.
**Rejected:** SCORING_WEIGHTS rebalance per profile (breaks comparability); dedicated `pain_points_lienclear` table (violates single-table convention, duplicates schema); new schema columns for Lienclear facets (premature — JSON works fine until query pressure justifies it).

## 2026-05-12: Domain-hit as soft cap, not hard precondition

**Choice:** `compute_lienclear_relevance` caps raw_score at 0.20 when `domain_hits` is empty, rather than zeroing or returning early. State/role/$/competitor facets are still extracted and surfaced in the report breakdown.
**Why:** Zeroing loses diagnostic value — when investigating false positives, knowing the per-component breakdown matters. Cap at 0.20 keeps the post visible to the inspector while blocking it from crossing the 0.30 export threshold. Reversible by config tweak if the cap turns out wrong.
**Rejected:** Full zero-out (loses facet diagnostics); hard precondition `return out` early (same diagnostic loss + obscures partial-match cases in tests).

## 2026-05-12: Comment augmentation rejected on measured signal density

**Choice:** `compute_lienclear_relevance` operates on post title + body only; comments are NOT concatenated into the scoring text. Decided via data: 22/62846 comments (0.035%) hit any Lienclear domain keyword.
**Why:** Architectural refactor to feed comment text into the scorer was about to ship "to fix" a thin signal. Cheap diagnostic (one `for row in conn.execute("SELECT body FROM comments"):` loop) showed augmentation would not move the needle. Surfaced the number to the user, killed the refactor before commit. Real bottleneck is upstream RAG classifier filtering construction posts, not comment coverage.
**Rejected:** Concat top-N comment bodies into augmented_body (refactor for ~0% signal gain); synthetic pain_point insertion for unclassified-but-domain-hit posts (couples Lienclear logic to pain_points lifecycle, dilutes cluster quality with off-topic text).
