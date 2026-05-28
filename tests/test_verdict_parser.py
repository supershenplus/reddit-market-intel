"""Tests for analysis/verdict_parser.py — tolerant digest parser."""

import pytest

from analysis.verdict_parser import (
    EXPECTED_DIGEST_FORMAT,
    FormatMismatch,
    parse_digest,
)


def _digest(niche_blocks: str, format_tag: str = "v3") -> str:
    return (
        f"<!-- digest_format: {format_tag} -->\n"
        "# Week of 2026-05-25 — Top Niches\n\n"
        + niche_blocks
    )


# --- format gating ---------------------------------------------------------

class TestFormatGate:
    def test_missing_header_raises(self):
        with pytest.raises(FormatMismatch, match="No digest_format"):
            parse_digest("## 1. some niche — score 0.4\n- [x] build\n- fingerprint: abc\n")

    def test_v1_raises(self):
        with pytest.raises(FormatMismatch, match="v1"):
            parse_digest(_digest("", format_tag="v1"))

    def test_v2_raises(self):
        with pytest.raises(FormatMismatch, match="v2"):
            parse_digest(_digest("", format_tag="v2"))

    def test_v3_passes(self):
        result = parse_digest(_digest(""))
        assert result == []


# --- checkbox shape tolerance ----------------------------------------------

class TestCheckboxTolerance:
    @pytest.mark.parametrize("box_form", [
        "- [x] build  [ ] watch  [ ] kill",
        "- [X] build  [ ] watch  [ ] kill",
        "[x] build  [ ] watch  [ ] kill",
        "* [x] build  [ ] watch  [ ] kill",
        "- [ x ] build  [ ] watch  [ ] kill",
    ])
    def test_accepts_common_editor_variants(self, box_form):
        block = (
            "## 1. niche A — score 0.5\n"
            "- Pain: x\n"
            f"{box_form}   notes: ok\n"
            "- fingerprint: abc123\n"
        )
        result = parse_digest(_digest(block))
        assert len(result) == 1
        assert result[0]["decision"] == "build"

    def test_crlf_line_endings(self):
        block = (
            "## 1. niche A — score 0.5\r\n"
            "- Pain: x\r\n"
            "- [x] build  [ ] watch  [ ] kill   notes: ok\r\n"
            "- fingerprint: abc123\r\n"
        )
        result = parse_digest(_digest(block))
        assert len(result) == 1
        assert result[0]["decision"] == "build"


# --- per-niche validation --------------------------------------------------

class TestPerNicheValidation:
    def test_no_box_checked_skipped_silently(self):
        block = (
            "## 1. niche A — score 0.5\n"
            "- [ ] build  [ ] watch  [ ] kill   notes: ___\n"
            "- fingerprint: abc123\n"
        )
        result = parse_digest(_digest(block))
        assert result == []
        # No warning either — empty rows are the default state
        assert parse_digest.last_warnings == []

    def test_multiple_boxes_checked_warns(self):
        block = (
            "## 1. niche A — score 0.5\n"
            "- [x] build  [x] watch  [ ] kill   notes: confused\n"
            "- fingerprint: abc123\n"
        )
        result = parse_digest(_digest(block))
        assert result == []
        assert any("2 boxes checked" in w for w in parse_digest.last_warnings)

    def test_missing_fingerprint_warns(self):
        block = (
            "## 1. niche A — score 0.5\n"
            "- [x] build  [ ] watch  [ ] kill   notes: ok\n"
        )
        result = parse_digest(_digest(block))
        assert result == []
        assert any("no fingerprint" in w for w in parse_digest.last_warnings)

    def test_template_placeholder_note_normalized(self):
        block = (
            "## 1. niche A — score 0.5\n"
            "- [x] build  [ ] watch  [ ] kill   notes: ___\n"
            "- fingerprint: abc123\n"
        )
        result = parse_digest(_digest(block))
        assert len(result) == 1
        assert result[0]["note"] is None  # `___` is treated as unset

    def test_checkbox_inside_notes_is_ignored(self):
        # CORR-W2 regression: operator-written `[x] build` inside notes used
        # to inflate the checked count and silently skip the niche.
        block = (
            "## 1. niche A — score 0.5\n"
            "- [x] build  [ ] watch  [ ] kill   notes: maybe [x] build later\n"
            "- fingerprint: abc123\n"
        )
        result = parse_digest(_digest(block))
        assert len(result) == 1
        assert result[0]["decision"] == "build"
        assert result[0]["note"] == "maybe [x] build later"
        assert parse_digest.last_warnings == []


# --- multi-niche soft fail -------------------------------------------------

class TestMultiNicheSoftFail:
    def test_one_bad_doesnt_skip_others(self):
        blocks = (
            "## 1. good niche — score 0.5\n"
            "- [x] build  [ ] watch  [ ] kill   notes: this one is fine\n"
            "- fingerprint: aaa111\n\n"
            "## 2. bad niche — score 0.4\n"
            "- [x] build  [x] watch  [ ] kill   notes: too many checks\n"
            "- fingerprint: bbb222\n\n"
            "## 3. another good — score 0.3\n"
            "- [ ] build  [ ] watch  [x] kill   notes: kill it\n"
            "- fingerprint: ccc333\n"
        )
        result = parse_digest(_digest(blocks))
        assert len(result) == 2
        labels = [v["subject_label"] for v in result]
        assert "good niche" in labels
        assert "another good" in labels
        assert "bad niche" not in labels
        # Bad one logged
        assert len(parse_digest.last_warnings) == 1


# --- output shape ----------------------------------------------------------

class TestOutputShape:
    def test_dict_keys_match_insert_verdict_signature(self):
        block = (
            "## 1. some pain — score 0.5\n"
            "- [x] build  [ ] watch  [ ] kill   notes: looks promising\n"
            "- fingerprint: abc123def456\n"
        )
        v = parse_digest(_digest(block))[0]
        # These are the exact keys Database.insert_verdict expects:
        for key in ("subject_type", "subject_label", "subject_fingerprint",
                    "decision", "note"):
            assert key in v
        assert v["subject_type"] == "niche"
        assert v["subject_label"] == "some pain"
        assert v["subject_fingerprint"] == "abc123def456"
        assert v["decision"] == "build"
        assert v["note"] == "looks promising"
