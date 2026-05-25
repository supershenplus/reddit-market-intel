"""Tests for analysis/taste.py — cosine taste-learning boost."""

import numpy as np
import pytest

from analysis import taste
from analysis.taste import compute_taste_boost, hint_when_n_eq_1


def _normed(*components) -> bytes:
    """Build a normalized float32 vector blob."""
    v = np.array(components, dtype=np.float32)
    v = v / np.linalg.norm(v)
    return v.tobytes()


# --- gating ----------------------------------------------------------------

class TestGating:
    def test_zero_builds_no_boost(self):
        m, similar = compute_taste_boost(_normed(1, 0, 0), [])
        assert m == 1.0
        assert similar == []

    def test_one_build_no_boost(self, monkeypatch):
        # Even an identical-direction build doesn't boost at N=1.
        c = _normed(1, 0, 0)
        m, similar = compute_taste_boost(c, [{"label": "X", "centroid": c}])
        assert m == 1.0
        assert similar == []

    def test_two_builds_can_boost(self, monkeypatch):
        c = _normed(1, 0, 0)
        m, similar = compute_taste_boost(
            c, [
                {"label": "X", "centroid": c},
                {"label": "Y", "centroid": c},
            ],
        )
        from config import TASTE_BOOST_MULTIPLIER
        assert m == TASTE_BOOST_MULTIPLIER
        assert similar == ["X", "Y"] or similar == ["Y", "X"]  # tie order

    def test_below_threshold_no_boost(self):
        c1 = _normed(1, 0, 0)
        c2 = _normed(0, 1, 0)  # orthogonal — sim = 0
        c3 = _normed(0, 0, 1)
        m, similar = compute_taste_boost(
            c1, [{"label": "Y", "centroid": c2}, {"label": "Z", "centroid": c3}]
        )
        assert m == 1.0
        assert similar == []


# --- empty / malformed cases ----------------------------------------------

class TestEdgeCases:
    def test_empty_niche_centroid_no_boost(self):
        c = _normed(1, 0, 0)
        m, _ = compute_taste_boost(b"", [
            {"label": "X", "centroid": c},
            {"label": "Y", "centroid": c},
        ])
        assert m == 1.0

    def test_dimension_mismatch_skipped(self):
        c1 = _normed(1, 0, 0)
        c2 = _normed(1, 0, 0, 0)  # 4-dim mismatch
        m, similar = compute_taste_boost(c1, [
            {"label": "X", "centroid": c2},
            {"label": "Y", "centroid": c1},  # this one matches dim
        ])
        # With N=2 and one dim-matched identical, the matched one should
        # still drive a boost — but the build_centroids list is N=2 so we
        # gate passes. Sim of c1 to c1 = 1.0, sim of c1 to c2 = skipped.
        assert m > 1.0
        assert similar == ["Y"]

    def test_none_centroid_in_build_list_skipped(self):
        c = _normed(1, 0, 0)
        m, similar = compute_taste_boost(c, [
            {"label": "X", "centroid": None},
            {"label": "Y", "centroid": c},
            {"label": "Z", "centroid": c},
        ])
        # 2 valid builds remain, identical → boost activates
        assert m > 1.0
        assert "Y" in similar and "Z" in similar


# --- threshold respect -----------------------------------------------------

class TestThreshold:
    def test_just_above_threshold_boosts(self, monkeypatch):
        # Force threshold to 0.5 for this test
        monkeypatch.setattr(taste, "TASTE_SIM_THRESHOLD", 0.5)
        c1 = _normed(1, 0, 0)
        # Build centroid with sim=0.6 to c1
        c_partial = _normed(0.6, 0.8, 0)
        m, similar = compute_taste_boost(c1, [
            {"label": "X", "centroid": c_partial},
            {"label": "Y", "centroid": c1},
        ])
        assert m > 1.0
        assert similar  # at least one match

    def test_just_below_threshold_no_boost(self, monkeypatch):
        monkeypatch.setattr(taste, "TASTE_SIM_THRESHOLD", 0.99)
        c1 = _normed(1, 0, 0)
        c_close = _normed(0.95, 0.31, 0)  # sim ~0.95, below 0.99
        m, similar = compute_taste_boost(c1, [
            {"label": "X", "centroid": c_close},
            {"label": "Y", "centroid": c_close},
        ])
        assert m == 1.0
        assert similar == []


# --- hint helper -----------------------------------------------------------

class TestHint:
    def test_n_zero_no_hint(self):
        assert hint_when_n_eq_1([]) is None

    def test_n_one_returns_hint(self):
        c = _normed(1, 0, 0)
        h = hint_when_n_eq_1([{"label": "X", "centroid": c}])
        assert h is not None
        assert "one more" in h or "1/" in h

    def test_n_two_no_hint(self):
        c = _normed(1, 0, 0)
        assert hint_when_n_eq_1([
            {"label": "X", "centroid": c}, {"label": "Y", "centroid": c}
        ]) is None
