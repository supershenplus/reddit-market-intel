"""Cluster snapshot + delta analysis.

Snapshots the current clusters table to disk, then later compares the live
DB against a prior snapshot to surface what's NEW / GROWING / DEAD /
SCORE_CHANGED. Foundation for the monthly delta cadence (W5-11) and the
Levelset/Procore sunset chatter indicator (W5-12).

Cluster identity is the `label` field — `id` is not stable across `analyze
--force` runs because clusters are dropped and rebuilt. Labels can drift
slightly (different top TF-IDF terms surface as the cluster composition
shifts), which produces noise; acceptable for a monthly cadence.

Snapshot path layout:
    data/cluster_snapshots/<date>.json   (one file per snapshot date)

JSON shape: list of cluster dicts with the columns from the clusters table
plus a `snapshotted_at` ISO timestamp at the top level.
"""

import json
from datetime import datetime, date
from pathlib import Path

from storage.db import Database
from config import DATA_DIR


SNAPSHOT_DIR = DATA_DIR / "cluster_snapshots"

# How much avg_opportunity_score must move to count as a meaningful change.
SCORE_DELTA_THRESHOLD = 0.10


def snapshot_path(snapshot_date: str | date | None = None) -> Path:
    """Return the snapshot file path for the given date (default = today)."""
    if snapshot_date is None:
        snapshot_date = date.today().isoformat()
    elif isinstance(snapshot_date, date):
        snapshot_date = snapshot_date.isoformat()
    return SNAPSHOT_DIR / f"{snapshot_date}.json"


def save_snapshot(db: Database, snapshot_date: str | date | None = None) -> Path:
    """Persist current clusters table to a JSON snapshot file. Returns the path."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    clusters = db.get_all_clusters()
    path = snapshot_path(snapshot_date)
    payload = {
        "snapshotted_at": datetime.now().isoformat(),
        "clusters": clusters,
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def load_snapshot(path: Path) -> list[dict]:
    """Load clusters from a snapshot file. Returns [] if file missing."""
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("clusters", [])


def compute_delta(current: list[dict], baseline: list[dict]) -> dict:
    """Diff current clusters against a baseline snapshot.

    Identity is `label`. Returns four buckets:
      - new: clusters in current not in baseline
      - grown: matched clusters whose post_count increased
      - dead: clusters in baseline not in current
      - score_changed: matched clusters whose avg_opportunity_score moved
        beyond SCORE_DELTA_THRESHOLD in either direction
    """
    by_label_current = {c["label"]: c for c in current if c.get("label")}
    by_label_baseline = {c["label"]: c for c in baseline if c.get("label")}

    new_clusters = [
        by_label_current[label]
        for label in by_label_current
        if label not in by_label_baseline
    ]
    dead_clusters = [
        by_label_baseline[label]
        for label in by_label_baseline
        if label not in by_label_current
    ]

    grown = []
    score_changed = []
    for label in by_label_current:
        if label not in by_label_baseline:
            continue
        cur = by_label_current[label]
        base = by_label_baseline[label]
        cur_pc = cur.get("post_count") or 0
        base_pc = base.get("post_count") or 0
        if cur_pc > base_pc:
            grown.append({
                "label": label,
                "baseline_posts": base_pc,
                "current_posts": cur_pc,
                "delta_posts": cur_pc - base_pc,
                "current_score": cur.get("avg_opportunity_score") or 0,
            })
        cur_score = cur.get("avg_opportunity_score") or 0
        base_score = base.get("avg_opportunity_score") or 0
        if abs(cur_score - base_score) >= SCORE_DELTA_THRESHOLD:
            score_changed.append({
                "label": label,
                "baseline_score": base_score,
                "current_score": cur_score,
                "delta_score": cur_score - base_score,
            })

    # Order each bucket by the most action-worthy item first. Tuple-tiebreaker
    # form (sort_value, idx, payload) so .sort(reverse=True) never falls through
    # to comparing dict payloads.
    new_clusters = _sort_desc(
        new_clusters, lambda c: c.get("avg_opportunity_score") or 0
    )
    grown = _sort_desc(grown, lambda r: r["delta_posts"])
    dead_clusters = _sort_desc(
        dead_clusters, lambda c: c.get("avg_opportunity_score") or 0
    )
    score_changed = _sort_desc(score_changed, lambda r: abs(r["delta_score"]))

    return {
        "new": new_clusters,
        "grown": grown,
        "dead": dead_clusters,
        "score_changed": score_changed,
    }


def _sort_desc(items: list, extract) -> list:
    """Descending sort by an extracted scalar via tuple-tiebreaker form."""
    decorated = [(extract(it), i, it) for i, it in enumerate(items)]
    decorated.sort(reverse=True)
    return [t[2] for t in decorated]


def render_delta_report(
    delta: dict, baseline_date: str, current_date: str | None = None
) -> str:
    """Format a delta dict as a markdown report."""
    current_date = current_date or date.today().isoformat()
    lines = [
        f"# Cluster Delta Report — {baseline_date} → {current_date}",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Baseline snapshot**: {baseline_date}",
        f"**Current state**: {current_date}",
        "",
        "## Summary",
        "",
        f"- **New clusters**: {len(delta['new'])}",
        f"- **Grown clusters**: {len(delta['grown'])}",
        f"- **Dead clusters**: {len(delta['dead'])}",
        f"- **Score-changed**: {len(delta['score_changed'])} "
        f"(|delta| >= {SCORE_DELTA_THRESHOLD})",
        "",
        "---",
        "",
    ]

    if delta["new"]:
        lines.append("## New Clusters")
        lines.append("")
        lines.append("Clusters that did not exist in the baseline snapshot.")
        lines.append("")
        for c in delta["new"]:
            score = c.get("avg_opportunity_score") or 0
            posts = c.get("post_count") or 0
            lines.append(
                f"- **{c.get('label', '(no label)')}** — "
                f"score {score:.2f}, {posts} post{'s' if posts != 1 else ''}"
            )
        lines.append("")

    if delta["grown"]:
        lines.append("## Grown Clusters")
        lines.append("")
        lines.append("Clusters whose post count increased since the baseline.")
        lines.append("")
        for g in delta["grown"]:
            lines.append(
                f"- **{g['label']}** — "
                f"{g['baseline_posts']} → {g['current_posts']} posts "
                f"(+{g['delta_posts']}), score {g['current_score']:.2f}"
            )
        lines.append("")

    if delta["dead"]:
        lines.append("## Dead Clusters")
        lines.append("")
        lines.append(
            "Clusters present in the baseline but missing from current state — "
            "either no new posts have surfaced or the label drifted across "
            "re-clustering."
        )
        lines.append("")
        for d in delta["dead"]:
            score = d.get("avg_opportunity_score") or 0
            posts = d.get("post_count") or 0
            lines.append(
                f"- **{d.get('label', '(no label)')}** — "
                f"baseline score {score:.2f}, baseline {posts} post"
                f"{'s' if posts != 1 else ''}"
            )
        lines.append("")

    if delta["score_changed"]:
        lines.append("## Score Movement")
        lines.append("")
        lines.append(
            f"Clusters whose avg_opportunity_score moved by at least "
            f"{SCORE_DELTA_THRESHOLD} in either direction."
        )
        lines.append("")
        for s in delta["score_changed"]:
            arrow = "↑" if s["delta_score"] > 0 else "↓"
            lines.append(
                f"- **{s['label']}** — "
                f"{s['baseline_score']:.2f} → {s['current_score']:.2f} "
                f"({arrow} {abs(s['delta_score']):.2f})"
            )
        lines.append("")

    if not any(delta[k] for k in ("new", "grown", "dead", "score_changed")):
        lines.append("No cluster changes since baseline.")
        lines.append("")

    return "\n".join(lines)
