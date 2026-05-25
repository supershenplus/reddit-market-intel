# Reddit Market Intelligence

A personal market-gap discovery engine. Scrapes ~100 subreddits across 12 verticals, extracts user pain points via RAG + LLM, clusters them, and emits a ranked weekly markdown digest skim-able in one sitting. Designed for an audience of one — solo operator hunting for SaaS opportunities.

## Pipeline

```
scrape-all → analyze → llm-extract → llm-import → digest
   (PRAW)     (RAG)      (markdown    (validate +     (top niches,
              + regex)    batches)     UPSERT)         LLM-vetoed)
```

| Stage | What it does | Module |
|---|---|---|
| **Scrape** | PRAW + JSON-API fallback; rate-aware multi-sub walking | `scraper/` |
| **Classify** | RAG (sentence-transformers + ChromaDB) primary, regex fallback | `analysis/classifier.py`, `analysis/rag_classifier.py` |
| **Cluster** | TF-IDF + cosine-similarity dedup; k-means meta-cluster into niches | `analysis/clustering.py`, `analysis/niches.py` |
| **LLM extract** | Batch-mode structured facet extraction via Claude Code session | `analysis/llm_extractor.py` |
| **Digest** | Weekly ranked markdown, LLM facets veto noise pain_points | `export/digest.py` |

## Quick start

```bash
pip install -r requirements.txt

# Scrape one sub (no credentials needed — JSON fallback)
python main.py scrape --subreddit smallbusiness --limit 50

# Or scrape every configured sub with age-based skipping (weekly cadence)
python main.py scrape-all --max-age-days 7 --limit 100

# Build pain_points + clusters + niches
python main.py analyze

# Phase 3 — extract structured facets via Claude Code (Max sub)
python main.py llm-extract --max-posts 100
#   → open a Claude Code session, follow the printed instructions
python main.py llm-import data/llm_batches/<UTC-ts>/

# Weekly digest (LLM veto active)
python main.py digest
```

## Commands

| Command | Description |
|---|---|
| `scrape` | Fetch posts + comments from one sub or category |
| `scrape-all` | Walk every configured sub, skipping recently-scraped (`--max-age-days N`) |
| `discover` | Find related subreddits from sidebar/crossposts |
| `analyze` | RAG/regex classifier + clustering + opportunity scoring |
| `llm-extract` | Phase 3 driver — export batches + print operator handoff |
| `llm-export` | Just write batch files (scriptable primitive) |
| `llm-import <dir>` | Validate manifest + UPSERT facets into pain_facets |
| `digest` | Build niches + emit weekly markdown digest (`reports/weekly/<date>.md`) |
| `export` | Per-cluster opportunity report (legacy; pre-pivot) |
| `snapshot` / `delta` | Track cluster movement week-over-week |
| `status` | DB counts and top clusters |

## Seed subreddits (12-vertical taxonomy)

```
b2b_saas        smallbusiness, Entrepreneur, SaaS, startups, indiehackers, ...
vertical_saas   legaltech, lawfirm, Accounting, taxpros, Dentistry, ...
dev_tools       webdev, devops, programming, ExperiencedDevs, golang, ...
marketing       marketing, SEO, PPC, EmailMarketing, socialmedia, ...
freelance       freelance, DigitalNomad, forhire, Upwork, ...
ecommerce       ecommerce, shopify, FulfillmentByAmazon, EtsySellers, ...
property        realestate, RealEstateInvesting, Landlord, PropertyManagement, ...
construction    Construction, Contractor, Electricians, HVAC, Plumbing, ...
services        AutoDetailing, Salon, lawncare, landscaping, CleaningCompany, ...
automation      nocode, n8n, zapier, MakeAutomation, RPA, ...
operations      projectmanagement, OperationsManagement, businessanalysis, ...
leadership      managers, Leadership, AskManagers, EngineeringManagers, ...
```

Edit `config.py:SEED_SUBREDDITS` to tune. `scrape-all` dedupes across categories.

## Reddit API access

| Mode | Auth | Rate limit | Setup |
|---|---|---|---|
| **JSON API** (fallback) | None | ~60 req/min | Works immediately |
| **PRAW** (preferred) | OAuth | 600 req/10min | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` env vars |

Create credentials at https://www.reddit.com/prefs/apps (select "script" type).

## Phase 3 — LLM facet extraction

Two paths, configured via `config.py:LLM_DEFAULT_MODE`:

### Batch mode (default — $0 marginal cost with Claude Max)

```bash
python main.py llm-extract --max-posts 100 --prefilter strict
```

Writes batches as markdown to `data/llm_batches/<UTC-ts>/batch_NNN.md`. Each batch contains the prompt, JSON schema, schema fingerprint, and ~50 posts.

You then open a Claude Code session and process the batches in-session (Claude reads the batch, infers facets, writes `batch_NNN_facets.json` next to each batch file). Pairs naturally with `/bigmode-max` workflow.

Finally:
```bash
python main.py llm-import data/llm_batches/<UTC-ts>/
```

Validates schema fingerprint + per-batch sha256, then UPSERTs into `pain_facets`. Idempotent under replay.

### API mode (Phase 3.5 — not yet implemented)

Direct Anthropic SDK calls with cost circuit breakers. Budget config is in place (`LLM_MAX_USD_PER_RUN`, `LLM_PRICING`) but the executor lands when unattended weekly runs become useful.

### What gets extracted

12 structured facets per post (see `analysis/llm_extractor.py:FACET_FIELDS`):
- `is_pain_point` — LLM's authoritative veto (hides post from digest when false)
- `pain_summary` — one-sentence summary
- `domain` — 12-vertical taxonomy alignment
- `current_solution` — what the author says they currently use
- `integrations_mentioned`, `dollar_anchors`, `max_dollar_anchor`
- `willingness_to_pay`: `would_pay | hesitant | no_signal`
- `urgency`: `blocking | recurring | nice_to_have | none`
- `buyer_role`, `market_size_signal`, `confidence`

### Pre-filter modes

| Mode | Behavior | When |
|---|---|---|
| `strict` (default) | RAG-positive posts only | Steady-state weekly |
| `sampled` | RAG-pos + 10% of RAG-neg | Recall audit |
| `off` | All candidates | Backfill / version migration |

Each row records `prefilter_source` so RAG ↔ LLM agreement is one SQL away.

### Re-extraction safety

`LLM_PROMPT_VERSION` in `config.py` gates re-extraction. Bumping it widens `llm-extract`'s selection to the full corpus (caps at `LLM_MAX_POSTS_PER_RUN`). The `pain_facets.prompt_version` column means stale rows survive alongside fresh ones — Phase 4 reads only the current version.

## Project layout

```
reddit-market-intel/
├── main.py                       # CLI (click)
├── config.py                     # All tunables (seeds, weights, LLM budget, profiles)
├── schema.sql                    # SQLite schema (source of truth)
├── DECISIONS.md                  # Append-only ADR log
├── TODO.md                       # Active sprint + Hardening + Recent log
├── requirements.txt
├── scraper/
│   ├── base.py                   # ABC + RedditPost/Comment dataclasses
│   ├── json_scraper.py           # No-auth JSON fallback
│   ├── praw_scraper.py           # PRAW + scraper factory
│   ├── comments.py               # Comment validation flag classifier
│   └── rate_limiter.py           # Token bucket + exponential backoff
├── analysis/
│   ├── classifier.py             # RAG-primary, regex-fallback wrapper
│   ├── rag_classifier.py         # sentence-transformers + ChromaDB
│   ├── keywords.py               # Regex pain-point patterns
│   ├── validators.py             # Comment-based validation scoring
│   ├── scorer.py                 # Composite opportunity score
│   ├── market_signals.py         # Monetization / simplicity / market-size + Lienclear facets
│   ├── clustering.py             # TF-IDF agglomerative
│   ├── cluster_delta.py          # Snapshot + week-over-week delta
│   ├── niches.py                 # K-means meta-cluster of clusters
│   └── llm_extractor.py          # Phase 3 — batch export + import + validation
├── storage/
│   └── db.py                     # SQLite CRUD + migration ledger
├── discovery/
│   └── subreddit_finder.py       # Sidebar + crosspost discovery
├── export/
│   ├── report.py                 # Per-cluster opportunity report
│   ├── digest.py                 # Weekly digest (Phase 3 veto active)
│   ├── competitor_gaps.py        # Lienclear deep-profile gap report
│   └── seo_phrases.py            # Lienclear SEO phrase extractor
└── tests/                        # 194 tests covering CLI, CRUD, RAG, LLM extractor, roundtrip, digest veto
```

## Database

| Table | Role |
|---|---|
| `posts` / `comments` | Raw scraped content (one row per Reddit ID) |
| `pain_points` | RAG-classifier output: intent_category + opportunity_score + validation |
| `clusters` | TF-IDF clusters of similar pain_points; one row per cluster |
| `niches` | K-means meta-clusters over cluster centroids; rank_score drives the digest |
| `pain_facets` | **Phase 3** — LLM-extracted structured facets, gated by `prompt_version` |
| `subreddits` | Per-sub metadata + `last_scraped` for `scrape-all` age skipping |
| `verdicts` | **Phase 5** — operator build/watch/kill decisions (stubbed) |
| `migrations` | Ledger of applied schema migrations |

Schema is in `schema.sql` (idempotent CREATE). ALTER-style migrations go through `storage/db.py:MIGRATIONS` and the `migrations` ledger.

## Configuration

All knobs in `config.py`. Highlights:

```python
# Scraping
DEFAULT_LIMIT = 100
DEFAULT_SORT = "hot"
JSON_API_DELAY = 1.0

# RAG classifier
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.35

# Scoring weights (must sum to 1.0)
SCORING_WEIGHTS = {...}
INTENT_WEIGHTS = {"would_pay": 1.0, "seeking_tool": 0.8, ...}

# Phase 3 LLM extraction
LLM_DEFAULT_MODE = "batch"           # batch | api (api Phase 3.5)
LLM_BATCH_SIZE = 50
LLM_MAX_POSTS_PER_RUN = 500          # circuit breaker
LLM_RAG_PREFILTER = True
LLM_PROMPT_VERSION = "v0.1"          # bump to widen re-extract selection
LLM_PRICING = {"claude-haiku-4-5": {...}, ...}

# Clustering
CLUSTER_DISTANCE_THRESHOLD = 0.85
TRENDING_MULTIPLIER = 2.0
RECENCY_HALF_LIFE_DAYS = 90

# Lienclear deep-profile (optional overlay, off by default)
PROFILES = {"lienclear": {...}}
```

## Example weekly workflow

```bash
# Monday morning — refresh corpus
python main.py scrape-all --max-age-days 7 --limit 100

# Tuesday — classify + cluster + niche
python main.py analyze
python main.py snapshot  # for week-over-week delta later

# Wednesday — LLM facet extraction (~30 min Claude Code session)
python main.py llm-extract --max-posts 200 --prefilter strict
# (process batches in a Claude Code session)
python main.py llm-import data/llm_batches/<UTC-ts>/

# Thursday — read the digest, decide what to build
python main.py digest
# → opens reports/weekly/<date>.md
```

## Phases (5-phase discovery-engine pivot)

| Phase | Status | What |
|---|---|---|
| 1 | shipped | Skeleton digest with dumb scoring |
| 2 | shipped | Broaden corpus from 5 categories → 12-vertical / ~100 subs |
| 3 | shipped | LLM batch-mode facet extraction + digest veto |
| 3.5 | deferred | API mode (Anthropic SDK + cost tracking + circuit breakers) |
| 4 | next | Real `complexity_score` + `revenue_score` from facets |
| 5 | next | Verdict capture + taste-learning + corpus-internal saturation (W7-1) |

See `DECISIONS.md` for the architectural choices behind each phase.

## Why this exists

Personal tool. Reddit is a firehose of unmet need; this collapses a week of scrolling into a one-page digest of ranked candidates. Audience of one — me.
