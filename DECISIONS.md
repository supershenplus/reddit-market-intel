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

## 2026-05-23: Facet-only pattern over scoring-weight integration for new signals

**Choice:** New signal layers (DIY-evidence, urgency, frequency, and the W5-7
heat-signal enrichment) ship as diagnostic facets on the dict returned by
`compute_lienclear_relevance` — captured patterns are stored in
`matched_patterns.lienclear`, surfaced in per-post and per-cluster sections
of the lienclear report, and aggregated as `<facet>_rate` on cluster meta.
They do **not** enter the relevance score weight.
**Why:** Adding to `SCORING_WEIGHTS` or `LIENCLEAR_RELEVANCE_WEIGHTS` would
(a) require renormalizing existing weights (which shifts every historical
pain_point's score and breaks cross-snapshot comparability), (b) require
schema migration + a `--force` re-analyze backfill, and (c) lock in a weight
value before any corpus signal density is measured. The facet-only path ships
the data on the next export with zero migration, lets the user eyeball signal
density first, and weight tuning can happen later once the actual hit rate is
known. The W5-7 enrichment also added a live-rescan fallback so older
pain_points light up without `--force` re-analyze.
**Rejected:** Adding new dimensions to `SCORING_WEIGHTS` immediately (weight
guesses without corpus measurement); requiring `--force` re-analyze to use
new facets (slow + couples signal addition to re-classification); skipping
extraction entirely until weights are validated (no signal at all defeats
the point of extraction).

## 2026-05-23: Cluster identity = label, not id, in delta snapshots

**Choice:** `analysis/cluster_delta.py` matches clusters between snapshots by
`label`, not by `id`. The compute_delta function builds `by_label` dicts and
diffs membership.
**Why:** `clusters.id` is a SQLite AUTOINCREMENT — it gets re-issued from
scratch on every `analyze --force` (since the clusters table is dropped and
rebuilt). A cluster about lien waivers might be id=42 in one snapshot and
id=617 in the next. Label is the only field that stays stable across re-runs.
Labels can still drift slightly when cluster composition shifts (different
top TF-IDF terms win the label slot), which produces some false NEW/DEAD
churn — acceptable noise for a monthly cadence; the bellwether-chatter and
score-change buckets are more reliable signals anyway.
**Rejected:** id-based matching (breaks on every `--force` run); content-
hash matching (over-engineered for monthly cadence); requiring a stable
cluster_uuid column (schema migration, doesn't survive --force without
extra plumbing).

## 2026-05-23: Bellwether competitors = Levelset + Procore for W5-12 thesis watch

**Choice:** `THESIS_BELLWETHER_COMPETITORS = ("Levelset", "Procore")` —
the W5-12 thesis-watch sub-section fires when either goes silent
(`baseline > 0 → current = 0`) or declines materially (`Δ ≤ -3 with
baseline ≥ 5`).
**Why:** Per the lienclear startup thesis, two macro signals open and keep
the market gap open: (a) the **Levelset acquisition vacuum** — Levelset was
the dominant DIY-construction-friendly lien-waiver tool and was acquired by
Procore in 2021; if Levelset chatter dies down on Reddit, the vacuum is
closing (someone else filled it, or trades stopped asking) and the thesis
weakens. (b) the **Procore price umbrella** — Procore at enterprise pricing
is the GC-side tool subs are forced to interact with; sustained
dissatisfaction is the wedge for an SMB-priced alternative. Other named
competitors (Buildertrend, Textura, GCPay, Siteline, Handle.com) inform
positioning but aren't load-bearing for the core thesis.
**Rejected:** Tracking all `LIENCLEAR_COMPETITORS` as bellwethers (dilutes
the watch — most competitor mention deltas are noise); requiring user to
configure bellwethers per-run (config drift); using a learned weight (no
labeled data for "thesis-impactful" yet).

## 2026-05-21: Domain detection at the report layer, not via synthetic pain_points

**Choice:** The lienclear report (`export/report.py`) renders a `Domain-Hit Posts` section by
scanning every row in `posts` through `compute_lienclear_relevance` at export time, surfacing
posts that hit Lienclear domain keywords regardless of whether the RAG classifier ever
classified them. Domain detection is decoupled from the generic pain-point classifier gate.
**Why:** Diagnostic confirmed `BUG-thin-signal`: of 5 domain-hit posts in a 3636-post corpus,
3 were dropped by the `if result:` classifier gate (`main.py:141`) before `compute_lienclear_relevance`
could score them. That function is pure regex on title/body/subreddit — it has zero dependency
on classifier output, so gating it behind the classifier was an architectural wart. A
report-layer scan recovers the dropped posts with no schema change and no `main.py` change.
**Rejected:** Synthetic pain_point insertion for unclassified-but-domain-hit posts (already
rejected 2026-05-12 — pollutes the shared `pain_points` table, dilutes cluster quality, couples
Lienclear logic to the pain_points lifecycle). RAG construction-seed expansion (a different
lever — lifts generic classification rate, carries false-positive risk, overlaps unfinished
W5-4). Note: this closes the *classifier-gate* component of `BUG-thin-signal`; the *corpus
thinness* component (only 5 domain-hit posts exist) remains a sourcing problem for a future
rescrape, not a code blocker.
