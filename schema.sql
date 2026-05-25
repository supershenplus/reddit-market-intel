-- Reddit Market Intelligence Pipeline — SQLite Schema

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reddit_id TEXT UNIQUE NOT NULL,
    subreddit TEXT NOT NULL,
    title TEXT,
    body TEXT,
    author TEXT,
    url TEXT,
    score INTEGER,
    num_comments INTEGER,
    created_utc REAL,
    scraped_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reddit_id TEXT UNIQUE NOT NULL,
    post_reddit_id TEXT NOT NULL,
    parent_reddit_id TEXT,
    author TEXT,
    body TEXT,
    score INTEGER,
    created_utc REAL,
    is_me_too INTEGER DEFAULT 0,
    links_product INTEGER DEFAULT 0,
    product_negative INTEGER DEFAULT 0,
    FOREIGN KEY (post_reddit_id) REFERENCES posts(reddit_id)
);

CREATE TABLE IF NOT EXISTS pain_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    matched_patterns TEXT,
    intent_category TEXT,
    opportunity_score REAL,
    sentiment_intensity REAL,
    validation_score REAL,
    recency_weight REAL,
    cross_sub_count INTEGER DEFAULT 1,
    cluster_id INTEGER,
    reviewed INTEGER DEFAULT 0,
    monetization_score REAL DEFAULT 0.0,
    solution_simplicity REAL DEFAULT 0.5,
    market_size_score REAL DEFAULT 0.0,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);

CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT,
    post_count INTEGER,
    avg_opportunity_score REAL,
    subreddits TEXT,
    first_seen TEXT,
    last_seen TEXT,
    trending INTEGER DEFAULT 0,
    niche_id INTEGER
);

-- Discovery-engine pivot (Phase 1): niches aggregate clusters into 5-15 ranked
-- candidates surfaced in the weekly markdown digest. centroid is a packed
-- float32 array (BLOB) used for taste-learning similarity in Phase 5.
CREATE TABLE IF NOT EXISTS niches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    description TEXT,
    post_count INTEGER,
    cluster_count INTEGER,
    sub_count INTEGER,
    complexity_score REAL,
    revenue_score REAL,
    rank_score REAL,
    saturation_note TEXT,
    first_seen TEXT,
    last_seen TEXT,
    centroid BLOB
);

-- Operator verdicts captured by triage workflow (Phase 5). Stubbed in Phase 1
-- so the schema is ready when digest-record lands. Identity is subject_label
-- (not id) so verdicts survive re-niching and re-clustering — same rationale
-- as cluster_delta uses label-based identity.
CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_type TEXT NOT NULL,
    subject_label TEXT NOT NULL,
    decision TEXT NOT NULL,
    decided_at TEXT DEFAULT (datetime('now')),
    note TEXT
);

-- Migration ledger replaces the ALTER-with-exception-catch pattern in
-- db.py._migrate_columns. Each migration runs once; ledger records it by name.
CREATE TABLE IF NOT EXISTS migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    applied_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subreddits (
    name TEXT PRIMARY KEY,
    subscribers INTEGER,
    category TEXT,
    discovered_from TEXT,
    last_scraped TEXT,
    active INTEGER DEFAULT 1
);

-- Phase 3 discovery-engine pivot — structured LLM-extracted facets per post.
-- One row per (post_id, prompt_version). is_pain_point is the LLM's
-- authoritative veto: when the current-version row is 0, the digest hides
-- the underlying pain_points row. Backwards-compatible: pre-Phase-3 DBs
-- with no facets surface every classified pain_point as before.
CREATE TABLE IF NOT EXISTS pain_facets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    prompt_version TEXT NOT NULL,
    is_pain_point INTEGER NOT NULL,
    pain_summary TEXT,
    domain TEXT,
    current_solution TEXT,
    integrations_mentioned TEXT,
    dollar_anchors TEXT,
    max_dollar_anchor REAL,
    willingness_to_pay TEXT,
    urgency TEXT,
    buyer_role TEXT,
    market_size_signal TEXT,
    confidence REAL,
    raw_response TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    mode TEXT,
    prefilter_source TEXT,
    extracted_at TEXT DEFAULT (datetime('now')),
    UNIQUE(post_id, prompt_version),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pp_score ON pain_points(opportunity_score DESC);
CREATE INDEX IF NOT EXISTS idx_pp_cluster ON pain_points(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_score ON clusters(avg_opportunity_score DESC);
-- idx_cluster_niche lives in db.py MIGRATIONS — depends on niche_id column
-- which is added via ALTER for pre-Phase-1 DBs.
CREATE INDEX IF NOT EXISTS idx_posts_sub ON posts(subreddit);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_reddit_id);
CREATE INDEX IF NOT EXISTS idx_niches_rank ON niches(rank_score DESC);
CREATE INDEX IF NOT EXISTS idx_verdicts_subject ON verdicts(subject_type, subject_label);
CREATE INDEX IF NOT EXISTS idx_facets_post ON pain_facets(post_id);
CREATE INDEX IF NOT EXISTS idx_facets_domain ON pain_facets(domain);
CREATE INDEX IF NOT EXISTS idx_facets_wtp ON pain_facets(willingness_to_pay);
