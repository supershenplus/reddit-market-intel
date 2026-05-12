# Reddit Market Intelligence Pipeline

A modular Python pipeline that scrapes niche subreddits for user complaints and requests, identifies market gaps for SaaS/apps/tools, clusters similar pain points into opportunities, and scores them by potential. No LLM API key required — uses regex/heuristic analysis locally, with structured exports designed for Claude Code analysis sessions.

## How It Works

```
Scrape → Classify → Validate → Score → Cluster → Export
```

1. **Scrape** posts and comment threads from target subreddits
2. **Classify** posts using 25 regex patterns across 5 intent categories
3. **Validate** via comment thread analysis (unanswered questions, "me too" signals, failed competitor mentions)
4. **Score** opportunities using a weighted composite of upvotes, sentiment, validation, cross-subreddit correlation, and recency
5. **Cluster** similar pain points using TF-IDF + cosine similarity to deduplicate
6. **Export** structured markdown reports grouped by market opportunity

## Quick Start

```bash
cd reddit-market-intel
pip install -r requirements.txt

# Scrape a subreddit (no credentials needed)
python main.py scrape --subreddit smallbusiness --limit 50

# Run the full analysis pipeline
python main.py analyze

# Export top opportunities
python main.py export --top 20 --output report.md
```

## Commands

| Command | Description |
|---------|-------------|
| `scrape` | Fetch posts + comments from Reddit |
| `analyze` | Run classifier, validator, scorer, and clustering |
| `discover` | Find related subreddits from sidebar/crossposts |
| `export` | Generate markdown opportunity report |
| `status` | Show database stats and top clusters |

### Scrape

```bash
# Single subreddit
python main.py scrape --subreddit Entrepreneur --limit 100 --sort top

# All subreddits in a category
python main.py scrape --category smb_saas --limit 50

# Skip comment fetching (faster, less validation data)
python main.py scrape --subreddit SaaS --no-comments
```

### Analyze

```bash
python main.py analyze
```

Runs the full pipeline on all unprocessed posts: pattern matching, comment validation, opportunity scoring, and clustering.

### Discover

```bash
python main.py discover --from smallbusiness --category smb_saas
```

Parses sidebar descriptions and crosspost patterns to find related subreddits automatically.

### Export

```bash
python main.py export --top 20 --output report.md --min-score 0.4
```

Generates a structured report grouped by opportunity cluster, including evidence posts, validation signals, and failed competitor mentions. Designed to be fed directly into a Claude Code session for deeper analysis.

### Status

```bash
python main.py status
```

Shows post/comment/cluster counts and the top-scoring opportunities.

## Reddit API Access

The pipeline works in two modes:

| Mode | Auth Required | Rate Limit | Setup |
|------|--------------|------------|-------|
| **JSON API** (default) | None | ~60 req/min | Works immediately |
| **PRAW** (primary) | OAuth credentials | 600 req/10min | Set env vars below |

To enable PRAW (higher throughput):

```bash
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
```

Create credentials at https://www.reddit.com/prefs/apps — select "script" type.

## Intent Categories

Posts are classified into 5 intent categories, each with different opportunity weight:

| Category | Weight | Example Signal |
|----------|--------|----------------|
| `would_pay` | 1.0 | "I'd gladly pay for..." |
| `unbundle` | 0.7 | "Too expensive for just..." |
| `seeking_tool` | 0.8 | "Is there an app that..." |
| `frustrated` | 0.6 | "Current options suck..." |
| `feature_request` | 0.5 | "Wish someone would build..." |

## Opportunity Scoring

Each pain point receives a composite score (0.0–1.0):

```
score = 0.20 * normalized_upvotes
      + 0.20 * sentiment_intensity
      + 0.20 * validation_score (from comment analysis)
      + 0.15 * cross_subreddit_multiplier
      + 0.15 * intent_weight
      + 0.10 * recency_weight (90-day half-life)
```

### Comment Validation Signals

| Signal | Effect | Meaning |
|--------|--------|---------|
| Unanswered post | +0.3 | Genuine market gap |
| "Me too" replies | +0.1 each (cap 0.3) | Demand confirmation |
| Competitor + negative sentiment | +0.2 | Unbundling opportunity |
| Competitor + positive reception | -0.4 | Not a gap |
| High engagement, no consensus | +0.2 | Fragmented market |

## Clustering

Similar complaints are grouped into market opportunities using:
- TF-IDF vectorization (unigrams + bigrams, English stop words removed)
- Agglomerative clustering with cosine distance threshold of 0.65
- Auto-labeling from top TF-IDF terms

Clusters track cross-subreddit spread and trending status (2x volume spike in last 30 days).

## Seed Subreddits

Preconfigured categories in `config.py`:

```
smb_saas:     smallbusiness, Entrepreneur, SaaS, startups, indiehackers
productivity: productivity, selfhosted, nocode, Automate
dev_tools:    webdev, devops, programming, sideproject
freelance:    freelance, DigitalNomad, WorkOnline
```

Add more via `discover` or edit `config.py` directly.

## Project Structure

```
reddit-market-intel/
├── main.py                    # CLI (click)
├── config.py                  # Settings and seed subreddits
├── schema.sql                 # SQLite schema
├── requirements.txt
├── scraper/
│   ├── base.py                # BaseScraper ABC
│   ├── json_scraper.py        # No-auth JSON API scraper
│   ├── praw_scraper.py        # PRAW OAuth scraper + factory
│   ├── comments.py            # Comment thread classifier
│   └── rate_limiter.py        # Token bucket + backoff
├── analysis/
│   ├── keywords.py            # 25 regex pain-point patterns
│   ├── classifier.py          # Pattern matching engine
│   ├── validators.py          # Comment-based validation scoring
│   ├── scorer.py              # Composite opportunity scoring
│   └── clustering.py          # TF-IDF deduplication
├── discovery/
│   └── subreddit_finder.py    # Related sub discovery
├── storage/
│   └── db.py                  # SQLite CRUD
└── export/
    └── report.py              # Clustered markdown reports
```

## Example Workflow

```bash
# 1. Scrape multiple categories
python main.py scrape --category smb_saas --limit 100
python main.py scrape --category freelance --limit 100

# 2. Discover more subreddits
python main.py discover --from smallbusiness

# 3. Analyze everything
python main.py analyze

# 4. Check what we found
python main.py status

# 5. Export for deep analysis
python main.py export --top 30 --output opportunities.md --min-score 0.4

# 6. Open in Claude Code for strategic analysis
# "Read opportunities.md and rank the top 5 by build feasibility for a solo developer"
```

## Configuration

All tunable parameters live in `config.py`:

- Rate limiting (delay, jitter, retries)
- Scoring weights and intent weights
- Clustering threshold and TF-IDF features
- Recency half-life
- Trending multiplier
- Comment parsing depth
