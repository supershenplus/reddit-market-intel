"""TF-IDF + cosine similarity clustering for pain point deduplication."""

import json
from datetime import datetime

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_distances
import numpy as np

from config import CLUSTER_DISTANCE_THRESHOLD, TFIDF_MAX_FEATURES, TRENDING_MULTIPLIER
from storage.db import Database


class PainPointClusterer:
    """Groups similar pain points into market opportunity clusters."""

    def __init__(self, db: Database):
        self.db = db
        self.vectorizer = TfidfVectorizer(
            max_features=TFIDF_MAX_FEATURES,
            stop_words="english",
            ngram_range=(1, 2),
        )

    def cluster(self):
        """Run clustering on all pain points. Updates DB with cluster assignments."""
        pain_points = self.db.get_all_pain_points()
        if len(pain_points) < 2:
            return

        # Clear existing clusters for re-clustering
        self.db.clear_clusters()

        # Build text corpus from titles + bodies
        texts = [f"{pp['title']} {pp['body']}" for pp in pain_points]

        # TF-IDF vectorization
        tfidf_matrix = self.vectorizer.fit_transform(texts)

        # Compute cosine distance matrix
        distance_matrix = cosine_distances(tfidf_matrix)

        # Agglomerative clustering
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=CLUSTER_DISTANCE_THRESHOLD,
            metric="precomputed",
            linkage="average",
        )
        labels = clustering.fit_predict(distance_matrix)

        # Group pain points by cluster
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(pain_points[i])

        # Create cluster records and assign pain points
        for label, members in clusters.items():
            cluster_label = self._generate_label(members)
            subreddits = list(set(m["subreddit"] for m in members))
            scores = [m["opportunity_score"] for m in members if m["opportunity_score"]]
            created_dates = [m["created_utc"] for m in members if m["created_utc"]]

            cluster_data = {
                "label": cluster_label,
                "post_count": len(members),
                "avg_opportunity_score": sum(scores) / len(scores) if scores else 0.0,
                "subreddits": json.dumps(subreddits),
                "first_seen": datetime.fromtimestamp(min(created_dates)).isoformat() if created_dates else None,
                "last_seen": datetime.fromtimestamp(max(created_dates)).isoformat() if created_dates else None,
                "trending": self._is_trending(members),
            }

            cluster_id = self.db.upsert_cluster(cluster_data)

            # Update pain point cluster assignments
            for member in members:
                self.db.update_pain_point_cluster(member["id"], cluster_id)

            # Update cross_sub_count for all members
            cross_sub = len(subreddits)
            for member in members:
                self.db.conn.execute(
                    "UPDATE pain_points SET cross_sub_count = ? WHERE id = ?",
                    (cross_sub, member["id"]),
                )
            self.db.conn.commit()

    def _generate_label(self, members: list[dict]) -> str:
        """Auto-generate a cluster label from top TF-IDF terms."""
        texts = [f"{m['title']} {m['body']}" for m in members]
        combined = " ".join(texts)

        # Use the fitted vectorizer to get feature names
        feature_names = self.vectorizer.get_feature_names_out()
        tfidf_vec = self.vectorizer.transform([combined])
        scores = tfidf_vec.toarray()[0]

        # Top 3 terms by TF-IDF score
        top_indices = np.argsort(scores)[-3:][::-1]
        top_terms = [feature_names[i] for i in top_indices if scores[i] > 0]

        return " + ".join(top_terms) if top_terms else "uncategorized"

    def _is_trending(self, members: list[dict]) -> int:
        """Check if cluster is trending (spike in last 30 days)."""
        import time
        now = time.time()
        thirty_days_ago = now - (30 * 86400)
        ninety_days_ago = now - (90 * 86400)

        recent = sum(1 for m in members if m.get("created_utc", 0) > thirty_days_ago)
        older = sum(1 for m in members if ninety_days_ago < m.get("created_utc", 0) <= thirty_days_ago)

        # Trending if recent count > 2x the average monthly rate
        avg_monthly = older / 2.0 if older > 0 else 0.5
        return 1 if recent > (TRENDING_MULTIPLIER * avg_monthly) else 0
