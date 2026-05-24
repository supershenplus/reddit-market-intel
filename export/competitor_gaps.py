"""Per-competitor gap report for the Lienclear research profile.

Standalone export — decoupled from the main opportunity report so it can be
re-generated on its own and consumed directly by the Lienclear repo.

For each named competitor in `LIENCLEAR_COMPETITORS` that appears in the
corpus: total mention count (from pain_point matched_patterns), the top
pain-pointed posts mentioning that competitor, and negative-quote excerpts
from comments. Output is a markdown file written to disk.
"""

import json
import re
from collections import Counter
from datetime import datetime

from storage.db import Database
from config import LIENCLEAR_COMPETITORS
from analysis.market_signals import compute_lienclear_relevance


class CompetitorGapReport:
    """Generates a per-competitor gap report from pain_points + comments."""

    def __init__(self, db: Database, posts_per_competitor: int = 5, quotes_per_competitor: int = 5):
        self.db = db
        self.posts_per_competitor = posts_per_competitor
        self.quotes_per_competitor = quotes_per_competitor
        self._canonical = {c.lower(): c for c in LIENCLEAR_COMPETITORS}

    def generate(self) -> str:
        counts = self._mention_counts()
        if not counts:
            return (
                "# Lienclear Competitor Gap Report\n\n"
                "No competitor mentions found in pain_points. "
                "Run `python main.py analyze` against a Lienclear-relevant corpus first.\n"
            )

        lines = [
            "# Lienclear Competitor Gap Report",
            "",
            f"**Generated**: {datetime.now().isoformat()}",
            f"**Competitors with mentions**: {len(counts)} of {len(LIENCLEAR_COMPETITORS)}",
            "",
            "## Summary",
            "",
        ]
        for comp, n in counts.most_common():
            lines.append(f"- **{comp}** — {n} mention{'s' if n != 1 else ''}")
        lines.extend(["", "---", ""])

        for comp, n in counts.most_common():
            lines.append(f"## {comp} — {n} mention{'s' if n != 1 else ''}")
            lines.append("")

            posts = self._top_posts_for_competitor(comp)
            if posts:
                lines.append(f"### Top posts mentioning {comp}")
                for i, p in enumerate(posts, 1):
                    title = (p["title"] or "(no title)")[:100]
                    lines.append(
                        f"{i}. [r/{p['subreddit']}] \"{title}\" "
                        f"(↑ {p['score'] or 0}) — relevance {p['relevance']:.2f}"
                    )
                    heat_signals = self._heat_signals_for_post(p)
                    if heat_signals:
                        lines.append(f"   - {heat_signals}")
                    lines.append(f"   URL: {p['url'] or 'N/A'}")
                lines.append("")

            quotes = self._negative_quotes_for_competitor(comp)
            if quotes:
                lines.append(f"### Negative quotes from comments")
                for q in quotes:
                    body = q["body"].replace("\n", " ").strip()
                    excerpt = (body[:300] + "…") if len(body) > 300 else body
                    lines.append(f"> {excerpt}")
                    lines.append(f">   — r/{q['subreddit']} · ↑ {q['score'] or 0}")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    # --- helpers ---------------------------------------------------------------

    def _mention_counts(self) -> Counter:
        """Total competitor mention count across all pain_points."""
        counts: Counter = Counter()
        cur = self.db.conn.execute(
            "SELECT matched_patterns FROM pain_points WHERE matched_patterns IS NOT NULL"
        )
        for row in cur.fetchall():
            for comp in self._extract_competitors(row["matched_patterns"]):
                counts[comp] += 1
        return counts

    def _extract_competitors(self, blob: str) -> list[str]:
        try:
            parsed = json.loads(blob)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        lc = parsed.get("lienclear") if isinstance(parsed, dict) else None
        if not lc:
            return []
        out = []
        for comp in lc.get("competitor_mentions") or []:
            canon = self._canonical.get(comp.lower())
            if canon:
                out.append(canon)
        return out

    def _top_posts_for_competitor(self, competitor: str) -> list[dict]:
        """Posts whose pain_point matched_patterns mentions this competitor."""
        cur = self.db.conn.execute(
            """SELECT p.title, p.body, p.subreddit, p.url, p.score, p.reddit_id,
                      pp.matched_patterns, pp.opportunity_score
               FROM pain_points pp
               JOIN posts p ON pp.post_id = p.id
               WHERE pp.matched_patterns IS NOT NULL
               ORDER BY pp.opportunity_score DESC"""
        )
        hits = []
        for row in cur.fetchall():
            comps = self._extract_competitors(row["matched_patterns"])
            if competitor not in comps:
                continue
            try:
                parsed = json.loads(row["matched_patterns"])
                lc = parsed.get("lienclear", {})
                relevance = float(lc.get("score") or 0)
                urgency = lc.get("urgency") or []
                frequency = lc.get("frequency") or []
            except (TypeError, ValueError, json.JSONDecodeError, AttributeError):
                relevance = 0.0
                urgency = []
                frequency = []
            hits.append({
                "title": row["title"],
                "body": row["body"],
                "subreddit": row["subreddit"],
                "url": row["url"],
                "score": row["score"],
                "relevance": relevance,
                "urgency": urgency,
                "frequency": frequency,
            })
            if len(hits) >= self.posts_per_competitor:
                break
        return hits

    def _heat_signals_for_post(self, post: dict) -> str:
        """Compact one-liner of urgency + frequency markers when present.

        Falls back to a live `compute_lienclear_relevance` scan on the
        title+body if the stored facets are absent (e.g. pain_point was
        classified before urgency/frequency landed — handles the gap
        gracefully without requiring --force re-analyze).
        """
        urgency = post.get("urgency") or []
        frequency = post.get("frequency") or []
        if not urgency and not frequency:
            lc_live = compute_lienclear_relevance(
                post.get("title") or "", post.get("body") or "",
                post.get("subreddit") or "",
            )
            urgency = lc_live.get("urgency") or []
            frequency = lc_live.get("frequency") or []
        parts = []
        if urgency:
            parts.append("Urgency: " + ", ".join(urgency[:5]))
        if frequency:
            parts.append("Frequency: " + ", ".join(frequency[:5]))
        return " | ".join(parts)

    def _negative_quotes_for_competitor(self, competitor: str) -> list[dict]:
        """Negative comments mentioning the competitor by word-boundary match."""
        pattern = re.compile(r"\b" + re.escape(competitor) + r"\b", re.IGNORECASE)
        cur = self.db.conn.execute(
            """SELECT c.body, c.score, p.subreddit
               FROM comments c
               JOIN posts p ON c.post_reddit_id = p.reddit_id
               WHERE c.product_negative = 1 AND c.body LIKE ?
               ORDER BY c.score DESC
               LIMIT ?""",
            (f"%{competitor}%", self.quotes_per_competitor * 4),
        )
        out = []
        for row in cur.fetchall():
            body = row["body"] or ""
            if pattern.search(body):
                out.append({
                    "body": body,
                    "score": row["score"],
                    "subreddit": row["subreddit"],
                })
            if len(out) >= self.quotes_per_competitor:
                break
        return out
