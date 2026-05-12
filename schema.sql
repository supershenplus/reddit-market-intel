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
    trending INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subreddits (
    name TEXT PRIMARY KEY,
    subscribers INTEGER,
    category TEXT,
    discovered_from TEXT,
    last_scraped TEXT,
    active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_pp_score ON pain_points(opportunity_score DESC);
CREATE INDEX IF NOT EXISTS idx_pp_cluster ON pain_points(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_score ON clusters(avg_opportunity_score DESC);
CREATE INDEX IF NOT EXISTS idx_posts_sub ON posts(subreddit);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_reddit_id);
