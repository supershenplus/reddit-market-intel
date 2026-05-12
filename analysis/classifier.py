"""Regex + heuristic classifier for pain-point detection."""

import json

from analysis.keywords import PAIN_POINT_PATTERNS, INTENT_PRIORITY


class PainPointClassifier:
    """Classifies posts by matching against pain-point regex patterns."""

    def classify(self, title: str, body: str) -> dict | None:
        """Classify a post's text against pain-point patterns.

        Returns dict with matched_patterns and intent_category, or None if no match.
        """
        text = f"{title} {body}".strip()
        if not text:
            return None

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

        # Pick the highest-priority category as the primary intent
        primary_category = max(categories_found, key=categories_found.get)

        # Sentiment intensity: more patterns matched = more intense signal
        # Normalize by total possible patterns (25)
        sentiment_intensity = min(1.0, len(matches) / 5.0)

        return {
            "matched_patterns": json.dumps(matches),
            "intent_category": primary_category,
            "sentiment_intensity": sentiment_intensity,
        }
