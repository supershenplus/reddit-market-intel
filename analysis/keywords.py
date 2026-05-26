"""Pain-point keyword patterns and comment validation patterns."""

import re

# Each tuple: (compiled_regex, intent_category)
PAIN_POINT_PATTERNS = [
    # Direct tool-seeking
    (re.compile(r"is there (?:an? )?(?:app|tool|software|service|platform) (?:that|for|which)", re.IGNORECASE), "seeking_tool"),
    (re.compile(r"(?:looking|searching) for (?:a |an )?(?:tool|app|solution|alternative)", re.IGNORECASE), "seeking_tool"),
    (re.compile(r"(?:any(?:one|body)? )?(?:know|recommend) (?:a |an )?(?:good )?\w+ (?:tool|app|service)", re.IGNORECASE), "seeking_tool"),
    (re.compile(r"what do you (?:all |guys )?use (?:for|to)\b", re.IGNORECASE), "seeking_tool"),
    (re.compile(r"(?:best|good) (?:alternative|replacement) (?:to|for)\b", re.IGNORECASE), "seeking_tool"),

    # Willingness to pay
    (re.compile(r"i(?:'d| would) (?:gladly |happily )?pay (?:for|good money)", re.IGNORECASE), "would_pay"),
    (re.compile(r"shut up and take my money", re.IGNORECASE), "would_pay"),
    (re.compile(r"(?:willing|ready) to pay (?:for|if)", re.IGNORECASE), "would_pay"),
    (re.compile(r"worth paying for", re.IGNORECASE), "would_pay"),

    # Frustration with existing tools
    (re.compile(r"(?:current|existing) (?:options?|tools?|solutions?) (?:suck|are terrible|are awful|are garbage)", re.IGNORECASE), "frustrated"),
    (re.compile(r"(?:so |really )?frustrat(?:ed|ing)\b.*(?:tool|app|software|workflow)", re.IGNORECASE), "frustrated"),
    (re.compile(r"(?:why is|why are) (?:there no|it so hard to find)\b", re.IGNORECASE), "frustrated"),
    (re.compile(r"(?:hate|can't stand) (?:using |how )\b", re.IGNORECASE), "frustrated"),
    (re.compile(r"(?:nothing|no tool|no app) (?:that |which )?(?:does|works|handles)\b", re.IGNORECASE), "frustrated"),
    (re.compile(r"(?:broken|buggy|unusable|clunky|bloated)\b.*(?:app|tool|software|ui|interface)", re.IGNORECASE), "frustrated"),

    # Feature requests / gaps
    (re.compile(r"(?:wish|if only) (?:there was|someone would|i could)\b", re.IGNORECASE), "feature_request"),
    (re.compile(r"(?:someone )?(?:should|needs to) (?:build|make|create)\b", re.IGNORECASE), "feature_request"),
    (re.compile(r"(?:doesn't|does not|won't|can't) (?:even )?(?:support|handle|do|work with)\b", re.IGNORECASE), "feature_request"),
    (re.compile(r"(?:missing|lacks?|no support for)\b.*(?:feature|integration|option)", re.IGNORECASE), "feature_request"),
    (re.compile(r"(?:why (?:hasn't|hasn't|doesn't) (?:anyone|someone))\b.*(?:built|made|created)", re.IGNORECASE), "feature_request"),

    # Unbundling signals
    (re.compile(r"(?:too (?:expensive|complex|bloated|heavy)) for (?:just|only)\b", re.IGNORECASE), "unbundle"),
    (re.compile(r"(?:overkill|overpowered) for (?:what i|my)\b", re.IGNORECASE), "unbundle"),
    (re.compile(r"(?:just need|only need|all i need)\b.*(?:simple|basic|lightweight)", re.IGNORECASE), "unbundle"),
    (re.compile(r"paying for .* (?:but only use|when i only need)", re.IGNORECASE), "unbundle"),
    (re.compile(r"i don't need .* (?:just|only) (?:want|need)", re.IGNORECASE), "unbundle"),
]

# Intent category priority (higher = stronger signal)
INTENT_PRIORITY = {
    "would_pay": 5,
    "unbundle": 4,
    "seeking_tool": 3,
    "frustrated": 2,
    "feature_request": 1,
    # Noise categories sit at 0 so the priority-margin tiebreak in
    # rag_classifier.classify() always prefers a real pain category when
    # both fire on the same post. A noise-only match short-circuits to
    # None at the end of classify() — see NOISE_CATEGORIES below.
    "noise_career": 0,
    "noise_support": 0,
    "noise_observer": 0,
}

# Categories that mean "this post is on-topic for RAG seeds but is not a
# pain-point opportunity." Used by RAGClassifier.classify() to early-return
# None when the winning category is one of these. Keeps the LLM prefilter
# from burning batch slots on career posts, tenant/landlord legal Qs, and
# agency-observer manifestos that LLM veto would catch anyway.
NOISE_CATEGORIES = frozenset({"noise_career", "noise_support", "noise_observer"})
