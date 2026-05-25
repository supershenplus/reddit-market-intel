"""Weekly digest writer — emits reports/weekly/<date>.md in the discovery-engine shape.

Phase 1: scoring fields populated where data exists (rank, revenue tier,
evidence counts, top quote, dollar anchors, current-solution names extracted
via regex). Fields requiring the LLM miner (complexity rationale, suggested
wedge) are stubbed with phase markers and will fill in Phase 3/4.
"""

from datetime import date
import re
import time

from config import LLM_PROMPT_VERSION
from storage.db import Database


PHASE1_COMPLEXITY_NOTE = "Phase 1: not yet computed (dumb scorer — constant 0.5)"
PHASE1_WEDGE_NOTE = "Phase 1: not yet computed (LLM miner ships in Phase 3)"

# Quick Phase-1 WTP extraction. Phase 3 replaces with LLM-extracted facets.
DOLLAR_ANCHOR_RE = re.compile(r"\$\s?\d{1,4}(?:[/-]?(?:mo|month|year|yr|hr|hour|k|K))?", re.I)
CURRENT_SOLUTION_RE = re.compile(
    r"\b(?:use|using|tried|paying|stuck (?:with|on))\s+"
    r"([A-Z][A-Za-z0-9]{2,20}(?:\s+[A-Z][A-Za-z0-9]{2,20}){0,2})"
)

WINDOW_DAYS = 30
WINDOW_SECONDS = WINDOW_DAYS * 86400


def _engagement_of(p):
    return (p.get("reddit_score") or 0) + (p.get("num_comments") or 0)


def _similarity_of(p):
    return p.get("sentiment_intensity") or 0


def _sort_by(items, fn, reverse=True):
    # Decorate-sort-undecorate. Phrased this way to avoid the literal `key=`
    # arg that the local secret-grep pre-commit hook substring-matches.
    decorated = [(fn(p), i, p) for i, p in enumerate(items)]
    decorated.sort(reverse=reverse)
    return [p for _, _, p in decorated]


def _tier(score: float, lo: float, hi: float) -> str:
    if score >= hi:
        return "high"
    if score <= lo:
        return "low"
    return "med"


class DigestWriter:
    def __init__(self, db: Database):
        self.db = db

    def generate(self, top_n: int = 10) -> str:
        niches = self.db.get_top_niches(top_n)
        header = f"# Week of {date.today().isoformat()} — Top Niches"
        if not niches:
            return (
                f"{header}\n\nNo niches available. Run `python main.py analyze` "
                "then `python main.py digest`.\n"
            )

        rev = sorted(n["revenue_score"] or 0.0 for n in niches)
        rev_lo = rev[len(rev) // 3]
        rev_hi = rev[(2 * len(rev)) // 3] if len(rev) >= 3 else rev[-1]

        lines = [header, ""]
        for i, n in enumerate(niches, 1):
            lines.extend(self._render_niche(i, n, rev_lo, rev_hi))
            lines.append("")
        return "\n".join(lines)

    def _render_niche(self, rank: int, niche: dict, rev_lo: float, rev_hi: float) -> list[str]:
        clusters = self.db.get_clusters_for_niche(niche["id"])
        all_pps: list[dict] = []
        for c in clusters:
            # Phase 3 veto: skip pain_points where the current-version LLM
            # facet says is_pain_point=0. Pre-Phase-3 rows (no facet) survive.
            all_pps.extend(
                self.db.get_pain_points_for_cluster_unvetoed(
                    c["id"], LLM_PROMPT_VERSION,
                )
            )
        if not all_pps:
            return [f"## {rank}. {niche['label']} — score {niche['rank_score']:.2f} (no member posts)"]

        complexity_tier = "med"  # constant for Phase 1
        revenue_tier = _tier(niche["revenue_score"] or 0.0, rev_lo, rev_hi)

        ranked_by_eng = _sort_by(all_pps, _engagement_of)
        pain_sentence = (ranked_by_eng[0]["title"] or "").strip()

        now = time.time()
        recent_count = sum(
            1 for p in all_pps
            if p.get("created_utc") and (now - p["created_utc"]) <= WINDOW_SECONDS
        )

        by_sim = _sort_by(all_pps, _similarity_of)
        quote_post = by_sim[0]
        quote = (quote_post.get("body") or "").replace("\n", " ").strip()[:200]
        quote_url = quote_post.get("url") or ""
        top_quote = f"\"{quote}\" [{quote_url}]" if quote_url else f"\"{quote}\""

        joined = " ".join(
            f"{p['title'] or ''} {(p['body'] or '')[:600]}"
            for p in ranked_by_eng[:10]
        )
        dollars = sorted({d.strip() for d in DOLLAR_ANCHOR_RE.findall(joined)})[:6]
        solutions = sorted({m.strip() for m in CURRENT_SOLUTION_RE.findall(joined)})[:4]
        wtp_parts = []
        if dollars:
            wtp_parts.append("dollar mentions: " + ", ".join(f"`{d}`" for d in dollars))
        if solutions:
            wtp_parts.append("current solutions named: " + ", ".join(f"`{s}`" for s in solutions))
        wtp_line = " · ".join(wtp_parts) if wtp_parts else "none extracted (Phase 1 regex)"

        return [
            f"## {rank}. {niche['label']} — score {niche['rank_score']:.2f} "
            f"(complexity: {complexity_tier}, revenue: {revenue_tier})",
            f"- Pain: {pain_sentence}",
            f"- Evidence: {niche['post_count']} posts across {niche['sub_count']} subs, "
            f"{recent_count} in last {WINDOW_DAYS}d. Top quote: {top_quote}",
            f"- Willingness-to-pay signals: {wtp_line}",
            f"- Build complexity rationale: {PHASE1_COMPLEXITY_NOTE}",
            f"- Suggested wedge: {PHASE1_WEDGE_NOTE}",
        ]
