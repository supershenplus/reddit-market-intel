"""Export clustered opportunity reports for Claude Code analysis."""

import json
from collections import Counter
from datetime import datetime

from storage.db import Database
from analysis.market_signals import compute_lienclear_relevance, classify_lienclear_phase

try:
    from config import PROFILES, LIENCLEAR_COMPETITORS, LIENCLEAR_PHASE_LABELS
except ImportError:  # pragma: no cover — defensive for partial configs
    PROFILES = {}
    LIENCLEAR_COMPETITORS = []
    LIENCLEAR_PHASE_LABELS = {}


class ReportGenerator:
    """Generates structured markdown reports of market opportunities."""

    def __init__(self, db: Database, profile: str | None = None):
        self.db = db
        self.profile = profile
        self.profile_cfg = PROFILES.get(profile, {}) if profile else {}

    def generate(self, top_n: int = 20, min_score: float = 0.0) -> str:
        """Generate a clustered opportunity report."""
        clusters = self.db.get_all_clusters()
        clusters = [c for c in clusters if (c["avg_opportunity_score"] or 0) >= min_score]

        # Lienclear profile: enrich + re-rank by aggregated lienclear_relevance
        domain_section: list[str] = []
        if self.profile == "lienclear":
            min_rel = self.profile_cfg.get("min_relevance", 0.30)
            strong_rel = self.profile_cfg.get("strong_relevance", 0.50)
            min_posts = self.profile_cfg.get("min_cluster_posts", 2)
            enriched = []
            for c in clusters:
                meta = self._aggregate_lienclear_meta(c["id"])
                rel = meta["avg_relevance"]
                # Strong-signal singletons survive; marginal singletons get filtered as noise.
                if rel >= strong_rel or (rel >= min_rel and (c["post_count"] or 0) >= min_posts):
                    enriched.append({**c, "_lc": meta})
            enriched.sort(
                key=lambda c: (c["_lc"]["avg_relevance"], c["avg_opportunity_score"] or 0),
                reverse=True,
            )
            clusters = enriched[:top_n]
            # Domain-hit posts the RAG classifier dropped before clustering —
            # scanned straight from `posts`, independent of the classifier gate.
            domain_section = self._render_domain_hit_section(min_rel, top_n)
        else:
            clusters = clusters[:top_n]

        if not clusters and not domain_section:
            return "# Market Opportunity Report\n\nNo opportunities found above threshold.\n"

        title_suffix = f" ({self.profile})" if self.profile else ""
        lines = [
            f"# Market Opportunity Report{title_suffix} — {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"**Generated**: {datetime.now().isoformat()}",
            f"**Clusters shown**: {len(clusters)} (min score: {min_score})",
        ]
        if self.profile == "lienclear":
            lines.append(f"**Profile**: lienclear — ranked by avg lienclear_relevance, min {self.profile_cfg.get('min_relevance', 0.30):.2f}")
        lines.extend(["", "---", ""])

        # Profile-level Competitor Gap section (before clusters)
        if self.profile == "lienclear" and self.profile_cfg.get("include_competitor_gap_section"):
            gap_section = self._render_competitor_gap_section()
            if gap_section:
                lines.extend(gap_section)

        for rank, cluster in enumerate(clusters, 1):
            subreddits = json.loads(cluster["subreddits"]) if cluster["subreddits"] else []
            trending = "Yes" if cluster["trending"] else "No"

            lines.append(f"## Opportunity #{rank}: {cluster['label']}")
            if self.profile == "lienclear":
                lc = cluster.get("_lc", {})
                lines.append(
                    f"**Lienclear relevance**: {lc.get('avg_relevance', 0):.2f} | "
                    f"**Opportunity score**: {cluster['avg_opportunity_score']:.2f} | "
                    f"**Posts**: {cluster['post_count']}"
                )
                lines.append(f"**Subreddits**: {', '.join(subreddits)}")
                lc_facets = self._render_lienclear_facets(lc)
                if lc_facets:
                    lines.extend(lc_facets)
            else:
                lines.append(
                    f"**Score**: {cluster['avg_opportunity_score']:.2f} | "
                    f"**Posts**: {cluster['post_count']} | "
                    f"**Subreddits**: {', '.join(subreddits)}"
                )
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

        if domain_section:
            lines.extend(domain_section)

        return "\n".join(lines)

    # --- Lienclear profile helpers -------------------------------------------------

    def _render_domain_hit_section(self, min_rel: float, top_n: int) -> list[str]:
        """Render posts whose text hits Lienclear domain keywords, scored directly.

        Domain detection (`compute_lienclear_relevance`) is pure regex and does
        not depend on the RAG pain-point classifier. Scanning `posts` here
        recovers on-topic posts the classifier filtered out before they could
        reach a cluster — the complete raw domain signal in the corpus.

        Posts are bucketed into ProductBlueprint build phases (1/2/3) so the
        report surfaces "what to build next" not just "what's painful".
        Highest-phase-wins on multi-hit; phase-unclassified domain hits fall
        into Phase 1 (the baseline waiver/lien layer).
        """
        cur = self.db.conn.execute(
            "SELECT reddit_id, title, body, subreddit, url, score FROM posts"
        )
        hits = []
        for row in cur.fetchall():
            lc = compute_lienclear_relevance(
                row["title"] or "", row["body"] or "", row["subreddit"] or ""
            )
            if lc["domain_hit"] and lc["score"] >= min_rel:
                phase = classify_lienclear_phase(row["title"] or "", row["body"] or "") or 1
                hits.append((row, lc, phase))
        if not hits:
            return []
        # Sort by (score, idx) descending; idx tiebreaker keeps tuple compare
        # off the dict/row payloads if scores tie.
        hits_with_idx = [(hl[1]["score"], i, hl) for i, hl in enumerate(hits)]
        hits_with_idx.sort(reverse=True)
        hits = [t[2] for t in hits_with_idx[:top_n]]

        lines = [
            "## Domain-Hit Posts",
            "",
            "Posts whose text matches Lienclear domain keywords (lien waiver, AIA "
            "G702/G703, retainage, mechanics lien, pay-when-paid), scored directly "
            "by `compute_lienclear_relevance` — independent of the generic "
            "pain-point classifier. Partitioned by ProductBlueprint build phase "
            "(highest-phase-wins on multi-hit).",
            "",
        ]

        buckets: dict[int, list] = {1: [], 2: [], 3: []}
        for row, lc, phase in hits:
            buckets[phase].append((row, lc))

        for phase in (1, 2, 3):
            if not buckets[phase]:
                continue
            label = LIENCLEAR_PHASE_LABELS.get(phase, f"Phase {phase}")
            lines.append(f"### {label} ({len(buckets[phase])} post{'s' if len(buckets[phase]) != 1 else ''})")
            lines.append("")
            for i, (row, lc) in enumerate(buckets[phase], 1):
                title = (row["title"] or "(no title)")[:80]
                lines.append(
                    f"{i}. [r/{row['subreddit']}] \"{title}\" — "
                    f"relevance {lc['score']:.2f} (↑ {row['score'] or 0})"
                )
                facets = []
                if lc.get("states"):
                    facets.append("States: " + ", ".join(lc["states"]))
                if lc.get("role"):
                    facets.append(f"Role: {lc['role']}")
                if lc.get("dollar_anchors"):
                    facets.append("$ anchors: " + ", ".join(lc["dollar_anchors"]))
                if lc.get("competitor_mentions"):
                    facets.append("Competitors: " + ", ".join(lc["competitor_mentions"]))
                if lc.get("diy_evidence"):
                    facets.append("DIY: " + ", ".join(lc["diy_evidence"]))
                if lc.get("urgency"):
                    facets.append("Urgency: " + ", ".join(lc["urgency"]))
                if lc.get("frequency"):
                    facets.append("Frequency: " + ", ".join(lc["frequency"]))
                if facets:
                    lines.append(f"   - {' | '.join(facets)}")
                lines.append(f"   - URL: {row['url'] or 'N/A'}")
            lines.append("")

        lines.extend(["---", ""])
        return lines

    def _aggregate_lienclear_meta(self, cluster_id: int) -> dict:
        """Aggregate per-cluster Lienclear signal from matched_patterns JSON blobs."""
        cur = self.db.conn.execute(
            "SELECT matched_patterns FROM pain_points WHERE cluster_id = ?",
            (cluster_id,),
        )
        # Only count competitors still in the live config — stale matches from
        # earlier analyze runs (e.g. an over-broad name we later removed) are
        # filtered here without requiring full re-analysis.
        canonical = {c.lower(): c for c in LIENCLEAR_COMPETITORS}
        relevances: list[float] = []
        states: Counter = Counter()
        roles: Counter = Counter()
        dollars: Counter = Counter()
        competitors: Counter = Counter()
        diy: Counter = Counter()
        urgency: Counter = Counter()
        frequency: Counter = Counter()
        domain_hits = 0
        diy_hit_posts = 0
        urgency_hit_posts = 0
        frequency_hit_posts = 0
        total = 0
        for row in cur.fetchall():
            total += 1
            blob = row["matched_patterns"]
            if not blob:
                continue
            try:
                parsed = json.loads(blob)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            lc = parsed.get("lienclear") if isinstance(parsed, dict) else None
            if not lc:
                continue
            relevances.append(float(lc.get("score") or 0))
            for s in lc.get("states") or []:
                states[s] += 1
            if lc.get("role"):
                roles[lc["role"]] += 1
            for d in lc.get("dollar_anchors") or []:
                dollars[d] += 1
            for comp in lc.get("competitor_mentions") or []:
                key = comp.lower()
                if key in canonical:
                    competitors[canonical[key]] += 1
            post_diy = lc.get("diy_evidence") or []
            for d in post_diy:
                diy[d] += 1
            if post_diy:
                diy_hit_posts += 1
            post_urgency = lc.get("urgency") or []
            for u in post_urgency:
                urgency[u] += 1
            if post_urgency:
                urgency_hit_posts += 1
            post_frequency = lc.get("frequency") or []
            for f in post_frequency:
                frequency[f] += 1
            if post_frequency:
                frequency_hit_posts += 1
            if lc.get("domain_hit"):
                domain_hits += 1
        avg_relevance = sum(relevances) / len(relevances) if relevances else 0.0
        return {
            "avg_relevance": avg_relevance,
            "post_count": total,
            "domain_hit_rate": (domain_hits / total) if total else 0.0,
            "diy_evidence_rate": (diy_hit_posts / total) if total else 0.0,
            "urgency_rate": (urgency_hit_posts / total) if total else 0.0,
            "frequency_rate": (frequency_hit_posts / total) if total else 0.0,
            "states": states.most_common(5),
            "roles": roles.most_common(5),
            "dollar_anchors": dollars.most_common(5),
            "competitors": competitors.most_common(5),
            "diy_evidence": diy.most_common(5),
            "urgency": urgency.most_common(5),
            "frequency": frequency.most_common(5),
        }

    def _render_lienclear_facets(self, lc: dict) -> list[str]:
        lines = []
        if lc.get("states"):
            lines.append("**States**: " + ", ".join(f"{s} ({n})" for s, n in lc["states"]))
        if lc.get("roles"):
            lines.append("**Roles**: " + ", ".join(f"{r} ({n})" for r, n in lc["roles"]))
        if lc.get("dollar_anchors"):
            lines.append("**$ anchors**: " + ", ".join(f"{d} ({n})" for d, n in lc["dollar_anchors"]))
        if lc.get("competitors"):
            lines.append("**Competitor mentions**: " + ", ".join(f"{c} ({n})" for c, n in lc["competitors"]))
        if lc.get("diy_evidence"):
            lines.append("**DIY workarounds**: " + ", ".join(f"{d} ({n})" for d, n in lc["diy_evidence"]))
        if lc.get("urgency"):
            lines.append("**Urgency markers**: " + ", ".join(f"{u} ({n})" for u, n in lc["urgency"]))
        if lc.get("frequency"):
            lines.append("**Frequency markers**: " + ", ".join(f"{f} ({n})" for f, n in lc["frequency"]))
        lines.append(f"**Domain-hit rate**: {lc.get('domain_hit_rate', 0):.0%}")
        if lc.get("diy_evidence_rate", 0) > 0:
            lines.append(f"**DIY-evidence rate**: {lc.get('diy_evidence_rate', 0):.0%}")
        if lc.get("urgency_rate", 0) > 0:
            lines.append(f"**Urgency rate**: {lc.get('urgency_rate', 0):.0%}")
        if lc.get("frequency_rate", 0) > 0:
            lines.append(f"**Frequency rate**: {lc.get('frequency_rate', 0):.0%}")
        return lines

    def _render_competitor_gap_section(self) -> list[str]:
        """Top-level Competitor Gap section aggregating mentions across all clusters."""
        cur = self.db.conn.execute(
            "SELECT matched_patterns FROM pain_points WHERE matched_patterns IS NOT NULL"
        )
        canonical = {c.lower(): c for c in LIENCLEAR_COMPETITORS}
        comp_counts: Counter = Counter()
        for row in cur.fetchall():
            try:
                parsed = json.loads(row["matched_patterns"])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            lc = parsed.get("lienclear") if isinstance(parsed, dict) else None
            if not lc:
                continue
            for comp in lc.get("competitor_mentions") or []:
                key = comp.lower()
                if key in canonical:
                    comp_counts[canonical[key]] += 1
        if not comp_counts:
            return []
        lines = [
            "## Competitor Gap Analysis",
            "",
            "Named-competitor mentions extracted across all Lienclear-relevant pain points. "
            "Frequency indicates where existing tools are being discussed (often negatively).",
            "",
        ]
        for comp, count in comp_counts.most_common(len(LIENCLEAR_COMPETITORS) or 10):
            lines.append(f"- **{comp}** — {count} mention{'s' if count != 1 else ''}")
            quote = self._sample_negative_quote(comp)
            if quote:
                lines.append(f"  > {quote}")
        lines.extend(["", "---", ""])
        return lines

    def _sample_negative_quote(self, competitor: str) -> str | None:
        """Find one short negative-product comment mentioning this competitor."""
        import re as _re

        cur = self.db.conn.execute(
            "SELECT body FROM comments WHERE product_negative = 1 AND body LIKE ? LIMIT 20",
            (f"%{competitor}%",),
        )
        # Apply word-boundary check in Python (SQL LIKE is too permissive — e.g.
        # 'Handle' would match 'handled'). Caller already filtered to competitors
        # present in the precompiled regex set.
        pattern = _re.compile(r"\b" + _re.escape(competitor) + r"\b", _re.IGNORECASE)
        for row in cur.fetchall():
            body = (row["body"] or "").replace("\n", " ").strip()
            if pattern.search(body):
                return (body[:200] + "…") if len(body) > 200 else body
        return None

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
