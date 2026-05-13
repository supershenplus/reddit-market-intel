# TODO — reddit-market-intel

**Active item:** W5-signal-tuning shipped (domain gate + --force + cluster floor + Procore case fix). Corpus 3636 posts / 62.8k comments. Signal genuinely thin: 5/3636 raw posts domain-hit, 22/62846 comments domain-hit (0.035%). Comment augmentation rejected as unjustified. Next: re-evaluate classifier filter rate or expand domain keyword surface.

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

## W5 — Lienclear market research

> Use pipeline as discovery engine for Lienclear (construction lien-waiver + AIA G702/G703 pay-app SaaS for small specialty-trade subs, $49–199/mo, CA-first then TX/FL/NY/GA). Source docs: `supershenplus/startup_docs` (BusinessPlan, ProductBlueprint, AdversarialAnalysis).
>
> Goals: (a) validate ICP pain claims with real Reddit evidence, (b) surface feature gaps vs Procore/Levelset/Textura/GCPay/Siteline/Handle, (c) feed SEO landing-page keyword list, (d) flag overlooked sub-niches.

### Subreddit + corpus setup
- [ ] **W5-1** Add `construction_subs` category in `config.py`: `Construction`, `Electricians`, `HVAC`, `Plumbing`, `ConstructionManagement`, `Contractor`, `Roofing`, `Concrete`, `Welding`, `Estimators`, `Flooring`, `Carpentry`, `Painting`, `Bookkeeping` (subset filter for construction tag), `smallbusiness` (subset filter for trade keywords)
- [ ] **W5-2** Scrape ≥2000 posts across category with `--time-filter year` to capture seasonal billing/payment complaints — verify PRAW throughput sufficient
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
- [ ] **W5-5** Add `lienclear_relevance_score` signal to `analysis/market_signals.py`:
  - +weight for state mentions in beachhead 5 (CA/TX/FL/NY/GA) and 12 statutory-form states (AZ/CA/FL/GA/MA/MI/MS/MO/MT/NV/TX/UT)
  - +weight for explicit dollar anchors $50–$200/mo (matches pricing tier)
  - +weight for firm-size cues (5–50 employees, $500K–$10M revenue, "small sub", "specialty trade")
  - −weight for GC-perspective posts (Lienclear ICP = sub, not GC) and homeowner posts
- [ ] **W5-6** Rebalance `SCORING_WEIGHTS` for Lienclear runs (CLI flag `--profile lienclear`): boost monetization + market_size + new lienclear_relevance, lower generic frequency

### Outputs feeding Lienclear repo
- [ ] **W5-7** Competitor-gap export — for each cluster mentioning a named competitor, emit row `(competitor, complaint_summary, post_count, top_quotes)` → `data/lienclear_competitor_gaps.md`
- [ ] **W5-8** SEO keyword export — extract noun-phrase clusters from high-score pain points → `data/lienclear_seo_keywords.csv` (feeds 50-state landing-page playbook from BusinessPlan §5.2)
- [ ] **W5-9** Phase-bucketed report (`export --profile lienclear`): partition opportunities by build phase from ProductBlueprint — Phase 1 (free waiver gen + SEO), Phase 2 (paid AIA + dashboard), Phase 3 (notifications + DocuSign + GC portal). Surfaces "what to build next" not just "what's painful"
- [ ] **W5-10** Cross-ref opportunities vs `Phase2Roadmap.html` features — emit table of {validated_by_reddit, in_roadmap, in_both, gap_in_roadmap, speculative}

### Cadence + hygiene
- [ ] **W5-11** Monthly re-run cron — diff new pain-point clusters vs prior month; surface emerging complaints (new GC tooling rollouts, statute changes) into a `delta_report.md`
- [ ] **W5-12** Track Levelset/Procore sunset chatter specifically — Levelset acquisition vacuum is the core thesis; if chatter dies down, thesis weakens. Boolean indicator in monthly delta report

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

(none yet — first sprint)

## Recent

> 1-line dated entries — newest first.

- 2026-05-12 — W5 signal tuning: domain-hit gate on compute_lienclear_relevance (caps non-domain posts at 0.20), --force flag on analyze, cluster post-count floor (min_cluster_posts=2, strong_relevance=0.40), Procore case-collision fix in Competitor Gap aggregator. 82 tests green. Rescrape: +2098 new posts (--sort new --limit 150) + 35 (--sort hot --limit 100), 41.8k + 1.6k comments. Diagnostic: 5/3636 raw posts domain-hit, 22/62846 comments (0.035%) — comment augmentation rejected. 2 clusters survive in reports/lienclear-v2.md (mechanics-lien foreclosure, AutoDesk Forma contract setup). Procore: 5 mentions total. Signal genuinely thin in current corpus shape.
- 2026-05-12 — W5 Phase A+B shipped: construction_subs category, compute_lienclear_relevance signal, --profile lienclear flag, Competitor Gap section, RAG seed hash-based reseed, classifier margin fix. 79 tests green. Smoke test (350 posts, no comments, --sort top) ran pipeline clean but surfaced weak signal — top-of-all-time posts skew photo/skill not billing. Next: re-scrape with --sort new + comments before scaling to 2000.
- 2026-05-11 — W3 complete: monetization/simplicity/market_size signals added, 66 tests green, pushed 9403e16
- 2026-05-11 — RAG classifier shipped (1.6% → 30% hit rate), 333 pain points from 1153 posts across 13 subreddits
- 2026-05-11 — PRAW credentials wired, python-dotenv added, smoke test passing
- 2026-05-11 — bigmode stack initialized: CLAUDE.md, TODO.md, CLAUDETODO.md, DECISIONS.md
