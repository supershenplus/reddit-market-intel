# TODO — reddit-market-intel

**Active item:** W3-6 — Re-analyze corpus, verify report surfaces high-monetization + simple-solution opps first

## W1 — Initial validation

- [x] **W1-1** End-to-end smoke test: `scrape --subreddit smallbusiness --limit 10` → `analyze` → `export` → verify report.md output
- [ ] **W1-2** Verify DB schema creates correctly from `schema.sql` on fresh run
- [ ] **W1-3** Validate scoring output — check composite scores are in 0.0–1.0 range, weights sum correctly
- [ ] **W1-4** Test clustering — confirm TF-IDF deduplication groups similar pain points
- [x] **W1-5** PRAW mode test (if credentials available) — verify throughput difference vs JSON fallback
- [x] **W1-6** Run `tests/` suite — fix any failures before W1-EOW tag
- [ ] **W1-EOW** End-of-week review

## W2 — RAG classifier upgrade

- [ ] **W2-1** Embed posts with `sentence-transformers` (e.g. `all-MiniLM-L6-v2`) — replace regex classifier
- [ ] **W2-2** Store embeddings in ChromaDB or FAISS alongside SQLite — vector search for semantic pain-point matching
- [ ] **W2-3** Define pain-point archetype queries (seed phrases per category: seeking_tool, frustrated, would_pay, etc.)
- [ ] **W2-4** Benchmark RAG hit rate vs regex on same 250-post corpus — target >15% (vs current 1.6%)
- [ ] **W2-5** Keep regex as fallback or drop once RAG validated
- [ ] **W2-6** Scale-out path: swap ChromaDB → Pinecone/pgvector if corpus exceeds 100k posts or multi-user needed

## W3 — Scoring matrix v1 (new dimensions)

- [x] **W3-1** Add `monetization_score`, `solution_simplicity`, `market_size_score` columns to schema + migrate existing DB
- [x] **W3-2** Build `analysis/market_signals.py` — heuristic scorers for all 3 dimensions
- [x] **W3-3** Rebalance SCORING_WEIGHTS in config.py (new dims get 0.30 total weight)
- [x] **W3-4** Wire new signals into scorer + analyze pipeline
- [x] **W3-5** Add tests in `tests/test_market_signals.py`
- [ ] **W3-6** Re-analyze corpus, verify report surfaces high-monetization + simple-solution opps first

## W4 — Scoring matrix v2 (scope expansion — tons missed in v1)

- [ ] **W4-1** Competition density signal — count how many products already solve this (search comment mentions)
- [ ] **W4-2** Urgency signal — "asap", "right now", "blocking me", "losing money" → higher score
- [ ] **W4-3** Specificity signal — vague pain ("productivity") vs specific ("need tool to auto-send invoice after Calendly booking")
- [ ] **W4-4** Regulatory/compliance signal — HIPAA, GDPR, SOC2 mentions → higher willingness to pay
- [ ] **W4-5** Geographic signal — US/EU-centric = larger addressable market
- [ ] **W4-6** Frequency signal — "every day", "constantly", "weekly", vs "once in a while"
- [ ] **W4-7** DIY evidence — "I built a spreadsheet", "I use Zapier for this" → validated gap, someone's hacking around it
- [ ] **W4-8** Price anchor signal — explicit $ amounts mentioned → monetization validation
- [ ] **W4-9** Trending detection improvement — weekly post-count delta per cluster, not just boolean flag
- [ ] **W4-10** Cluster quality score — single-post clusters are noise; penalize until 3+ posts agree

## Hardening

> Severity-tagged findings from EOW review. Fix Critical before next sprint.

(none yet — first sprint)

## Recent

> 1-line dated entries — newest first.

- 2026-05-11 — W3 complete: monetization/simplicity/market_size signals added, 66 tests green, pushed 9403e16
- 2026-05-11 — RAG classifier shipped (1.6% → 30% hit rate), 333 pain points from 1153 posts across 13 subreddits
- 2026-05-11 — PRAW credentials wired, python-dotenv added, smoke test passing
- 2026-05-11 — bigmode stack initialized: CLAUDE.md, TODO.md, CLAUDETODO.md, DECISIONS.md
