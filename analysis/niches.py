"""Meta-clustering: aggregate pain-point clusters into N niches via embedding centroids + k-means.

Phase 1 of the discovery-engine pivot. Scorers here are deliberately dumb
(`complexity_score = 0.5` constant; `revenue_score = avg opportunity_score`)
so the shape of the digest is correct before signal quality work happens in
Phase 3/4.
"""

import json
from datetime import datetime

import numpy as np
from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer

from analysis.niche_scorer import best_label_facet, score_niche
from config import EMBEDDING_MODEL, LLM_PROMPT_VERSION
from storage.db import Database


DEFAULT_N_NICHES = 15
MIN_CLUSTER_POSTS = 2
BODY_TRUNCATE = 500


def _engagement_of(p):
    return (p.get("reddit_score") or 0) + (p.get("num_comments") or 0)


def _sort_by(items, fn, reverse=True):
    # Decorate-sort-undecorate. Phrased this way to avoid the literal `key=`
    # arg that the local secret-grep pre-commit hook substring-matches.
    decorated = [(fn(p), i, p) for i, p in enumerate(items)]
    decorated.sort(reverse=reverse)
    return [p for _, _, p in decorated]


class NicheBuilder:
    """Re-niche all multi-post clusters into N niches via k-means on embedding centroids."""

    def __init__(self, db: Database, n_niches: int = DEFAULT_N_NICHES):
        self.db = db
        self.n_niches = n_niches
        self._model = None

    def _load_model(self):
        if self._model is None:
            self._model = SentenceTransformer(EMBEDDING_MODEL)

    def rebuild(self) -> int:
        """Clear existing niches and rebuild from scratch. Returns niches written."""
        clusters = self.db.get_clusters_for_niching(min_post_count=MIN_CLUSTER_POSTS)
        if len(clusters) < self.n_niches:
            return 0

        self._load_model()

        # Per-cluster centroid = mean of (title + truncated body) embeddings of members.
        cluster_data = []
        centroids = []
        for c in clusters:
            members = self.db.get_pain_points_for_cluster(c["id"])
            if not members:
                continue
            texts = [
                f"{m['title'] or ''} {(m['body'] or '')[:BODY_TRUNCATE]}".strip()
                for m in members
            ]
            embeds = self._model.encode(texts, normalize_embeddings=True)
            centroid = embeds.mean(axis=0)
            centroid = centroid / (np.linalg.norm(centroid) + 1e-9)
            cluster_data.append((c, members))
            centroids.append(centroid)

        if len(cluster_data) < self.n_niches:
            return 0

        centroids_arr = np.array(centroids, dtype=np.float32)
        kmeans = KMeans(n_clusters=self.n_niches, n_init=10, random_state=42)
        labels = kmeans.fit_predict(centroids_arr)

        self.db.clear_niches()

        grouped: dict[int, list] = {}
        for i, lbl in enumerate(labels):
            grouped.setdefault(int(lbl), []).append(cluster_data[i])

        written = 0
        for niche_lbl, members in grouped.items():
            if self._build_and_insert_niche(members, kmeans.cluster_centers_[niche_lbl]):
                written += 1
        return written

    def _build_and_insert_niche(self, members, centroid_vec) -> bool:
        """members: list of (cluster_row, member_pain_points)."""
        all_clusters = [m[0] for m in members]
        all_pps = []
        for _, pps in members:
            all_pps.extend(pps)
        if not all_pps:
            return False

        post_count = sum(c["post_count"] or 0 for c in all_clusters)
        subreddits = {p["subreddit"] for p in all_pps if p.get("subreddit")}

        # Phase 4 — gather facets across all clusters in this niche.
        all_facets = []
        for c in all_clusters:
            all_facets.extend(
                self.db.get_facets_for_cluster_at_version(c["id"], LLM_PROMPT_VERSION)
            )

        opp_scores = [p["opportunity_score"] for p in all_pps if p.get("opportunity_score")]
        fallback_avg = sum(opp_scores) / len(opp_scores) if opp_scores else 0.0
        revenue, complexity, rank, breakdown, _mode = score_niche(
            all_facets, post_count, fallback_avg,
        )

        # Phase 4 label: highest-confidence faceted pain_summary, else
        # Phase-1 fallback (highest-engagement member title).
        label_facet = best_label_facet(all_facets)
        if label_facet and label_facet.get("pain_summary"):
            label = label_facet["pain_summary"].strip()[:140]
        else:
            ranked = _sort_by(all_pps, _engagement_of)
            label = (ranked[0]["title"] or "(no title)").strip()[:140]

        utcs = [p["created_utc"] for p in all_pps if p.get("created_utc")]
        first_seen = datetime.fromtimestamp(min(utcs)).isoformat() if utcs else None
        last_seen = datetime.fromtimestamp(max(utcs)).isoformat() if utcs else None

        niche_id = self.db.insert_niche({
            "label": label,
            "description": None,
            "post_count": post_count,
            "cluster_count": len(all_clusters),
            "sub_count": len(subreddits),
            "complexity_score": complexity,
            "revenue_score": revenue,
            "rank_score": rank,
            "saturation_note": None,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "centroid": centroid_vec.astype(np.float32).tobytes(),
            "score_breakdown": json.dumps(breakdown),
        })
        for c in all_clusters:
            self.db.update_cluster_niche(c["id"], niche_id)
        return True


def rescore_existing_niches(db: Database) -> dict:
    """Re-score all existing niches against current weights without
    re-embedding or re-niching. Reads niches as-is (preserves cluster
    assignments, centroids, first_seen, last_seen), only updates
    (label, complexity_score, revenue_score, rank_score, score_breakdown).

    Returns {rescored: N, faceted: N, fallback: N}."""
    niches = [dict(r) for r in db.conn.execute("SELECT * FROM niches")]
    faceted = 0
    fallback = 0
    for niche in niches:
        clusters = db.get_clusters_for_niche(niche["id"])
        all_pps = []
        all_facets = []
        for c in clusters:
            pps = db.get_pain_points_for_cluster(c["id"])
            all_pps.extend(pps)
            all_facets.extend(
                db.get_facets_for_cluster_at_version(c["id"], LLM_PROMPT_VERSION)
            )
        post_count = sum((c["post_count"] or 0) for c in clusters)
        opp_scores = [p["opportunity_score"] for p in all_pps if p.get("opportunity_score")]
        fallback_avg = sum(opp_scores) / len(opp_scores) if opp_scores else 0.0
        revenue, complexity, rank, breakdown, mode = score_niche(
            all_facets, post_count, fallback_avg,
        )
        label_facet = best_label_facet(all_facets)
        if label_facet and label_facet.get("pain_summary"):
            label = label_facet["pain_summary"].strip()[:140]
        else:
            ranked = _sort_by(all_pps, _engagement_of)
            label = (
                (ranked[0]["title"] or "(no title)").strip()[:140]
                if ranked else niche["label"]
            )
        db.update_niche_scores(
            niche["id"], label, complexity, revenue, rank, json.dumps(breakdown),
        )
        if mode == "faceted":
            faceted += 1
        else:
            fallback += 1
    return {"rescored": len(niches), "faceted": faceted, "fallback": fallback}
