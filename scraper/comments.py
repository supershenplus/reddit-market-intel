"""Comment thread analysis — classify comments for validation signals."""

import re

from scraper.base import RedditComment

# Patterns to classify comment intent
ME_TOO_PATTERNS = [
    re.compile(r"\b(?:same here|me too|i need this|this \^|seconded|\+1|same problem)\b", re.IGNORECASE),
    re.compile(r"\b(?:following|bumping?|upvot(?:ed|ing) for visibility)\b", re.IGNORECASE),
    re.compile(r"\b(?:i('d| would) (?:also |definitely )?(?:love|want|need|use) this)\b", re.IGNORECASE),
]

LINKS_PRODUCT_PATTERNS = [
    re.compile(r"\b(?:i (?:use|tried|switched to|recommend)|check out|have you tried|look at)\s+\w+", re.IGNORECASE),
    re.compile(r"https?://\S+", re.IGNORECASE),  # any URL = likely product link
]

PRODUCT_NEGATIVE_PATTERNS = [
    re.compile(
        r"\b(?:i (?:use|tried|used))\s+\w+.*\b(?:but|however|except|unfortunately|sucks?|hate|terrible|awful|expensive|buggy|slow)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:switched (?:away )?from|stopped using|cancelled|ditched)\b", re.IGNORECASE),
]


def classify_comment(comment: RedditComment) -> dict:
    """Classify a comment's validation signals.

    Returns dict with is_me_too, links_product, product_negative flags.
    """
    body = comment.body
    flags = {
        "is_me_too": 0,
        "links_product": 0,
        "product_negative": 0,
    }

    for pattern in ME_TOO_PATTERNS:
        if pattern.search(body):
            flags["is_me_too"] = 1
            break

    for pattern in LINKS_PRODUCT_PATTERNS:
        if pattern.search(body):
            flags["links_product"] = 1
            break

    for pattern in PRODUCT_NEGATIVE_PATTERNS:
        if pattern.search(body):
            flags["product_negative"] = 1
            break

    return flags


def analyze_comment_thread(comments: list[RedditComment]) -> dict:
    """Analyze a full comment thread for validation signals.

    Returns aggregate metrics for the post's comment thread.
    """
    total = len(comments)
    me_too_count = 0
    product_links = 0
    product_negatives = 0
    has_positive_answer = False

    classified = []
    for comment in comments:
        flags = classify_comment(comment)
        classified.append((comment, flags))

        if flags["is_me_too"]:
            me_too_count += 1
        if flags["links_product"]:
            product_links += 1
            # If links a product but NOT negative, it's a valid answer
            if not flags["product_negative"] and comment.score > 2:
                has_positive_answer = True
        if flags["product_negative"]:
            product_negatives += 1

    return {
        "total_comments": total,
        "me_too_count": me_too_count,
        "product_links": product_links,
        "product_negatives": product_negatives,
        "has_positive_answer": has_positive_answer,
        "is_unanswered": product_links == 0 and total > 0,
        "classified_comments": classified,
    }
