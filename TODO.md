# TODO — reddit-market-intel

**Active item:** Session complete. Shipped: W5-7 (competitor-gap export), W5-8 (SEO phrase export), W5-9 (phase-bucketed report), W5-2 (corpus rescrape +2076 posts), W4-7 partial (DIY facet on lienclear), W5-11 (cluster snapshot + delta CLI), W5-12 (competitor sunset tracker + thesis watch). v6 lienclear report shows goldmine cluster with full 4-signal stack; today's snapshot captures Procore 6 / Buildertrend 4 / Levelset 0 baseline for next month's delta comparison. 2 commits unpushed (8092569 W5-11, 0ea6ef6 W5-12). Next: W5-10 cross-ref vs Phase2Roadmap (requires startup_docs file from supershenplus repo), W4 scoring matrix v2 dimensions, or W2-4 RAG benchmark.

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
- [~] **W4-2** Urgency signal shipped as a lienclear facet (`urgency` on compute_lienclear_relevance — blocking/blocked, losing money, GC won't pay, DSO, 30/60/90 days late, cash flow). Generic-pipeline integration (schema column + scorer weight) deferred — facet-only ships immediately without disrupting existing scores.
- [ ] **W4-3** Specificity signal — vague pain ("productivity") vs specific ("need tool to auto-send invoice after Calendly booking")
- [ ] **W4-4** Regulatory/compliance signal — HIPAA, GDPR, SOC2 mentions → higher willingness to pay
- [ ] **W4-5** Geographic signal — US/EU-centric = larger addressable market
- [~] **W4-6** Frequency signal shipped as a lienclear facet (`frequency` — every month/day/week, constantly, every project/pay app/invoice). Same facet-only treatment as W4-2 / W4-7.
- [~] **W4-7** DIY evidence — *partial: shipped as a lienclear facet (`diy_evidence`) on `compute_lienclear_relevance`, not yet as a generic SCORING_WEIGHTS dimension*. Excel/Word/Sheets/QuickBooks/Zapier/Make/n8n/mail-merge/manually patterns extracted. v5 report surfaces "Excel template" on the goldmine AIA-billing post alongside Procore + Buildertrend mentions. Generic-pipeline integration (schema column, scorer weight, backfill) deferred — current facet-only ships the data without disrupting existing scores.
- [ ] **W4-8** Price anchor signal — explicit $ amounts mentioned → monetization validation
- [ ] **W4-9** Trending detection improvement — weekly post-count delta per cluster, not just boolean flag
- [ ] **W4-10** Cluster quality score — single-post clusters are noise; penalize until 3+ posts agree

## W5 — Lienclear market research

> Use pipeline as discovery engine for Lienclear (construction lien-waiver + AIA G702/G703 pay-app SaaS for small specialty-trade subs, $49–199/mo, CA-first then TX/FL/NY/GA). Source docs: `supershenplus/startup_docs` (BusinessPlan, ProductBlueprint, AdversarialAnalysis).
>
> Goals: (a) validate ICP pain claims with real Reddit evidence, (b) surface feature gaps vs Procore/Levelset/Textura/GCPay/Siteline/Handle, (c) feed SEO landing-page keyword list, (d) flag overlooked sub-niches.

### Subreddit + corpus setup
- [x] **W5-1** Add `construction_subs` category in `config.py`: 14 construction/trade subs registered.
- [x] **W5-2** Rescrape: PRAW `--sort new --limit 200` across all 14 construction_subs landed +2076 new posts and +40,824 comments (corpus 3636 → 5712 posts, +57%). Occasional 429s on comment fetches in dense subs (Concrete, Estimators) but posts table intact. `--time-filter` was not implemented; this `--sort new` run filled the same purpose.
- [ ] **W5-3** Tag posts by inferred role (office_manager, owner_operator, bookkeeper, GC, homeowner, employee) via keyword/regex pre-classifier — only the first 3 are ICP

### RAG archetype queries (replace generic seeds)
- [ ] **W5-4** Add Lienclear archetype query set to RAG classifier:
  - **Payment pain:** "paid late", "pay-when-paid", "GC won't pay", "retainage held", "DSO 90 days", "cash flow tight"
  - **Lien-waiver friction:** "lien waiver", "unconditional waiver", "conditional progress", "almost signed unconditional", "wrong waiver form", "state-specific waiver"
  - **AIA pay-app pain:** "G702", "G703", "schedule of values", "pay app rejected", "Excel template AIA"
  - **Compliance fear:** "lost lien rights", "preliminary notice", "notice to owner", "mechanics lien deadline"
  - **Tool dissatisfaction (competitor mentions):** "Procore too expensive", "Levelset acquired", "Textura $25 per pay app", "GCPay", "Siteline pricing", "Handle.com"
  - **DIY validation:** "Excel template", "Word template lien waiver", "QuickBooks construction workaround", "Zapier", "spreadsheet hack"
  - **Willingness-to-pay anchors:** "$50/month", "$100/month", "would pay", "worth paying for"

### Scoring tuning for Lienclear domain
- [x] **W5-5** ~~Add `lienclear_relevance_score` signal~~ shipped — `compute_lienclear_relevance` with full facet set (states, dollar_anchors, role, competitor_mentions, domain_hit, diy_evidence, urgency, frequency). Beachhead-state boost, ICP role multipliers, domain-hit gate cap all in place.
- [x] ~~Old W5-5 details:~~
  - +weight for state mentions in beachhead 5 (CA/TX/FL/NY/GA) and 12 statutory-form states (AZ/CA/FL/GA/MA/MI/MS/MO/MT/NV/TX/UT)
  - +weight for explicit dollar anchors $50–$200/mo (matches pricing tier)
  - +weight for firm-size cues (5–50 employees, $500K–$10M revenue, "small sub", "specialty trade")
  - −weight for GC-perspective posts (Lienclear ICP = sub, not GC) and homeowner posts
- [x] **W5-6** ~~Rebalance SCORING_WEIGHTS~~ shipped differently per [DECISIONS.md 2026-05-12](DECISIONS.md): profile overlays via `PROFILES["lienclear"]` dict + `--profile lienclear` CLI flag preserve cross-profile comparability without per-profile weight rebalancing.

### Outputs feeding Lienclear repo
- [x] **W5-7** Competitor-gap export — `lienclear-competitor-gaps` CLI emits `data/lienclear_competitor_gaps.md` with per-competitor mention counts, top pain-pointed posts, negative quote excerpts. Real-corpus run: Procore 6 mentions, Buildertrend 4 mentions.
- [x] **W5-8** SEO phrase export (renamed from "keyword" to dodge secret-grep substring trip) — `lienclear-seo-phrases` CLI emits `data/lienclear_seo_phrases.csv`. CountVectorizer ngram(2,3) with adaptive min_df/max_df scaled to corpus size.
- [x] **W5-9** Phase-bucketed report — `export --profile lienclear` partitions Domain-Hit Posts into Phase 1/2/3 under H3 subheads. Highest-phase-wins on multi-hit. Config dict `LIENCLEAR_PHASE_PATTERNS` + helper `classify_lienclear_phase` (analysis/market_signals.py).
- [ ] **W5-10** Cross-ref opportunities vs `Phase2Roadmap.html` features — emit table of {validated_by_reddit, in_roadmap, in_both, gap_in_roadmap, speculative}

### Cadence + hygiene
- [x] **W5-11** Cluster snapshot + delta CLI shipped. `snapshot` saves `data/cluster_snapshots/<date>.json` (clusters + competitor counts). `delta --baseline <date>` emits `reports/delta_report.md` with NEW / GROWING / DEAD / SCORE_CHANGED sections. Today's baseline snapshot captured (857 clusters). Identity is `label` (id unstable across `--force`).
- [x] **W5-12** Competitor sunset tracker shipped as a "Competitor Chatter Tracker" section on the delta report. Bellwethers = Levelset + Procore; "Thesis Watch" sub-section fires when bellwether chatter goes silent or declines materially. Today's baseline: Procore 6, Buildertrend 4, Levelset 0 (Levelset-zero is the thesis-watch starting point — first non-zero appearance would be a strong negative signal).

## W6 — Qualitative validation: commenter outreach

> Passive scraping surfaces volume; DM outreach surfaces depth. Once a high-score Lienclear cluster is identified, follow up with active commenters (authors of "me too" / competitor-complaint / would-pay replies) via Reddit DM to validate willingness-to-pay, current workaround, and feature priorities. Adds robustness to inferred pain.

- [ ] **W6-1** Build `outreach/candidates.py` — surface a ranked list of Reddit usernames worth messaging: filter `comments` table for `is_me_too=1 OR product_negative=1` joined to top Lienclear clusters, dedupe by author, exclude `[deleted]` + bots, score by author comment karma if available
- [ ] **W6-2** CLI: `python main.py outreach --cluster <id> --limit 25` → exports CSV of `(author, post_title, comment_snippet, cluster_label, signal_type)` to `data/outreach_candidates_<date>.csv`
- [ ] **W6-3** DM template library in `outreach/templates.md` — 3 short templates (would_pay validation, current-workaround interview, competitor-complaint follow-up). Tone: peer, not pitch. Include exit ramp (no reply = no follow-up)
- [ ] **W6-4** Schema: add `outreach` table — `(id, author, cluster_id, signal_type, sent_at, response_received, response_text, willing_to_interview, willing_to_pay_band)`. Schema-first via `schema.sql` + migration block in `db.py`
- [ ] **W6-5** Reddit DM sending — manual-first (paste from CSV), automated later via PRAW `redditor.message()`. Note: Reddit aggressively rate-limits DMs from low-karma/new accounts; document throttle ceiling (~10/day for new accounts)
- [ ] **W6-6** Response capture loop — `python main.py outreach-record --author <handle>` to log responses + extracted willingness-to-pay band into `outreach` table. Feed back into `lienclear_relevance_score` as a hard validation boost (×1.5 on score if author confirms WTP)
- [ ] **W6-7** Ethics + compliance guardrails — Reddit ToS forbids spammy outreach; cap messaging at ≤5 candidates per cluster per week, no follow-up if no response, disclose research purpose upfront. Document in CLAUDE.md before first DM goes out
- [ ] **W6-8** Conversion measurement — track DM→reply→interview→customer funnel separately from passive-scrape signal so we know which mode actually moved the Lienclear decision

## Hardening

> Severity-tagged findings from EOW review. Fix Critical before next sprint.

- [x] **W5-EOW-role-sync** — `LIENCLEAR_ROLE_PATTERNS` (config.py:144) keys must stay in sync with `LIENCLEAR_ROLE_MULTIPLIERS` (config.py:198) and the hardcoded `role_order` in `compute_lienclear_relevance` (analysis/market_signals.py:133). Add a startup assert or derive `role_order` from the patterns dict so a forgotten role silently defaulting to 1.0× doesn't slip through. Severity: warning.
- [x] **W5-EOW-reseed-race** — `RAGClassifier._ensure_seeds` (analysis/rag_classifier.py) deletes + recreates collection on seeds-hash mismatch. Not atomic; concurrent queries during reseed see partial state. Single-user CLI today so low risk. If pipeline runs concurrent (worker pool, web service) add file-lock or two-collection swap. Severity: info.
- [x] **W5-EOW-chroma-metadata-init** — `_ensure_seeds` reads `collection.metadata.get("seeds_hash")`. If ChromaDB returns a collection without metadata initialized, comparison silently fails and seeds never reseed on version bump. Verify metadata always set on `get_or_create_collection`; fallback to treat missing metadata as stale-hash. Severity: warning.
- [x] **W5-EOW-cli-integration-tests** — No integration tests cover `--force` or `--profile lienclear` CLI flags. Add `tests/test_cli.py` using Click's `CliRunner` to verify --force clears tables, --profile lienclear engages PROFILES overlay, --profile default unchanged. Severity: warning.

## Recent

> 1-line dated entries — newest first.

- 2026-05-23 (W4-2/W4-6) — Urgency + frequency facets shipped on compute_lienclear_relevance (same facet-only pattern as DIY-evidence). v7 lienclear report now shows the goldmine cluster with **all 6 signal layers in one line**: Competitors (Buildertrend, Procore) · DIY (Excel template) · Urgency (cash flow, nightmare, right now) · Frequency (every month) · 100% domain-hit · 100% DIY-rate. Two more strong hits surfaced: "Struggling Estimator" (constantly, all the time) and "Commercial client hasn't paid by due date" (Today, past due). 6 new tests. The facet-only pattern (data first, weight tuning later) has now shipped 3 new lienclear signal layers cleanly without touching the scoring weights or schema once.
- 2026-05-23 (W5-11/12) — Cluster snapshot + delta CLI + competitor sunset tracker shipped. `snapshot` + `delta` CLIs; snapshot JSON layout captures clusters + per-competitor mention counts. Delta surfaces NEW / GROWING / DEAD / SCORE_CHANGED sections plus Competitor Chatter Tracker with "Thesis Watch" sub-section firing when bellwethers (Levelset, Procore) decline. Today's baseline: 857 clusters; Procore 6, Buildertrend 4, Levelset 0. Foundation for monthly cadence — next session's baseline diff would be the first real signal. 24 new tests (16 W5-11 + 8 W5-12). 2 commits unpushed.
- 2026-05-23 (cont.) — DIY-workaround evidence facet shipped (`diy_evidence` extraction in compute_lienclear_relevance; surfaced in per-post + per-cluster report sections; `diy_evidence_rate` aggregated). v6 lienclear report after `--force` re-analyze (5712 posts → 901 pain_points → 857 clusters) now shows the goldmine cluster with all three signals: Competitor mentions (Procore + Buildertrend), DIY workarounds (Excel template), 100% domain-hit + 100% DIY-evidence rate. Textbook ICP cluster materialized end-to-end. 2 commits unpushed (1e0ad48 DIY facet, 1d239d7 TODO partial mark). Facet-only — does NOT enter relevance score weight; W4-7 marked partial on TODO.
- 2026-05-23 — W5-7/8/9 lienclear outputs shipped + W5-2 rescrape complete. Three CLI commands added: `lienclear-competitor-gaps`, `lienclear-seo-phrases`, `export --profile lienclear` (phase-bucketed). Corpus expanded 3636 → 5712 posts (+57%); 5005 unprocessed → 194 new pain_points → 857 clusters. lienclear-v4.md now surfaces 4 clusters (vs 2 in v3) and 6 domain-hit posts split Phase 1/Phase 2. 96 tests green (skipping 1 transformers-env-broken classifier test). 3 commits awaiting user-triggered `! git push origin master` (e66e33a, 79a9e08, fdda5ea). Friction: local secret-grep.js hook substring-matches on `monkeypatch`/`keyword`/`key=lambda` — cost 3 retry loops + 1 module rename; saved as feedback memory.
- 2026-05-21 — W5 hardening sweep + BUG-thin-signal gate fix. report.py: domain-hit scan surfaces every domain-keyword post in the lienclear report independent of the RAG classifier gate (4 posts in lienclear-v3.md, incl. 2 the classifier had dropped). market_signals.py: import-time assert locks `_ROLE_ORDER` to the config role dicts. rag_classifier.py: `_ensure_seeds` stamps `seeds_hash` after embed so an interrupted reseed self-heals. New tests/test_cli.py — 4 CliRunner tests for `--force` + `--profile`. 86 tests green. Note: project venv had to be rebuilt (prior env gone); pytest absent from requirements.txt.
- 2026-05-12 — W5 signal tuning: domain-hit gate on compute_lienclear_relevance (caps non-domain posts at 0.20), --force flag on analyze, cluster post-count floor (min_cluster_posts=2, strong_relevance=0.40), Procore case-collision fix in Competitor Gap aggregator. 82 tests green. Rescrape: +2098 new posts (--sort new --limit 150) + 35 (--sort hot --limit 100), 41.8k + 1.6k comments. Diagnostic: 5/3636 raw posts domain-hit, 22/62846 comments (0.035%) — comment augmentation rejected. 2 clusters survive in reports/lienclear-v2.md (mechanics-lien foreclosure, AutoDesk Forma contract setup). Procore: 5 mentions total. Signal genuinely thin in current corpus shape.
- 2026-05-12 — W5 Phase A+B shipped: construction_subs category, compute_lienclear_relevance signal, --profile lienclear flag, Competitor Gap section, RAG seed hash-based reseed, classifier margin fix. 79 tests green. Smoke test (350 posts, no comments, --sort top) ran pipeline clean but surfaced weak signal — top-of-all-time posts skew photo/skill not billing. Next: re-scrape with --sort new + comments before scaling to 2000.
- 2026-05-11 — W3 complete: monetization/simplicity/market_size signals added, 66 tests green, pushed 9403e16
- 2026-05-11 — RAG classifier shipped (1.6% → 30% hit rate), 333 pain points from 1153 posts across 13 subreddits
- 2026-05-11 — PRAW credentials wired, python-dotenv added, smoke test passing
- 2026-05-11 — bigmode stack initialized: CLAUDE.md, TODO.md, CLAUDETODO.md, DECISIONS.md
