"""SQLite database operations for Reddit Market Intelligence."""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from config import DB_PATH, DATA_DIR


# Ordered ALTER migrations. CREATE TABLE additions belong in schema.sql
# (idempotent via IF NOT EXISTS); ALTER TABLE ADD COLUMN can't be expressed
# idempotently in SQLite so it goes here, gated by the migrations ledger.
# Each migration's sql runs via executescript() so multi-statement (ALTER +
# dependent index) lands atomically.
MIGRATIONS = [
    ("0001_clusters_add_niche_id", """
        ALTER TABLE clusters ADD COLUMN niche_id INTEGER;
        CREATE INDEX IF NOT EXISTS idx_cluster_niche ON clusters(niche_id);
    """),
]


class Database:
    """Handles all SQLite CRUD operations."""

    def __init__(self, db_path: Path = DB_PATH):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        schema_path = Path(__file__).parent.parent / "schema.sql"
        with open(schema_path) as f:
            self.conn.executescript(f.read())
        self._migrate_columns()
        self._run_migrations()

    def _migrate_columns(self):
        """Legacy ALTER-with-catch migrations (pre-ledger). New ALTERs go in MIGRATIONS."""
        new_cols = [
            ("monetization_score", "REAL", "0.0"),
            ("solution_simplicity", "REAL", "0.5"),
            ("market_size_score", "REAL", "0.0"),
        ]
        for name, col_type, default in new_cols:
            try:
                self.conn.execute(
                    f"ALTER TABLE pain_points ADD COLUMN {name} {col_type} DEFAULT {default}"
                )
                self.conn.commit()
            except Exception:
                pass  # column already exists

    def _run_migrations(self):
        applied = {r[0] for r in self.conn.execute("SELECT name FROM migrations")}
        for name, sql in MIGRATIONS:
            if name in applied:
                continue
            try:
                self.conn.executescript(sql)
            except sqlite3.OperationalError as e:
                # Column may already exist from a prior unledgered ALTER; record as
                # applied so we don't retry every startup.
                if "duplicate column" not in str(e).lower():
                    raise
            self.conn.execute("INSERT INTO migrations (name) VALUES (?)", (name,))
            self.conn.commit()

    def close(self):
        self.conn.close()

    # --- Posts ---

    def insert_post(self, post: dict) -> bool:
        """Insert a post. Returns True if new, False if duplicate."""
        try:
            self.conn.execute(
                """INSERT INTO posts (reddit_id, subreddit, title, body, author, url, score, num_comments, created_utc)
                   VALUES (:reddit_id, :subreddit, :title, :body, :author, :url, :score, :num_comments, :created_utc)""",
                post,
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def post_exists(self, reddit_id: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM posts WHERE reddit_id = ?", (reddit_id,))
        return cur.fetchone() is not None

    def get_post_by_reddit_id(self, reddit_id: str) -> Optional[dict]:
        cur = self.conn.execute("SELECT * FROM posts WHERE reddit_id = ?", (reddit_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_posts_without_pain_points(self) -> list[dict]:
        """Get posts that haven't been analyzed yet."""
        cur = self.conn.execute(
            """SELECT p.* FROM posts p
               LEFT JOIN pain_points pp ON pp.post_id = p.id
               WHERE pp.id IS NULL"""
        )
        return [dict(r) for r in cur.fetchall()]

    def get_all_pain_points(self) -> list[dict]:
        cur = self.conn.execute(
            """SELECT pp.*, p.title, p.body, p.subreddit, p.url, p.score as reddit_score, p.created_utc
               FROM pain_points pp JOIN posts p ON pp.post_id = p.id
               ORDER BY pp.opportunity_score DESC"""
        )
        return [dict(r) for r in cur.fetchall()]

    # --- Comments ---

    def insert_comment(self, comment: dict) -> bool:
        """Insert a comment. Returns True if new, False if duplicate."""
        try:
            self.conn.execute(
                """INSERT INTO comments (reddit_id, post_reddit_id, parent_reddit_id, author, body, score, created_utc,
                   is_me_too, links_product, product_negative)
                   VALUES (:reddit_id, :post_reddit_id, :parent_reddit_id, :author, :body, :score, :created_utc,
                   :is_me_too, :links_product, :product_negative)""",
                comment,
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_comments_for_post(self, post_reddit_id: str) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM comments WHERE post_reddit_id = ? ORDER BY score DESC",
            (post_reddit_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    # --- Pain Points ---

    def insert_pain_point(self, pain_point: dict):
        self.conn.execute(
            """INSERT INTO pain_points (post_id, matched_patterns, intent_category, opportunity_score,
               sentiment_intensity, validation_score, recency_weight, cross_sub_count, cluster_id,
               monetization_score, solution_simplicity, market_size_score)
               VALUES (:post_id, :matched_patterns, :intent_category, :opportunity_score,
               :sentiment_intensity, :validation_score, :recency_weight, :cross_sub_count, :cluster_id,
               :monetization_score, :solution_simplicity, :market_size_score)""",
            pain_point,
        )
        self.conn.commit()

    def update_pain_point_cluster(self, pain_point_id: int, cluster_id: int):
        self.conn.execute(
            "UPDATE pain_points SET cluster_id = ? WHERE id = ?",
            (cluster_id, pain_point_id),
        )
        self.conn.commit()

    def update_pain_point_score(self, pain_point_id: int, score: float):
        self.conn.execute(
            "UPDATE pain_points SET opportunity_score = ? WHERE id = ?",
            (score, pain_point_id),
        )
        self.conn.commit()

    # --- Clusters ---

    def upsert_cluster(self, cluster: dict) -> int:
        """Insert or update a cluster. Returns cluster id."""
        if cluster.get("id"):
            self.conn.execute(
                """UPDATE clusters SET label=:label, post_count=:post_count, avg_opportunity_score=:avg_opportunity_score,
                   subreddits=:subreddits, first_seen=:first_seen, last_seen=:last_seen, trending=:trending
                   WHERE id=:id""",
                cluster,
            )
            self.conn.commit()
            return cluster["id"]
        else:
            cur = self.conn.execute(
                """INSERT INTO clusters (label, post_count, avg_opportunity_score, subreddits, first_seen, last_seen, trending)
                   VALUES (:label, :post_count, :avg_opportunity_score, :subreddits, :first_seen, :last_seen, :trending)""",
                cluster,
            )
            self.conn.commit()
            return cur.lastrowid

    def get_all_clusters(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM clusters ORDER BY avg_opportunity_score DESC")
        return [dict(r) for r in cur.fetchall()]

    def clear_clusters(self):
        """Remove all clusters and cluster assignments (for re-clustering)."""
        self.conn.execute("UPDATE pain_points SET cluster_id = NULL")
        self.conn.execute("DELETE FROM clusters")
        self.conn.commit()

    # --- Subreddits ---

    def upsert_subreddit(self, sub: dict):
        self.conn.execute(
            """INSERT INTO subreddits (name, subscribers, category, discovered_from, last_scraped, active)
               VALUES (:name, :subscribers, :category, :discovered_from, :last_scraped, :active)
               ON CONFLICT(name) DO UPDATE SET
               subscribers=excluded.subscribers, last_scraped=excluded.last_scraped""",
            sub,
        )
        self.conn.commit()

    def get_subreddit_info(self, name: str) -> Optional[dict]:
        cur = self.conn.execute("SELECT * FROM subreddits WHERE name = ?", (name,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_active_subreddits(self, category: Optional[str] = None) -> list[dict]:
        if category:
            cur = self.conn.execute(
                "SELECT * FROM subreddits WHERE active = 1 AND category = ?", (category,)
            )
        else:
            cur = self.conn.execute("SELECT * FROM subreddits WHERE active = 1")
        return [dict(r) for r in cur.fetchall()]

    # --- Niches (Phase 1 discovery-engine pivot) ---

    def get_clusters_for_niching(self, min_post_count: int = 2) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM clusters WHERE post_count >= ? ORDER BY post_count DESC",
            (min_post_count,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_pain_points_for_cluster(self, cluster_id: int) -> list[dict]:
        cur = self.conn.execute(
            """SELECT pp.*, p.title, p.body, p.subreddit, p.url,
                      p.score AS reddit_score, p.num_comments, p.created_utc
               FROM pain_points pp JOIN posts p ON pp.post_id = p.id
               WHERE pp.cluster_id = ?""",
            (cluster_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def clear_niches(self):
        self.conn.execute("UPDATE clusters SET niche_id = NULL")
        self.conn.execute("DELETE FROM niches")
        self.conn.commit()

    def insert_niche(self, niche: dict) -> int:
        cur = self.conn.execute(
            """INSERT INTO niches
               (label, description, post_count, cluster_count, sub_count,
                complexity_score, revenue_score, rank_score, saturation_note,
                first_seen, last_seen, centroid)
               VALUES (:label, :description, :post_count, :cluster_count, :sub_count,
                       :complexity_score, :revenue_score, :rank_score, :saturation_note,
                       :first_seen, :last_seen, :centroid)""",
            niche,
        )
        self.conn.commit()
        return cur.lastrowid

    def update_cluster_niche(self, cluster_id: int, niche_id: int):
        self.conn.execute(
            "UPDATE clusters SET niche_id = ? WHERE id = ?",
            (niche_id, cluster_id),
        )
        self.conn.commit()

    def get_top_niches(self, n: int = 10) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM niches ORDER BY rank_score DESC LIMIT ?", (n,)
        )
        return [dict(r) for r in cur.fetchall()]

    def get_clusters_for_niche(self, niche_id: int) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM clusters WHERE niche_id = ?", (niche_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    # --- Stats ---

    def get_stats(self) -> dict:
        stats = {}
        for table in ("posts", "comments", "pain_points", "clusters", "subreddits"):
            cur = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cur.fetchone()[0]
        cur = self.conn.execute("SELECT MAX(opportunity_score) FROM pain_points")
        row = cur.fetchone()
        stats["top_score"] = row[0] if row[0] else 0.0
        return stats
