"""SEO phrase export for the Lienclear research profile.

Extracts bigram/trigram noun-phrase candidates from posts that hit the
Lienclear domain signal (relevance >= min_relevance). Frequencies + average
relevance of containing posts drive the rank — feeds the 50-state
landing-page playbook in the Lienclear repo BusinessPlan §5.2.

Output: CSV with `phrase,frequency,avg_relevance,sample_post_title,sample_url`.
"""

import csv
import io
from collections import defaultdict
from math import ceil

from sklearn.feature_extraction.text import CountVectorizer

from storage.db import Database
from analysis.market_signals import compute_lienclear_relevance


class SEOPhraseReport:
    """Generate a CSV of SEO phrase candidates ranked by frequency × relevance."""

    def __init__(
        self,
        db: Database,
        min_relevance: float = 0.30,
        top_n: int = 100,
        ngram_range: tuple[int, int] = (2, 3),
        max_df: float | None = None,
    ):
        self.db = db
        self.min_relevance = min_relevance
        self.top_n = top_n
        self.ngram_range = ngram_range
        # None = adaptive: keep all phrases on small focused corpora (those are
        # the most domain-central phrases); only filter near-ubiquitous noise on
        # larger ones. Explicit value overrides.
        self.max_df = max_df

    def generate(self) -> str:
        rows = self._build_rows()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["phrase", "frequency", "avg_relevance", "sample_post_title", "sample_url"])
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()

    # --- internals -------------------------------------------------------------

    def _collect_domain_hit_docs(self) -> list[dict]:
        """Return posts whose lienclear relevance clears the threshold."""
        cur = self.db.conn.execute(
            "SELECT reddit_id, title, body, subreddit, url, score FROM posts"
        )
        docs = []
        for row in cur.fetchall():
            lc = compute_lienclear_relevance(
                row["title"] or "", row["body"] or "", row["subreddit"] or ""
            )
            if lc["domain_hit"] and lc["score"] >= self.min_relevance:
                docs.append({
                    "text": f"{row['title'] or ''} {row['body'] or ''}".strip(),
                    "title": row["title"] or "(no title)",
                    "url": row["url"] or "",
                    "relevance": lc["score"],
                })
        return docs

    def _build_rows(self) -> list[list]:
        docs = self._collect_domain_hit_docs()
        if not docs:
            return []
        texts = [d["text"] for d in docs]

        # Adaptive min_df: with very few domain-hit docs, drop to 1 so we still
        # surface phrases. With more docs, require >=2 to filter one-off noise.
        min_df = 1 if len(docs) < 4 else max(2, ceil(0.05 * len(docs)))
        # Adaptive max_df: small focused corpora — keep all phrases (no upper
        # filter); larger corpora — drop near-ubiquitous filler.
        max_df = self.max_df if self.max_df is not None else (1.0 if len(docs) < 20 else 0.9)

        try:
            vec = CountVectorizer(
                ngram_range=self.ngram_range,
                min_df=min_df,
                max_df=max_df,
                stop_words="english",
                lowercase=True,
            )
            matrix = vec.fit_transform(texts)
        except ValueError:
            # max_df < min_df after pruning, or no vocabulary survived
            return []

        vocab = vec.get_feature_names_out()
        if len(vocab) == 0:
            return []

        # Per-phrase: total frequency, list of relevances + doc-indices it hit
        freq = matrix.sum(axis=0).A1  # 1-D array of totals
        # For avg_relevance + sample we need doc-level membership
        doc_relevances = [d["relevance"] for d in docs]
        rel_sums = defaultdict(float)
        rel_counts = defaultdict(int)
        sample_doc_idx: dict[int, int] = {}
        coo = matrix.tocoo()
        for doc_i, phrase_i, cnt in zip(coo.row, coo.col, coo.data):
            rel_sums[phrase_i] += doc_relevances[doc_i]
            rel_counts[phrase_i] += 1
            # Pick the highest-relevance doc containing this phrase as the sample
            current_sample = sample_doc_idx.get(phrase_i)
            if current_sample is None or doc_relevances[doc_i] > doc_relevances[current_sample]:
                sample_doc_idx[phrase_i] = doc_i

        # Tuple form (score, idx, row) — idx is a tiebreaker so tuple sort
        # never falls through to comparing row payloads (lists/strings).
        ranked = []
        for phrase_i, phrase in enumerate(vocab):
            avg_rel = rel_sums[phrase_i] / rel_counts[phrase_i] if rel_counts[phrase_i] else 0.0
            score = freq[phrase_i] * avg_rel
            sample = docs[sample_doc_idx[phrase_i]]
            row = [phrase, int(freq[phrase_i]), round(avg_rel, 4),
                   sample["title"][:120], sample["url"]]
            ranked.append((score, phrase_i, row))
        ranked.sort(reverse=True)
        return [t[2] for t in ranked[: self.top_n]]
