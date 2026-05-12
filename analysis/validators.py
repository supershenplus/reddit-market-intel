"""Comment-based validation scoring for pain points."""

from scraper.comments import analyze_comment_thread
from scraper.base import RedditComment


def compute_validation_score(comments: list[RedditComment]) -> float:
    """Compute validation score from comment thread analysis.

    Scoring logic:
    - Unanswered (no product linked)     : +0.3
    - "Me too" replies                   : +0.1 each (cap 0.3)
    - Product linked + negative follow-up: +0.2
    - Product linked + positive reception: -0.4
    - High comment count + no consensus  : +0.2

    Returns: float clamped to [0.0, 1.0]
    """
    if not comments:
        return 0.3  # No comments = likely unanswered = moderate signal

    analysis = analyze_comment_thread(comments)
    score = 0.0

    # Unanswered: no one linked a working product
    if analysis["is_unanswered"]:
        score += 0.3

    # "Me too" demand validation
    me_too_bonus = min(0.3, analysis["me_too_count"] * 0.1)
    score += me_too_bonus

    # Product linked but with negative sentiment = unbundling opportunity
    if analysis["product_negatives"] > 0:
        score += 0.2

    # Product linked with positive reception = not actually a gap
    if analysis["has_positive_answer"]:
        score -= 0.4

    # High engagement with no clear answer = fragmented market
    if analysis["total_comments"] >= 10 and not analysis["has_positive_answer"]:
        score += 0.2

    return max(0.0, min(1.0, score))
