"""Pain-point classifier: RAG primary, regex fallback."""

import json

from analysis.keywords import PAIN_POINT_PATTERNS, INTENT_PRIORITY


class PainPointClassifier:
    """Classifies posts using RAG (semantic) with regex as fallback."""

    def __init__(self):
        self._rag = None

    def _get_rag(self):
        if self._rag is None:
            try:
                from analysis.rag_classifier import RAGClassifier
                self._rag = RAGClassifier()
            except ImportError:
                self._rag = False  # sentence-transformers not installed
        return self._rag if self._rag is not False else None

    def classify(self, title: str, body: str) -> dict | None:
        """Classify post. RAG primary, regex fallback if RAG unavailable."""
        text = f"{title} {body}".strip()
        if not text:
            return None

        rag = self._get_rag()
        if rag is not None:
            result = rag.classify(title, body)
            if result is not None:
                return result
            # RAG found nothing — also try regex to catch explicit phrasing
            return self._regex_classify(text)

        return self._regex_classify(text)

    def _regex_classify(self, text: str) -> dict | None:
        matches = []
        categories_found = {}

        for pattern, category in PAIN_POINT_PATTERNS:
            if pattern.search(text):
                matches.append(category)
                priority = INTENT_PRIORITY.get(category, 0)
                if category not in categories_found or priority > categories_found[category]:
                    categories_found[category] = priority

        if not matches:
            return None

        primary_category = max(categories_found, key=categories_found.get)
        sentiment_intensity = min(1.0, len(matches) / 5.0)

        return {
            "matched_patterns": json.dumps(matches),
            "intent_category": primary_category,
            "sentiment_intensity": sentiment_intensity,
        }
