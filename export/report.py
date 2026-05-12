"""Export clustered opportunity reports for Claude Code analysis."""

import json
from datetime import datetime

from storage.db import Database


class ReportGenerator:
    """Generates structured markdown reports of market opportunities."""

    def __init__(self, db: Database):
        self.db = db

    def generate(self, top_n: int = 20, min_score: float = 0.0) -> str:
        """Generate a clustered opportunity report.

        Args:
            top_n: Max number of opportunities to include.
            min_score: Minimum avg_opportunity_score for a cluster.

        Returns:
            Markdown string.
        """
        clusters = self.db.get_all_clusters()
        clusters = [c for c in clusters if (c["avg_opportunity_score"] or 0) >= min_score]
        clusters = clusters[:top_n]

        if not clusters:
            return "# Market Opportunity Report\n\nNo opportunities found above threshold.\n"

        lines = [
            f"# Market Opportunity Report — {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"**Generated**: {datetime.now().isoformat()}",
            f"**Clusters shown**: {len(clusters)} (min score: {min_score})",
            "",
            "---",
            "",
        ]

        for rank, cluster in enumerate(clusters, 1):
            subreddits = json.loads(cluster["subreddits"]) if cluster["subreddits"] else []
            trending = "Yes" if cluster["trending"] else "No"

            lines.append(f"## Opportunity #{rank}: {cluster['label']}")
            lines.append(f"**Score**: {cluster['avg_opportunity_score']:.2f} | "
                        f"**Posts**: {cluster['post_count']} | "
                        f"**Subreddits**: {', '.join(subreddits)}")
            lines.append(f"**Trending**: {trending} | "
                        f"**First seen**: {cluster['first_seen'] or 'N/A'} | "
                        f"**Last seen**: {cluster['last_seen'] or 'N/A'}")
            lines.append("")

            # Get pain points in this cluster
            pain_points = self._get_cluster_evidence(cluster["id"])

            if pain_points:
                lines.append("### Evidence")
                for i, pp in enumerate(pain_points[:5], 1):
                    title = pp["title"][:80] if pp["title"] else "(no title)"
                    lines.append(
                        f"{i}. [r/{pp['subreddit']}] \"{title}\" "
                        f"(↑ {pp['reddit_score'] or 0})"
                    )
                    # Show comment thread summary
                    comments = self.db.get_comments_for_post(pp.get("reddit_id", ""))
                    me_too = sum(1 for c in comments if c.get("is_me_too"))
                    neg = sum(1 for c in comments if c.get("product_negative"))
                    if me_too or neg:
                        parts = []
                        if me_too:
                            parts.append(f'{me_too} "me too" replies')
                        if neg:
                            parts.append(f"{neg} competitor complaints")
                        lines.append(f"   - {', '.join(parts)}")
                    elif not comments:
                        lines.append("   - Unanswered — no viable product linked")
                    lines.append(f"   - URL: {pp.get('url', 'N/A')}")

                lines.append("")

                # Failed competitors section
                competitors = self._extract_competitors(cluster["id"])
                if competitors:
                    lines.append("### Failed Competitors Mentioned")
                    for comp, reason in competitors[:5]:
                        lines.append(f"- {comp}: \"{reason}\"")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _get_cluster_evidence(self, cluster_id: int) -> list[dict]:
        """Get top pain points for a cluster, ordered by score."""
        cur = self.db.conn.execute(
            """SELECT pp.*, p.title, p.body, p.subreddit, p.url, p.score as reddit_score,
                      p.reddit_id, p.created_utc
               FROM pain_points pp
               JOIN posts p ON pp.post_id = p.id
               WHERE pp.cluster_id = ?
               ORDER BY pp.opportunity_score DESC
               LIMIT 10""",
            (cluster_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def _extract_competitors(self, cluster_id: int) -> list[tuple[str, str]]:
        """Extract mentioned competitors from negative product comments in a cluster."""
        import re

        cur = self.db.conn.execute(
            """SELECT c.body FROM comments c
               JOIN posts p ON c.post_reddit_id = p.reddit_id
               JOIN pain_points pp ON pp.post_id = p.id
               WHERE pp.cluster_id = ? AND c.product_negative = 1
               LIMIT 20""",
            (cluster_id,),
        )

        competitors = []
        # Simple extraction: look for "I tried/use X but..." patterns
        pattern = re.compile(
            r"(?:i (?:tried|use|used|switched from))\s+([A-Z]\w+).*?(?:but|however|except)\s+(.{10,60})",
            re.IGNORECASE,
        )

        for row in cur.fetchall():
            match = pattern.search(row["body"])
            if match:
                name = match.group(1)
                reason = match.group(2).strip().rstrip(".")
                competitors.append((name, reason))

        # Deduplicate by competitor name
        seen = set()
        unique = []
        for name, reason in competitors:
            if name.lower() not in seen:
                seen.add(name.lower())
                unique.append((name, reason))

        return unique
