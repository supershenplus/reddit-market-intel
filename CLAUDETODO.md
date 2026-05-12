# reddit-market-intel — Meta Backlog (CLAUDETODO)

> Workflow-stack and tooling improvements only. Pipeline/feature work goes in TODO.md.

**Last touched:** 2026-05-11
**Active item:** none — stack just initialized

---

## How to resume cold

1. Read this file top-to-bottom.
2. Pick first unchecked Critical, then High, then Medium item.
3. After each item: tick, write 1-line "what changed" under **Recent**, bump **Active item**.

---

## Critical

(none yet)

## High

- [ ] Add `ruff` or `flake8` lint config — no linter currently configured
- [ ] Add `pytest` config (`pytest.ini` or `pyproject.toml`) — tests/ exists but no runner config
- [ ] Cover `storage/db.py` with at least basic CRUD tests

## Medium

- [ ] Evaluate LLM classifier as optional upgrade path over regex (track cost vs accuracy tradeoff)
- [ ] Add `--dry-run` flag to `scrape` for testing without writing to DB
- [ ] Benchmark scoring weights — current values are heuristic, not empirically validated

## Deferred

- [ ] Multi-user / cloud deployment (Postgres migration) — only if this becomes a shared tool

---

## Recent

> 1-line dated entries — newest first.

- 2026-05-11 — CLAUDETODO initialized with bigmode stack
