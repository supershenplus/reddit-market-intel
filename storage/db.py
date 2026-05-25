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
    ("0002_create_pain_facets", """
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
        CREATE INDEX IF NOT EXISTS idx_facets_post ON pain_facets(post_id);
        CREATE INDEX IF NOT EXISTS idx_facets_domain ON pain_facets(domain);
        CREATE INDEX IF NOT EXISTS idx_facets_wtp ON pain_facets(willingness_to_pay);
    """),
    ("0003_niches_add_score_breakdown", """
        ALTER TABLE niches ADD COLUMN score_breakdown TEXT;
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
        # score_breakdown is optional (Phase 4 adds it; pre-Phase-4 callers
        # may not pass it, in which case it lands as NULL).
        niche.setdefault("score_breakdown", None)
        cur = self.conn.execute(
            """INSERT INTO niches
               (label, description, post_count, cluster_count, sub_count,
                complexity_score, revenue_score, rank_score, saturation_note,
                first_seen, last_seen, centroid, score_breakdown)
               VALUES (:label, :description, :post_count, :cluster_count, :sub_count,
                       :complexity_score, :revenue_score, :rank_score, :saturation_note,
                       :first_seen, :last_seen, :centroid, :score_breakdown)""",
            niche,
        )
        self.conn.commit()
        return cur.lastrowid

    def update_niche_scores(
        self, niche_id: int, label: str,
        complexity_score: float, revenue_score: float, rank_score: float,
        score_breakdown: str,
    ):
        """In-place rescore for `analyze --rescore-niches`. Leaves the niche's
        cluster assignments + centroid + first_seen alone — only score fields
        and the label move (since label is derived from facets too)."""
        self.conn.execute(
            """UPDATE niches SET
                 label = ?,
                 complexity_score = ?,
                 revenue_score = ?,
                 rank_score = ?,
                 score_breakdown = ?
               WHERE id = ?""",
            (label, complexity_score, revenue_score, rank_score,
             score_breakdown, niche_id),
        )
        self.conn.commit()

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

    # --- Pain Facets (Phase 3 LLM extraction) ---

    def get_posts_without_facets(self, prompt_version: str) -> list[dict]:
        """Posts with no pain_facets row at the given prompt_version. Resume
        target for llm-extract — re-processes only stale rows. A version bump
        naturally widens this set to the full corpus."""
        cur = self.conn.execute(
            """SELECT p.* FROM posts p
               LEFT JOIN pain_facets pf
                 ON pf.post_id = p.id AND pf.prompt_version = ?
               WHERE pf.id IS NULL""",
            (prompt_version,),
        )
        return [dict(r) for r in cur.fetchall()]

    def upsert_pain_facet(self, facet: dict):
        """UPSERT keyed on (post_id, prompt_version). Idempotent under
        re-import; the operator can replay a batch with no duplicate rows."""
        self.conn.execute(
            """INSERT INTO pain_facets (
                post_id, prompt_version, is_pain_point, pain_summary, domain,
                current_solution, integrations_mentioned, dollar_anchors,
                max_dollar_anchor, willingness_to_pay, urgency, buyer_role,
                market_size_signal, confidence, raw_response, model,
                input_tokens, output_tokens, mode, prefilter_source
            ) VALUES (
                :post_id, :prompt_version, :is_pain_point, :pain_summary, :domain,
                :current_solution, :integrations_mentioned, :dollar_anchors,
                :max_dollar_anchor, :willingness_to_pay, :urgency, :buyer_role,
                :market_size_signal, :confidence, :raw_response, :model,
                :input_tokens, :output_tokens, :mode, :prefilter_source
            )
            ON CONFLICT(post_id, prompt_version) DO UPDATE SET
                is_pain_point = excluded.is_pain_point,
                pain_summary = excluded.pain_summary,
                domain = excluded.domain,
                current_solution = excluded.current_solution,
                integrations_mentioned = excluded.integrations_mentioned,
                dollar_anchors = excluded.dollar_anchors,
                max_dollar_anchor = excluded.max_dollar_anchor,
                willingness_to_pay = excluded.willingness_to_pay,
                urgency = excluded.urgency,
                buyer_role = excluded.buyer_role,
                market_size_signal = excluded.market_size_signal,
                confidence = excluded.confidence,
                raw_response = excluded.raw_response,
                model = excluded.model,
                input_tokens = excluded.input_tokens,
                output_tokens = excluded.output_tokens,
                mode = excluded.mode,
                prefilter_source = excluded.prefilter_source,
                extracted_at = datetime('now')""",
            facet,
        )
        self.conn.commit()

    def get_facets_for_post(self, post_id: int) -> list[dict]:
        """All facet rows for a post across prompt_versions (newest first)."""
        cur = self.conn.execute(
            "SELECT * FROM pain_facets WHERE post_id = ? ORDER BY extracted_at DESC",
            (post_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_current_facet(self, post_id: int, prompt_version: str):
        cur = self.conn.execute(
            "SELECT * FROM pain_facets WHERE post_id = ? AND prompt_version = ?",
            (post_id, prompt_version),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_facets_for_cluster_at_version(
        self, cluster_id: int, prompt_version: str,
    ) -> list[dict]:
        """All pain_facets rows for posts in this cluster at the given
        prompt_version. Phase 4 scorer reads these; the scorer applies the
        is_pain_point=1 filter itself so the LLM veto state is also preserved
        in the score_breakdown for Phase 5 audit."""
        cur = self.conn.execute(
            """SELECT pf.* FROM pain_facets pf
               JOIN pain_points pp ON pp.post_id = pf.post_id
               WHERE pp.cluster_id = ? AND pf.prompt_version = ?""",
            (cluster_id, prompt_version),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_pain_points_for_cluster_unvetoed(
        self, cluster_id: int, prompt_version: str,
    ) -> list[dict]:
        """Cluster members filtered by the LLM veto: pain_points with a
        current-version pain_facet of is_pain_point=0 are excluded.
        Pain_points with no facet at all are INCLUDED (backwards compatibility
        with pre-Phase-3 state — facets are additive, not required)."""
        cur = self.conn.execute(
            """SELECT pp.*, p.title, p.body, p.subreddit, p.url,
                      p.score AS reddit_score, p.num_comments, p.created_utc
               FROM pain_points pp
               JOIN posts p ON pp.post_id = p.id
               LEFT JOIN pain_facets pf
                 ON pf.post_id = p.id AND pf.prompt_version = ?
               WHERE pp.cluster_id = ?
                 AND (pf.is_pain_point IS NULL OR pf.is_pain_point = 1)""",
            (prompt_version, cluster_id),
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
