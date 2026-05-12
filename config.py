"""Configuration for Reddit Market Intelligence Pipeline."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "market_intel.db"

# Reddit API credentials (PRAW) — set via environment or leave empty for JSON fallback
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "MarketIntel/1.0")

# RAG classifier
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_PATH = str(DATA_DIR / "chroma")
SIMILARITY_THRESHOLD = 0.35   # cosine similarity floor; tune after benchmarking

# Rate limiting
JSON_API_DELAY = 1.0          # seconds between JSON API requests
JSON_API_JITTER = (0.5, 1.5)  # random jitter range (seconds)
MAX_RETRIES = 5
BACKOFF_BASE = 2              # exponential backoff base (seconds)

# Scraping defaults
DEFAULT_LIMIT = 100
DEFAULT_SORT = "hot"          # hot, new, top
COMMENT_DEPTH = 3             # max depth of comment tree to parse

# Seed subreddits by category
SEED_SUBREDDITS = {
    "smb_saas": ["smallbusiness", "Entrepreneur", "SaaS", "startups", "indiehackers"],
    "productivity": ["productivity", "selfhosted", "nocode", "Automate"],
    "dev_tools": ["webdev", "devops", "programming", "sideproject"],
    "freelance": ["freelance", "DigitalNomad", "WorkOnline"],
}

# Scoring weights (must sum to 1.0)
SCORING_WEIGHTS = {
    "reddit_score": 0.15,
    "sentiment_intensity": 0.15,
    "validation_score": 0.15,
    "cross_sub_multiplier": 0.10,
    "intent_weight": 0.10,
    "recency_weight": 0.05,
    "monetization_score": 0.15,
    "solution_simplicity": 0.10,
    "market_size_score": 0.05,
}

# Market signal keywords
MONETIZATION_HIGH_KEYWORDS = [
    r"\bwould pay\b", r"\bwilling to pay\b", r"\bpay for\b", r"\bworth paying\b",
    r"\b\$\d+\s*(?:/mo|/month|per month|/year)\b", r"\bROI\b", r"\bB2B\b",
    r"\benterprise\b", r"\bsave.*time.*money\b", r"\bcharge clients\b",
    r"\bbusiness expense\b", r"\bbudget for\b",
]
MONETIZATION_LOW_KEYWORDS = [
    r"\bfree\b", r"\bopen.?source\b", r"\bcan't afford\b", r"\btoo expensive\b",
    r"\bno budget\b", r"\bjust a hobby\b",
]
MONETIZATION_HIGH_SUBREDDITS = {
    "smallbusiness", "Entrepreneur", "SaaS", "startups", "freelance",
    "AskEntrepreneur", "microsaas", "ecommerce",
}
MONETIZATION_LOW_SUBREDDITS = {
    "productivity", "digitalnomad", "nocode", "SideProject",
}

SIMPLICITY_HIGH_KEYWORDS = [
    r"\bstatic site\b", r"\bdirectory\b", r"\baggregator\b", r"\bnewsletter\b",
    r"\bsimple form\b", r"\bjust needs?\b", r"\bone.?page\b", r"\blanding page\b",
    r"\bno.?code\b", r"\bsimple webapp\b", r"\bbasic tool\b",
]
SIMPLICITY_LOW_KEYWORDS = [
    r"\breal.?time\b", r"\bmulti.?tenant\b", r"\benterprise integration\b",
    r"\bAPI sync\b", r"\bmachine learning\b", r"\bcomplex\b", r"\bscalable infra\b",
    r"\bmicroservices\b", r"\breal.?time collaboration\b",
]

MARKET_SIZE_CEILING_SUBSCRIBERS = 10_000_000

INTENT_WEIGHTS = {
    "would_pay": 1.0,
    "seeking_tool": 0.8,
    "unbundle": 0.7,
    "frustrated": 0.6,
    "feature_request": 0.5,
}

# Clustering
CLUSTER_DISTANCE_THRESHOLD = 0.65
TFIDF_MAX_FEATURES = 5000
TRENDING_MULTIPLIER = 2.0     # post count in 30d must exceed this * avg to be "trending"
RECENCY_HALF_LIFE_DAYS = 90
