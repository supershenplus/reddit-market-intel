"""Phase 3 LLM pain-miner — batch-mode export + import.

Flow:
1. `select_posts` picks candidates (resume by prompt_version + optional RAG
   pre-filter in strict / sampled / off modes).
2. `export_batches` writes them as markdown files + manifest.json under
   data/llm_batches/<UTC-timestamp>/.
3. Operator opens a Claude Code session against their Max sub, processes
   each batch per the embedded schema, writes facets JSON next to each
   batch file (e.g. `batch_001_facets.json`).
4. `import_facets` validates schema fingerprint + per-batch sha256, then
   UPSERTs into pain_facets via Database.upsert_pain_facet.

API mode (paid Anthropic SDK) is Phase 3.5 — this module has zero new deps.
"""

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import (
    LLM_BATCH_DIR,
    LLM_BATCH_SIZE,
    LLM_MAX_POSTS_PER_RUN,
    LLM_PROMPT_VERSION,
)
from storage.db import Database


# --- Schema spec -----------------------------------------------------------

# Authoritative facet schema. The schema_fingerprint derives from this
# literal list, so any change here MUST be paired with bumping
# LLM_PROMPT_VERSION in config.py — otherwise the importer will refuse
# files generated against the prior schema. The (name, type, description)
# tuples drive both the prompt rendering AND the import validator, so
# the operator and the loader can't drift apart.
FACET_FIELDS = [
    ("is_pain_point", "bool",
     "true if the post is a legitimate user pain point worth ranking; "
     "false for off-topic, meta, support-only, or clearly-not-a-pain content"),
    ("pain_summary", "str",
     "one short sentence (<=140 chars) summarizing the pain in user-facing language"),
    ("domain", "str",
     "one of: b2b_saas | vertical_saas | dev_tools | marketing | freelance | "
     "ecommerce | property | construction | services | automation | "
     "operations | leadership | other"),
    ("current_solution", "str | null",
     "what the author says they currently use (e.g. 'Excel', 'Procore', "
     "'manual process', 'nothing'); null when not mentioned"),
    ("integrations_mentioned", "str[]",
     "named tools/services the author mentions (e.g. ['QuickBooks', 'Stripe']); "
     "empty array when none"),
    ("dollar_anchors", "str[]",
     "explicit money amounts (e.g. ['$50/mo', '$2000 setup']); empty array when none"),
    ("max_dollar_anchor", "float | null",
     "the largest monthly-equivalent USD value mentioned, normalized "
     "(e.g. '$2400/yr' -> 200.0); null when no $ mentioned"),
    ("willingness_to_pay", "str",
     "one of: would_pay | hesitant | no_signal"),
    ("urgency", "str",
     "one of: blocking | recurring | nice_to_have | none"),
    ("buyer_role", "str | null",
     "if discernible: owner | manager | individual_contributor | finance | it | other; "
     "null when unclear"),
    ("market_size_signal", "str | null",
     "one of: enterprise | smb | prosumer | hobbyist; null when unclear"),
    ("confidence", "float",
     "your self-rated confidence in this extraction, 0.0-1.0"),
]

_VALID_WTP = {"would_pay", "hesitant", "no_signal"}
_VALID_URGENCY = {"blocking", "recurring", "nice_to_have", "none"}
_VALID_DOMAINS = {
    "b2b_saas", "vertical_saas", "dev_tools", "marketing", "freelance",
    "ecommerce", "property", "construction", "services", "automation",
    "operations", "leadership", "other",
}


def schema_fingerprint() -> str:
    """sha256[:16] of FACET_FIELDS. The manifest stores this; import refuses
    files generated against a different schema. Cheap insurance against
    silent shape drift between export and import."""
    payload = json.dumps(FACET_FIELDS, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _render_schema_for_prompt() -> str:
    return "\n".join(
        f"- `{name}` ({typ}): {desc}" for name, typ, desc in FACET_FIELDS
    )


PROMPT_HEADER = """\
# Pain-point facet extraction

You are extracting structured facets from Reddit posts so they can be
scored as potential SaaS opportunities. For each post below, output one
JSON object with these fields:

{schema}

## Rules
- Return a JSON array, one object per post, in the same order as the input.
- Each object MUST include `post_id` (echo back the input id) so the
  importer can match results to source posts.
- When uncertain, prefer `confidence: 0.3` over making up facts.
- `is_pain_point: false` is the right call for: pure tool-recommendation
  asks with no pain expressed, meta/announcement posts, "look at my project"
  show-offs, off-topic content. The point is to filter noise, not to
  classify every post as a pain.

Schema fingerprint: `{fingerprint}`
Prompt version: `{version}`
"""


# --- Pre-filter + selection ------------------------------------------------

def select_posts(
    db: Database,
    prefilter: str = "strict",
    max_posts: int = LLM_MAX_POSTS_PER_RUN,
    re_extract: bool = False,
    sample_rate: float = 0.10,
    rag_classifier=None,
) -> list[dict]:
    """Return posts to extract, each tagged with `_prefilter` source.

    - `re_extract=False`: skip posts with a current-version facet (resume).
    - `prefilter='strict'`: only RAG-positive posts (steady-state).
    - `prefilter='sampled'`: RAG-positive + sample_rate fraction of RAG-negative
      (recall audit).
    - `prefilter='off'`: all candidates (backfills, version migrations).

    `rag_classifier` is injectable for tests; in normal use it's lazily
    imported so this module stays importable without sentence-transformers.
    """
    if re_extract:
        candidates = [dict(r) for r in db.conn.execute("SELECT * FROM posts")]
    else:
        candidates = db.get_posts_without_facets(LLM_PROMPT_VERSION)
    if not candidates:
        return []

    if prefilter == "off":
        return _tag_and_cap(candidates, "no_filter", max_posts)

    if prefilter not in ("strict", "sampled"):
        raise ValueError(
            f"Unknown prefilter mode: {prefilter!r}. Use strict|sampled|off."
        )

    if rag_classifier is None:
        from analysis.rag_classifier import RAGClassifier
        rag_classifier = RAGClassifier()

    rag_pass, rag_fail = [], []
    for p in candidates:
        if rag_classifier.classify(p["title"] or "", p["body"] or "") is not None:
            p["_prefilter"] = "rag_pass"
            rag_pass.append(p)
        else:
            p["_prefilter"] = "rag_fail_sampled"
            rag_fail.append(p)

    if prefilter == "strict":
        return rag_pass[:max_posts]

    # sampled mode: rag_pass + a slice of rag_fail for recall audit
    rng = random.Random(42)
    sample_size = max(1, int(len(rag_fail) * sample_rate))
    sample_size = min(sample_size, len(rag_fail))
    sampled = rng.sample(rag_fail, sample_size) if sample_size > 0 else []
    combined = rag_pass + sampled
    rng.shuffle(combined)
    return combined[:max_posts]


def _tag_and_cap(posts: list[dict], source: str, max_posts: int) -> list[dict]:
    capped = posts[:max_posts]
    for p in capped:
        p["_prefilter"] = source
    return capped


# --- Batch export ----------------------------------------------------------

def export_batches(
    posts: list[dict],
    batch_size: int = LLM_BATCH_SIZE,
    output_root: Optional[Path] = None,
) -> Path:
    """Write batch markdown files + manifest.json. Returns the batch dir.

    Each batch file is self-contained: prompt + schema + N posts. The
    manifest records prompt_version, schema_fingerprint, per-batch sha256
    of the input file, and per-batch status (pending|imported)."""
    if not posts:
        raise ValueError("export_batches called with empty post list")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = Path(output_root) if output_root else Path(LLM_BATCH_DIR)
    batch_dir = root / ts
    batch_dir.mkdir(parents=True, exist_ok=True)

    fingerprint = schema_fingerprint()
    batches_meta = []

    for batch_idx, start in enumerate(range(0, len(posts), batch_size), start=1):
        chunk = posts[start:start + batch_size]
        batch_path = batch_dir / f"batch_{batch_idx:03d}.md"
        content = _render_batch(chunk, fingerprint, batch_idx)
        batch_path.write_text(content, encoding="utf-8")
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        batches_meta.append({
            "batch_id": batch_idx,
            "file": batch_path.name,
            "sha256": sha,
            "post_count": len(chunk),
            "post_ids": [p["id"] for p in chunk],
            "status": "pending",
        })

    prefilter_breakdown: dict[str, int] = {}
    for p in posts:
        src = p.get("_prefilter", "no_filter")
        prefilter_breakdown[src] = prefilter_breakdown.get(src, 0) + 1

    manifest = {
        "prompt_version": LLM_PROMPT_VERSION,
        "schema_fingerprint": fingerprint,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_posts": len(posts),
        "prefilter_breakdown": prefilter_breakdown,
        "batches": batches_meta,
    }
    (batch_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return batch_dir


def _render_batch(posts: list[dict], fingerprint: str, batch_idx: int) -> str:
    header = PROMPT_HEADER.format(
        schema=_render_schema_for_prompt(),
        fingerprint=fingerprint,
        version=LLM_PROMPT_VERSION,
    )
    lines = [
        header,
        f"Batch {batch_idx} — {len(posts)} posts.",
        "",
        f"Write the facets JSON to `batch_{batch_idx:03d}_facets.json` "
        f"in this same directory.",
        "",
        "---",
        "",
    ]
    for p in posts:
        lines.append(f"## Post {p['id']} (r/{p['subreddit']})")
        lines.append("")
        lines.append(f"prefilter: `{p.get('_prefilter', 'no_filter')}`")
        lines.append("")
        lines.append(f"**Title:** {p.get('title') or '(no title)'}")
        body = (p.get("body") or "").strip()
        if body:
            lines.append("")
            lines.append(body)
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


# --- Batch import ----------------------------------------------------------

def import_facets(batch_dir: Path, db: Database) -> dict:
    """Validate manifest + per-batch hashes, UPSERT facets, mark batches
    imported in place. Returns {imported, errors, warnings}."""
    batch_dir = Path(batch_dir)
    manifest_path = batch_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest at {manifest_path}")
    manifest = json.loads(manifest_path.read_text())

    file_version = manifest.get("prompt_version")
    file_fingerprint = manifest.get("schema_fingerprint")
    current_fingerprint = schema_fingerprint()

    if file_fingerprint != current_fingerprint:
        raise ValueError(
            f"Schema fingerprint mismatch: manifest={file_fingerprint!r} "
            f"current={current_fingerprint!r}. Refusing to import — facets "
            "were generated against a different schema."
        )

    warnings: list[str] = []
    if file_version != LLM_PROMPT_VERSION:
        warnings.append(
            f"Manifest prompt_version={file_version!r} differs from current "
            f"{LLM_PROMPT_VERSION!r}. Persisting under the manifest's version."
        )

    imported = 0
    errors: list[str] = []
    for batch_entry in manifest["batches"]:
        batch_file = batch_dir / batch_entry["file"]
        if batch_file.exists():
            actual_sha = hashlib.sha256(batch_file.read_bytes()).hexdigest()
            if actual_sha != batch_entry["sha256"]:
                errors.append(f"sha256 mismatch on {batch_entry['file']}")
                continue
        facets_path = batch_dir / batch_entry["file"].replace(".md", "_facets.json")
        if not facets_path.exists():
            errors.append(f"facets missing: {facets_path.name}")
            continue
        try:
            facets = json.loads(facets_path.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"invalid JSON in {facets_path.name}: {e}")
            continue
        if not isinstance(facets, list):
            errors.append(
                f"{facets_path.name}: expected a JSON array of facets, "
                f"got {type(facets).__name__}"
            )
            continue
        for facet_obj in facets:
            try:
                row = _validate_and_normalize(facet_obj, file_version)
                row["mode"] = "batch"
                row.setdefault("prefilter_source", None)
                row.setdefault("model", "claude-via-batch-session")
                row.setdefault("input_tokens", None)
                row.setdefault("output_tokens", None)
                row.setdefault("raw_response", json.dumps(facet_obj))
                db.upsert_pain_facet(row)
                imported += 1
            except (ValueError, KeyError) as e:
                errors.append(
                    f"invalid facet {facet_obj.get('post_id', '?')}: {e}"
                )
        batch_entry["status"] = "imported"

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"imported": imported, "errors": errors, "warnings": warnings}


def _validate_and_normalize(facet: dict, prompt_version: str) -> dict:
    """Validate one facet object and shape it into a pain_facets row dict.
    Raises ValueError on missing required fields or invalid enums. JSON-
    encodes array fields for SQLite text storage. Unknown domain values
    are normalized to 'other' rather than rejected."""
    if "post_id" not in facet:
        raise ValueError("missing post_id")
    if "is_pain_point" not in facet:
        raise ValueError("missing is_pain_point")
    wtp = facet.get("willingness_to_pay")
    if wtp and wtp not in _VALID_WTP:
        raise ValueError(f"invalid willingness_to_pay: {wtp!r}")
    urg = facet.get("urgency")
    if urg and urg not in _VALID_URGENCY:
        raise ValueError(f"invalid urgency: {urg!r}")
    dom = facet.get("domain")
    if dom and dom not in _VALID_DOMAINS:
        dom = "other"
    return {
        "post_id": int(facet["post_id"]),
        "prompt_version": prompt_version,
        "is_pain_point": 1 if facet["is_pain_point"] else 0,
        "pain_summary": facet.get("pain_summary"),
        "domain": dom,
        "current_solution": facet.get("current_solution"),
        "integrations_mentioned": json.dumps(facet.get("integrations_mentioned") or []),
        "dollar_anchors": json.dumps(facet.get("dollar_anchors") or []),
        "max_dollar_anchor": facet.get("max_dollar_anchor"),
        "willingness_to_pay": wtp,
        "urgency": urg,
        "buyer_role": facet.get("buyer_role"),
        "market_size_signal": facet.get("market_size_signal"),
        "confidence": facet.get("confidence"),
    }
