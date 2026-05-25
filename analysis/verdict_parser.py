"""Phase 5 — parse operator-edited digest markdown back into verdict rows.

Tolerant of common editor reformats: `[ ]` vs `[]`, `- [ ]` vs `* [ ]` vs
just `[ ]`, `[x]` vs `[X]`, trailing whitespace, CRLF vs LF, arbitrary
notes content. Fails soft per niche — a malformed niche block logs a
warning and the rest of the file still parses.

Refuses non-v3 digest files explicitly (silent zero-verdict parse on a
pre-checkbox file would look 'successful' but record nothing).

Expected per-niche shape in the digest markdown:

    ## 3. <label> — score 0.42 (...)
    - Pain: ...
    - Evidence: ...
    ...
    - [ ] build  [ ] watch  [ ] kill   notes: <free text>
    - fingerprint: <stable_key>

Returns list of {subject_label, subject_fingerprint, decision, note} dicts
for each niche where exactly one box is checked. Niches with zero or
multiple checks are skipped with a warning.
"""

import re
from typing import Optional


EXPECTED_DIGEST_FORMAT = "v3"


# Header to detect format compatibility.
_FORMAT_RE = re.compile(r"<!--\s*digest_format:\s*([v0-9.]+)\s*-->", re.IGNORECASE)

# Niche heading (## N. label — ...). Capture the label text.
_NICHE_HEADING_RE = re.compile(r"^##\s+\d+\.\s+(.+?)\s+—", re.MULTILINE)

# Fingerprint line we emit (- fingerprint: <16-hex>). Accept alphanumeric +
# underscore to allow non-hex test fixtures alongside real sha1[:16] values.
_FINGERPRINT_RE = re.compile(r"^[-*]?\s*fingerprint:\s*([a-zA-Z0-9_]+)\s*$", re.MULTILINE)

# Checkbox forms: capture word after the box.
# Matches: [ ] build, [] build, - [ ] build, * [x] build, [X] BUILD, etc.
_CHECKBOX_RE = re.compile(
    r"\[\s*([xX]?)\s*\]\s*(build|watch|kill)",
    re.IGNORECASE,
)

# Optional inline notes after the checkbox row: "notes: <text>"
_NOTES_RE = re.compile(r"notes?:\s*(.*?)(?:\n|$)", re.IGNORECASE)


class FormatMismatch(Exception):
    """Raised when the digest file doesn't carry the expected digest_format."""


def parse_digest(content: str) -> list[dict]:
    """Parse a v3 digest file. Returns list of verdict dicts (one per niche
    with exactly one checkbox checked). Raises FormatMismatch on v1/v2 or
    missing format header."""
    fmt_match = _FORMAT_RE.search(content)
    if not fmt_match:
        raise FormatMismatch(
            "No digest_format header found. Re-generate the digest "
            "via `python main.py digest` (current format is "
            f"{EXPECTED_DIGEST_FORMAT})."
        )
    if fmt_match.group(1).lower() != EXPECTED_DIGEST_FORMAT:
        raise FormatMismatch(
            f"Digest format is {fmt_match.group(1)!r}, expected "
            f"{EXPECTED_DIGEST_FORMAT!r}. Re-generate the digest."
        )

    # Normalize CRLF → LF up front so all downstream regex is line-uniform.
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Split on niche headings and parse each block.
    blocks = _split_niche_blocks(content)
    verdicts = []
    warnings = []
    for label, body in blocks:
        result = _parse_niche_block(label, body)
        if isinstance(result, dict):
            verdicts.append(result)
        elif result is not None:
            warnings.append(result)
    # Warnings are surfaced via the second return; callers can log them.
    parse_digest.last_warnings = warnings
    return verdicts


def _split_niche_blocks(content: str) -> list[tuple[str, str]]:
    """Yields (label, block_text) for each niche heading found. Block text
    runs from the heading to the next `## N.` heading (or EOF)."""
    matches = list(_NICHE_HEADING_RE.finditer(content))
    blocks = []
    for i, m in enumerate(matches):
        label = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        blocks.append((label, content[start:end]))
    return blocks


def _parse_niche_block(label: str, body: str) -> Optional[dict] | str:
    """Returns dict on success, warning-string when skipped, None on no
    checkbox activity (treated as 'operator left this one unmarked')."""
    fp_match = _FINGERPRINT_RE.search(body)
    fingerprint = fp_match.group(1).strip() if fp_match else None

    # All checkbox matches in the body. There may be 3 (the three options),
    # we want the ones marked with x/X.
    boxes = _CHECKBOX_RE.findall(body)
    if not boxes:
        return None  # silent — no checkbox row at all (operator didn't fill)
    checked = [decision.lower() for mark, decision in boxes if mark]
    if not checked:
        return None  # unmarked block — operator skipped
    if len(checked) > 1:
        return (
            f"niche {label!r}: {len(checked)} boxes checked "
            f"({', '.join(checked)}). Skipped — check exactly one."
        )
    decision = checked[0]
    if not fingerprint:
        return (
            f"niche {label!r}: marked {decision} but no fingerprint line "
            "found. Skipped — re-generate the digest to include fingerprints."
        )

    notes_match = _NOTES_RE.search(body)
    note = notes_match.group(1).strip() if notes_match else None
    if note in ("", "___", "_____"):  # template placeholder
        note = None

    return {
        "subject_type": "niche",
        "subject_label": label,
        "subject_fingerprint": fingerprint,
        "decision": decision,
        "note": note,
    }
