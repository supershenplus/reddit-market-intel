"""Phase 5 — taste-learning. Boost niches semantically similar to the
operator's past `build` verdicts.

Centroids are stored as L2-normalized float32 BLOBs (see
`analysis/niches.py:71` where `centroid / norm(centroid)`); cosine
similarity collapses to a plain dot product. No model load needed —
this module is pure NumPy.

Gating: requires `TASTE_MIN_BUILD_VERDICTS` distinct build centroids
before activating. With N=1 the operator can pin all future digests
with one click; N=2 demands at least a pattern. When N==1, callers
surface a hint instead of activating the boost.
"""

import numpy as np

from config import (
    TASTE_BOOST_MULTIPLIER,
    TASTE_MIN_BUILD_VERDICTS,
    TASTE_SIM_THRESHOLD,
)


def _blob_to_vec(blob) -> np.ndarray:
    """SQLite BLOB → numpy float32 vector. Returns empty array on None/empty."""
    if not blob:
        return np.array([], dtype=np.float32)
    return np.frombuffer(blob, dtype=np.float32)


def compute_taste_boost(
    niche_centroid_blob,
    build_centroids: list[dict],
) -> tuple[float, list[str]]:
    """Return (multiplier, similar_to_labels).

    - multiplier=1.0 (no boost) when:
        * fewer than TASTE_MIN_BUILD_VERDICTS build centroids exist
        * niche centroid is empty/None
        * no build centroid exceeds TASTE_SIM_THRESHOLD
    - multiplier=TASTE_BOOST_MULTIPLIER when at least one build centroid
      crosses the similarity threshold. similar_to_labels lists the
      qualifying build niches by label (in cosine-desc order).

    build_centroids: list of {label, centroid} dicts from db.get_build_centroids()."""
    if len(build_centroids) < TASTE_MIN_BUILD_VERDICTS:
        return 1.0, []
    niche_vec = _blob_to_vec(niche_centroid_blob)
    if niche_vec.size == 0:
        return 1.0, []

    similars = []  # (sim, label)
    for entry in build_centroids:
        build_vec = _blob_to_vec(entry.get("centroid"))
        if build_vec.size == 0 or build_vec.size != niche_vec.size:
            continue
        # Centroids are L2-normalized at write time, so cosine = dot.
        sim = float(np.dot(niche_vec, build_vec))
        if sim >= TASTE_SIM_THRESHOLD:
            similars.append((sim, entry.get("label", "?")))

    if not similars:
        return 1.0, []
    similars.sort(reverse=True)
    return TASTE_BOOST_MULTIPLIER, [label for _, label in similars]


def hint_when_n_eq_1(build_centroids: list[dict]) -> str | None:
    """Returns the operator hint string when the build-verdict count is
    exactly 1, else None. Surfaced in the digest header."""
    if len(build_centroids) == 1:
        return (
            "Mark one more niche as `build` to enable taste-learning "
            "(currently 1/" + str(TASTE_MIN_BUILD_VERDICTS) + " verdicts)."
        )
    return None
