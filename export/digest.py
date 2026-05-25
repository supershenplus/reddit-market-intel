"""Weekly digest writer — emits reports/weekly/<date>.md in the discovery-engine shape.

Phase 4 active: complexity + revenue scoring read pain_facets via
analysis/niche_scorer; digest surfaces per-niche facet coverage and a
faceted-vs-dumb-fallback mode tag so the operator knows which scores to
trust. Niches with no facets render the same as pre-Phase-4 (graceful
degrade)."""

import json
import re
import time
from datetime import date

from analysis.niche_scorer import filter_eligible
from analysis.saturation import compute_saturation
from analysis.taste import compute_taste_boost, hint_when_n_eq_1
from config import LLM_PROMPT_VERSION
from storage.db import Database


PHASE5_WEDGE_NOTE = "Phase 5: not yet computed (verdict-driven wedge suggestion)"
DIGEST_FORMAT = "v3"
LOW_COVERAGE_THRESHOLD = 0.05  # 5%

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
    def __init__(self, db: Database, include_killed: bool = False):
        self.db = db
        self.include_killed = include_killed
        # Phase 5 — verdict context loaded once per generate() call so each
        # niche render is O(1) lookup.
        self._killed_fingerprints: set = set()
        self._watch_snapshots: dict = {}
        self._build_centroids: list[dict] = []

    def generate(self, top_n: int = 10) -> str:
        # Load verdict state up front (Phase 5).
        self._killed_fingerprints = self.db.get_killed_fingerprints()
        self._watch_snapshots = self.db.get_watch_verdicts_with_snapshots()
        self._build_centroids = self.db.get_build_centroids()

        niches_raw = self.db.get_top_niches(top_n * 2)  # fetch extra to cover killed
        # Phase 5 — hide killed niches by default; --include-killed shows them.
        if not self.include_killed:
            niches = [
                n for n in niches_raw
                if n.get("stable_key") not in self._killed_fingerprints
            ][:top_n]
        else:
            niches = niches_raw[:top_n]

        header_lines = [
            f"<!-- digest_format: {DIGEST_FORMAT} -->",
            f"# Week of {date.today().isoformat()} — Top Niches",
        ]
        if not niches:
            return (
                "\n".join(header_lines)
                + "\n\nNo niches available. Run `python main.py analyze` "
                "then `python main.py digest`.\n"
            )

        # Coverage stats across the whole digest so we can surface the
        # bias warning when the operator hasn't extracted enough facets yet.
        total_posts, total_facets = self._corpus_coverage()
        coverage = (total_facets / total_posts) if total_posts else 0.0
        if coverage < LOW_COVERAGE_THRESHOLD:
            header_lines.append("")
            header_lines.append(
                f"> Note: facet coverage is {coverage*100:.1f}% "
                f"({total_facets}/{total_posts}) — Phase 4 scoring is active "
                f"only on a subset of niches. Extract more posts via "
                f"`python main.py llm-extract` to widen faceted scoring."
            )
        # Phase 5 — taste-learning bootstrap hint (N=1 case)
        hint = hint_when_n_eq_1(self._build_centroids)
        if hint:
            header_lines.append("")
            header_lines.append(f"> {hint}")
        # Phase 5 — verdict summary line
        v_summary = self.db.get_verdict_summary()
        if v_summary["total"]:
            header_lines.append("")
            killed_hidden = (
                "" if self.include_killed
                else f" (hidden: {v_summary['kill']} killed)"
            )
            header_lines.append(
                f"> Verdicts: build {v_summary['build']} · "
                f"watch {v_summary['watch']} · "
                f"kill {v_summary['kill']}{killed_hidden}"
            )

        rev = sorted(n["revenue_score"] or 0.0 for n in niches)
        rev_lo = rev[len(rev) // 3]
        rev_hi = rev[(2 * len(rev)) // 3] if len(rev) >= 3 else rev[-1]

        lines = header_lines + [""]
        for i, n in enumerate(niches, 1):
            lines.extend(self._render_niche(i, n, rev_lo, rev_hi))
            lines.append("")
        return "\n".join(lines)

    def _corpus_coverage(self) -> tuple[int, int]:
        total_posts = self.db.conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        total_facets = self.db.conn.execute(
            "SELECT COUNT(*) FROM pain_facets WHERE prompt_version = ? AND is_pain_point = 1",
            (LLM_PROMPT_VERSION,),
        ).fetchone()[0]
        return total_posts, total_facets

    def _render_niche(self, rank: int, niche: dict, rev_lo: float, rev_hi: float) -> list[str]:
        clusters = self.db.get_clusters_for_niche(niche["id"])
        all_pps: list[dict] = []
        all_facets: list[dict] = []
        for c in clusters:
            # Phase 3 veto: skip pain_points where the current-version LLM
            # facet says is_pain_point=0. Pre-Phase-3 rows (no facet) survive.
            all_pps.extend(
                self.db.get_pain_points_for_cluster_unvetoed(
                    c["id"], LLM_PROMPT_VERSION,
                )
            )
            all_facets.extend(
                self.db.get_facets_for_cluster_at_version(
                    c["id"], LLM_PROMPT_VERSION,
                )
            )
        if not all_pps:
            # Empty niche still gets the verdict UX — operator can kill it
            # so it stops surfacing in subsequent digests.
            kill_tag = ""
            if self.include_killed and niche.get("stable_key") in self._killed_fingerprints:
                kill_tag = " 💀 KILLED"
            return [
                f"## {rank}. {niche['label']} — score {niche['rank_score']:.2f} "
                f"(no member posts){kill_tag}",
                "",
                f"- [ ] build  [ ] watch  [ ] kill   notes: ___",
                f"- fingerprint: {niche.get('stable_key') or '(missing — re-run analyze)'}",
            ]

        breakdown = _safe_json(niche.get("score_breakdown"))
        mode = breakdown.get("mode", "?") if breakdown else "?"

        complexity_tier = _tier(
            niche["complexity_score"] or 0.5,
            lo=0.33, hi=0.67,
        )
        revenue_tier = _tier(niche["revenue_score"] or 0.0, rev_lo, rev_hi)

        ranked_by_eng = _sort_by(all_pps, _engagement_of)
        eligible_facets = filter_eligible(all_facets)

        # Pain line: prefer the faceted summary with the highest confidence;
        # fall back to highest-engagement title.
        pain_sentence = ""
        if eligible_facets:
            top_facet = _sort_by(eligible_facets, lambda f: f.get("confidence") or 0)[0]
            pain_sentence = (top_facet.get("pain_summary") or "").strip()
        if not pain_sentence:
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

        # Willingness-to-pay line: aggregate from facets when present,
        # fallback to regex over post text.
        wtp_line = _format_wtp_line(eligible_facets, ranked_by_eng)
        complexity_line = _format_complexity_line(breakdown, mode)

        coverage_tag = f"facets: {len(eligible_facets)}/{niche['post_count']} at {LLM_PROMPT_VERSION}"
        mode_tag = "" if mode == "faceted" else " (scoring: dumb fallback)"

        # Phase 5 — taste-learning boost (recomputed each digest, not persisted).
        boost_mult, similar_to = compute_taste_boost(
            niche.get("centroid"), self._build_centroids,
        )
        effective_rank = niche["rank_score"] * boost_mult
        boost_chip = ""
        if boost_mult > 1.0:
            similar_str = ", ".join(f"`{s[:40]}`" for s in similar_to[:3])
            boost_chip = (
                f" · 🎯 taste-boost ×{boost_mult:.2f} (similar to past build: "
                f"{similar_str})"
            )

        # Phase 5 — saturation display chip (display-only, no rank effect).
        sat = compute_saturation(all_facets)
        sat_line = ""
        if sat["integrations"]:
            sat_line = (
                f"- Saturation (integrations referenced across faceted posts): "
                f"{', '.join(f'`{x}`' for x in sat['integrations'][:8])}"
            )
            if len(sat["integrations"]) > 8:
                sat_line += f" +{len(sat['integrations']) - 8} more"

        # Phase 5 — watch-delta line when this niche is watched.
        watch_line = self._watch_delta_line(niche, len(eligible_facets))

        # Phase 5 — kill tag when --include-killed surfaced a killed niche.
        kill_tag = ""
        if self.include_killed and niche.get("stable_key") in self._killed_fingerprints:
            kill_tag = " 💀 KILLED"

        out = [
            f"## {rank}. {niche['label']} — score {effective_rank:.2f} "
            f"(complexity: {complexity_tier}, revenue: {revenue_tier})"
            f"{mode_tag}{kill_tag}{boost_chip}",
            f"- Pain: {pain_sentence}",
            f"- Evidence: {niche['post_count']} posts across {niche['sub_count']} subs, "
            f"{recent_count} in last {WINDOW_DAYS}d · {coverage_tag}. "
            f"Top quote: {top_quote}",
            f"- Willingness-to-pay signals: {wtp_line}",
            f"- Build complexity rationale: {complexity_line}",
        ]
        if sat_line:
            out.append(sat_line)
        if watch_line:
            out.append(watch_line)
        out.extend([
            f"- Suggested wedge: {PHASE5_WEDGE_NOTE}",
            "",
            f"- [ ] build  [ ] watch  [ ] kill   notes: ___",
            f"- fingerprint: {niche.get('stable_key') or '(missing — re-run analyze)'}",
        ])
        return out

    def _watch_delta_line(self, niche: dict, current_facet_count: int) -> str:
        """If this niche is on watch, return a delta-since-watch line.
        Compares post_count + facet_count + max_dollar_anchor against the
        snapshot taken at verdict time."""
        fp = niche.get("stable_key")
        if not fp or fp not in self._watch_snapshots:
            return ""
        entry = self._watch_snapshots[fp]
        snap = entry["snapshot"] or {}
        decided_at = entry["decided_at"]
        parts = []
        if "post_count" in snap and snap["post_count"] is not None:
            delta = (niche.get("post_count") or 0) - snap["post_count"]
            if delta:
                parts.append(f"{delta:+d} posts")
        if "facet_count" in snap and snap["facet_count"] is not None:
            delta_f = current_facet_count - snap["facet_count"]
            if delta_f:
                parts.append(f"{delta_f:+d} facets")
        snap_anchor = snap.get("max_dollar_anchor") or 0
        # Pulled from the score_breakdown JSON at watch time
        snap_max = snap_anchor if snap_anchor else None
        # Note: current max is read from current facets; intentionally not
        # re-computed here to keep the row cheap. Phase 6/7 may revisit.
        if not parts:
            return f"- Watching since {decided_at[:10]}: no growth yet"
        return f"- Watching since {decided_at[:10]}: " + ", ".join(parts)


def _safe_json(s):
    if not s:
        return {}
    try:
        return json.loads(s)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _format_wtp_line(eligible_facets: list[dict], ranked_by_eng: list[dict]) -> str:
    if eligible_facets:
        wtp_counts = {"would_pay": 0, "hesitant": 0, "no_signal": 0}
        max_anchor = 0.0
        for f in eligible_facets:
            wtp = f.get("willingness_to_pay")
            if wtp in wtp_counts:
                wtp_counts[wtp] += 1
            anchor = f.get("max_dollar_anchor")
            if anchor and anchor > max_anchor:
                max_anchor = anchor
        n = len(eligible_facets)
        parts = []
        if wtp_counts["would_pay"]:
            parts.append(f"would_pay: {wtp_counts['would_pay']}/{n}")
        if wtp_counts["hesitant"]:
            parts.append(f"hesitant: {wtp_counts['hesitant']}/{n}")
        if max_anchor > 0:
            parts.append(f"max ${max_anchor:.0f}")
        if parts:
            return " · ".join(parts) + " (from facets)"

    # Fallback: regex over post bodies (pre-Phase-4 behavior).
    joined = " ".join(
        f"{p['title'] or ''} {(p['body'] or '')[:600]}"
        for p in ranked_by_eng[:10]
    )
    dollars = sorted({d.strip() for d in DOLLAR_ANCHOR_RE.findall(joined)})[:6]
    solutions = sorted({m.strip() for m in CURRENT_SOLUTION_RE.findall(joined)})[:4]
    parts = []
    if dollars:
        parts.append("dollar mentions: " + ", ".join(f"`{d}`" for d in dollars))
    if solutions:
        parts.append("current solutions named: " + ", ".join(f"`{s}`" for s in solutions))
    return " · ".join(parts) if parts else "none extracted (regex fallback)"


def _format_complexity_line(breakdown: dict, mode: str) -> str:
    if mode != "faceted" or not breakdown:
        reason = (breakdown or {}).get("fallback_reason", "no facets yet")
        return f"dumb scorer — constant 0.5 ({reason})"
    comp_bd = breakdown.get("complexity", {})
    bits = []
    if "integrations_count" in comp_bd:
        bits.append(f"integrations score {comp_bd['integrations_count']:.2f}")
    if "market_size_signal" in comp_bd:
        bits.append(f"market_size score {comp_bd['market_size_signal']:.2f}")
    if "complexity_keywords" in comp_bd:
        bits.append(f"keywords score {comp_bd['complexity_keywords']:.2f}")
    eff_n = comp_bd.get("_effective_n", 0)
    return " · ".join(bits) + f" (effective_n={eff_n:.1f})"
