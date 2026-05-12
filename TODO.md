# TODO — reddit-market-intel

**Active item:** W1-EOW — End-of-week review

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

## Hardening

> Severity-tagged findings from EOW review. Fix Critical before next sprint.

(none yet — first sprint)

## Recent

> 1-line dated entries — newest first.

- 2026-05-11 — PRAW credentials wired, python-dotenv added, smoke test passing
- 2026-05-11 — bigmode stack initialized: CLAUDE.md, TODO.md, CLAUDETODO.md, DECISIONS.md
