"""Configuration for Reddit Market Intelligence Pipeline."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "market_intel.db"

# Reddit API credentials (PRAW) — set via environment or leave empty for JSON fallback
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "MarketIntel/1.0")

# RAG classifier
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_PATH = str(DATA_DIR / "chroma")
SIMILARITY_THRESHOLD = 0.35   # cosine similarity floor; tune after benchmarking

# Rate limiting
JSON_API_DELAY = 1.0          # seconds between JSON API requests
JSON_API_JITTER = (0.5, 1.5)  # random jitter range (seconds)
MAX_RETRIES = 5
BACKOFF_BASE = 2              # exponential backoff base (seconds)

# Scraping defaults
DEFAULT_LIMIT = 100
DEFAULT_SORT = "hot"          # hot, new, top
COMMENT_DEPTH = 3             # max depth of comment tree to parse

# Seed subreddits by vertical (Phase 2 discovery-engine pivot — 12-vertical
# taxonomy, ~100 unique subs). Categories are non-disjoint: scrape-all dedupes
# by sub name, first-category-wins on metadata. Add/remove freely — Reddit
# returns 404 for unknown subs and the scraper logs + skips.
SEED_SUBREDDITS = {
    "b2b_saas": [
        "smallbusiness", "Entrepreneur", "SaaS", "startups", "indiehackers",
        "microsaas", "AskEntrepreneur", "SideProject", "EntrepreneurRideAlong",
    ],
    "vertical_saas": [
        "legaltech", "lawfirm", "Accounting", "taxpros",
        "Dentistry", "MedicalAssistant", "Veterinary", "Optometry",
    ],
    "dev_tools": [
        "webdev", "devops", "programming", "ExperiencedDevs",
        "learnprogramming", "node", "Python", "golang", "rust",
        "kubernetes", "docker", "sysadmin",
    ],
    "marketing": [
        "marketing", "SEO", "PPC", "content_marketing", "EmailMarketing",
        "socialmedia", "GrowmyBusiness", "bigseo",
    ],
    "freelance": [
        "freelance", "DigitalNomad", "WorkOnline", "forhire",
        "freelanceWriters", "graphic_design", "Upwork",
    ],
    "ecommerce": [
        "ecommerce", "shopify", "FulfillmentByAmazon", "AmazonSeller",
        "EtsySellers", "dropship", "woocommerce",
    ],
    "property": [
        "realestate", "RealEstateInvesting", "Landlord", "PropertyManagement",
        "AirBnB", "Mortgages",
    ],
    "construction": [
        "Construction", "Contractor", "ConstructionManagers",
        "Electricians", "HVAC", "Plumbing", "Roofing", "Concrete",
        "Carpentry", "Painting", "Flooring", "Welding", "Estimators",
    ],
    "services": [
        "AutoDetailing", "AutoRepair", "Salon", "tattoo",
        "lawncare", "landscaping", "CleaningCompany",
        "petgrooming", "personaltrainer",
    ],
    "automation": [
        "nocode", "Automate", "n8n", "zapier", "MakeAutomation",
        "RPA", "lowcode",
    ],
    "operations": [
        "projectmanagement", "OperationsManagement", "businessanalysis",
        "supplychain", "logistics", "ITManagement", "Bookkeeping",
    ],
    "leadership": [
        "managers", "Leadership", "AskManagers",
        "middlemanagement", "EngineeringManagers", "humanresources",
    ],
    "gaming": [
        "forza", "ForzaHorizon", "forzahorizon6", "forzahorizon5",
        "ForzaMotorsport", "forzahorizon4", "simracing",
    ],
    # 2026-05-31 green-field re-aim: poster=buyer, under-tooled, verbal signal,
    # money present. Deliberately OUTSIDE the saturated B2B-SMB-tools cluster
    # that produced 3 straight saturation/buyer-side kills (Niche #1, lienclear).
    # Unknown sub names 404-skip in the scraper, so over-inclusion is safe.
    "regulated_solo": [
        "Notary", "homeinspection", "Homeinspections", "appraisal",
        "RealEstateAppraisal", "freightbrokers", "CourtReporting",
        "ClaimsAdjuster", "privateinvestigator", "privateinvestigation",
        "processservers",
    ],
    "physical_operators": [
        "foodtrucks", "selfstorage", "vending", "VendingMachines",
        "Laundromats", "laundromat", "weddingphotography", "Catering",
        "eventplanning",
    ],
    # 2026-05-31 focused probe: the two under-tooled (1-competitor) green-field
    # candidates from the first gate pass. Deep-scraped to test whether would_pay
    # evidence materializes with volume or stays absent (see
    # [[feedback-greenfield-wtp-absent]]). Transient — fold into the verdict.
    "probe_inspect_claims": [
        "homeinspection", "Homeinspections", "ClaimsAdjuster",
    ],
}

# Scoring weights (must sum to 1.0)
SCORING_WEIGHTS = {
    "reddit_score": 0.15,
    "sentiment_intensity": 0.15,
    "validation_score": 0.15,
    "cross_sub_multiplier": 0.10,
    "intent_weight": 0.10,
    "recency_weight": 0.05,
    "monetization_score": 0.15,
    "solution_simplicity": 0.10,
    "market_size_score": 0.05,
}

# Market signal keywords
MONETIZATION_HIGH_KEYWORDS = [
    r"\bwould pay\b", r"\bwilling to pay\b", r"\bpay for\b", r"\bworth paying\b",
    r"\b\$\d+\s*(?:/mo|/month|per month|/year)\b", r"\bROI\b", r"\bB2B\b",
    r"\benterprise\b", r"\bsave.*time.*money\b", r"\bcharge clients\b",
    r"\bbusiness expense\b", r"\bbudget for\b",
]
MONETIZATION_LOW_KEYWORDS = [
    r"\bfree\b", r"\bopen.?source\b", r"\bcan't afford\b", r"\btoo expensive\b",
    r"\bno budget\b", r"\bjust a hobby\b",
]
MONETIZATION_HIGH_SUBREDDITS = {
    "smallbusiness", "Entrepreneur", "SaaS", "startups", "freelance",
    "AskEntrepreneur", "microsaas", "ecommerce",
}
MONETIZATION_LOW_SUBREDDITS = {
    "productivity", "digitalnomad", "nocode", "SideProject",
}

SIMPLICITY_HIGH_KEYWORDS = [
    r"\bstatic site\b", r"\bdirectory\b", r"\baggregator\b", r"\bnewsletter\b",
    r"\bsimple form\b", r"\bjust needs?\b", r"\bone.?page\b", r"\blanding page\b",
    r"\bno.?code\b", r"\bsimple webapp\b", r"\bbasic tool\b",
]
SIMPLICITY_LOW_KEYWORDS = [
    r"\breal.?time\b", r"\bmulti.?tenant\b", r"\benterprise integration\b",
    r"\bAPI sync\b", r"\bmachine learning\b", r"\bcomplex\b", r"\bscalable infra\b",
    r"\bmicroservices\b", r"\breal.?time collaboration\b",
]

MARKET_SIZE_CEILING_SUBSCRIBERS = 10_000_000

INTENT_WEIGHTS = {
    "would_pay": 1.0,
    "seeking_tool": 0.8,
    "unbundle": 0.7,
    "frustrated": 0.6,
    "feature_request": 0.5,
}

# Clustering
CLUSTER_DISTANCE_THRESHOLD = 0.85
TFIDF_MAX_FEATURES = 5000
TRENDING_MULTIPLIER = 2.0     # post count in 30d must exceed this * avg to be "trending"
RECENCY_HALF_LIFE_DAYS = 90

# ---------------------------------------------------------------------------
# Lienclear research profile — construction lien-waiver + AIA pay-app SaaS
# Domain: small specialty-trade subcontractors (5–100 employees, $500K–$10M rev)
# Pricing: $49–199/mo. Beachhead: CA → TX/FL/NY/GA. See plan in
# .claude/plans/sequential-painting-nova.md and supershenplus/startup_docs.
# ---------------------------------------------------------------------------

# Beachhead 5 — weight 1.0. Other 8 statutory-form states — weight 0.6.
LIENCLEAR_BEACHHEAD_STATES = [
    r"\bCalifornia\b", r"\bCA\b",
    r"\bTexas\b", r"\bTX\b",
    r"\bFlorida\b", r"\bFL\b",
    r"\bNew York\b", r"\bNY\b",
    r"\bGeorgia\b", r"\bGA\b",
]
LIENCLEAR_STATUTORY_STATES = [
    r"\bArizona\b", r"\bAZ\b",
    r"\bMassachusetts\b", r"\bMA\b",
    r"\bMichigan\b", r"\bMI\b",
    r"\bMississippi\b", r"\bMS\b",
    r"\bMissouri\b", r"\bMO\b",
    r"\bMontana\b", r"\bMT\b",
    r"\bNevada\b", r"\bNV\b",
    r"\bUtah\b", r"\bUT\b",
]

# Dollar anchors near Lienclear pricing tiers ($49 / $99 / $199 + adjacent)
LIENCLEAR_DOLLAR_ANCHORS = [
    r"\$\s*(?:25|49|50|75|99|100|149|150|199|200)\b",
    r"\$\s*\d+\s*(?:/mo|/month|per month|a month)\b",
]

# ICP role hints — first 3 boost score, last 2 downweight (not the buyer)
LIENCLEAR_ROLE_PATTERNS = {
    "office_manager": [
        r"\boffice manager\b", r"\bproject admin(?:istrator)?\b",
        r"\bAP clerk\b", r"\bAR clerk\b", r"\bbilling clerk\b",
        r"\baccounts payable\b", r"\baccounts receivable\b",
    ],
    "owner_operator": [
        r"\bI own (?:a |the )?(?:small )?(?:construction|electrical|plumbing|HVAC|roofing|concrete) (?:company|business|contractor)\b",
        r"\bmy (?:construction|sub|trade) (?:company|business)\b",
        r"\bas a small (?:sub|subcontractor|contractor)\b",
        r"\bwe run a (?:small )?(?:trade|sub|construction)\b",
    ],
    "bookkeeper": [
        r"\bbookkeeper\b", r"\bconstruction accountant\b",
        r"\bQuickBooks (?:for |construction)\b",
    ],
    "gc": [
        r"\bgeneral contractor\b", r"\bas a GC\b", r"\bwe(?:'re| are) the GC\b",
        r"\bGC requires\b", r"\bour GC\b",
    ],
    "homeowner": [
        r"\bhomeowner\b", r"\bmy house\b", r"\bremodel(?:ing)? my\b",
        r"\bcontractor I hired\b", r"\bDIY (?:home )?(?:reno|remodel)\b",
    ],
}

# Named competitors from BusinessPlan §2.4
LIENCLEAR_COMPETITORS = [
    "Procore", "Levelset", "Textura", "GCPay", "Siteline",
    "Handle.com", "Buildertrend", "CoConstruct",
]

# Domain vocabulary — presence of these is the primary signal that a post is
# even on-topic for Lienclear. Without a hit here, score caps low.
LIENCLEAR_DOMAIN_KEYWORDS = [
    r"\blien waivers?\b", r"\bconditional waivers?\b", r"\bunconditional waivers?\b",
    r"\bAIA\s*G?70[23]\b", r"\bG702\b", r"\bG703\b",
    r"\bschedule of values\b", r"\bSOV\b",
    r"\bpay apps?\b", r"\bpay applications?\b", r"\bpay-?when-?paid\b",
    r"\bretainage\b", r"\bretention\b.{0,80}\b(?:withheld|held|release)\b",
    r"\bpreliminary notices?\b", r"\bnotice to owner\b",
    r"\bmechanic'?s liens?\b", r"\blien rights?\b",
    r"\bprogress (?:billing|payments?)\b",
]

# Phase classification — partitions domain-hit posts into ProductBlueprint
# build phases so the report surfaces "what to build NEXT" not just
# "what's painful". Highest-phase-wins on multi-hit (later phases imply the
# earlier foundation exists, so a post mentioning G702 alongside waivers
# is really a Phase-2 ask). Defaults to Phase 1 when a domain-hit post
# matches no specific phase pattern (Phase 1 = baseline waiver/lien work).
LIENCLEAR_PHASE_PATTERNS = {
    1: [  # free waiver gen + SEO (BusinessPlan §5.1)
        r"\blien waivers?\b", r"\bconditional waivers?\b", r"\bunconditional waivers?\b",
        r"\bpreliminary notices?\b", r"\bnotice to owner\b",
        r"\bmechanic'?s liens?\b", r"\blien rights?\b",
    ],
    2: [  # paid AIA pay-app + dashboard
        r"\bAIA\s*G?70[23]\b", r"\bG702\b", r"\bG703\b",
        r"\bschedule of values\b", r"\bSOV\b",
        r"\bpay apps?\b", r"\bpay applications?\b",
        r"\bprogress (?:billing|payments?)\b",
        r"\bretainage\b", r"\bretention\b.{0,80}\b(?:withheld|held|release)\b",
        r"\bpay-?when-?paid\b",
    ],
    3: [  # notifications + DocuSign + GC portal + integrations
        r"\bDocuSign\b", r"\be[-\s]?sign(?:ature|ing)?\b",
        r"\bGC portal\b", r"\bgeneral contractor portal\b",
        r"\bautomated (?:notification|reminder|workflow|approval)\b",
        r"\bapproval workflow\b",
        r"\bAPI integration\b", r"\bsync with (?:QuickBooks|Procore|Sage)\b",
        r"\bnotification (?:system|email|SMS)\b",
    ],
}

LIENCLEAR_PHASE_LABELS = {
    1: "Phase 1 — Free waiver gen + SEO",
    2: "Phase 2 — Paid AIA pay-app + dashboard",
    3: "Phase 3 — Notifications + DocuSign + GC portal",
}

# DIY-workaround signal — strongest market-validation evidence per the
# lienclear thesis. When someone says "I built a spreadsheet for our pay apps"
# they are explicitly the willing-to-buy ICP: they have the pain, they spent
# time hacking around it, and they would pay to stop hacking. Extracted as
# a facet only (not summed into the relevance score) so the data surfaces
# without perturbing existing scoring behavior — weight tunable later.
# Urgency markers — "this is bleeding NOW" vs "I'd like this someday".
# High-urgency posts disproportionately convert to paying customers.
LIENCLEAR_URGENCY_PATTERNS = [
    r"\b(?:right now|right this minute|ASAP|today|tomorrow)\b",
    r"\b(?:blocking|blocked|holding up|stuck on|killing)\b",
    r"\b(?:losing|lost|leaking|hemorrhaging) (?:money|cash|revenue|sleep|deals?)\b",
    r"\b(?:can't|cannot|won't|wouldn't) (?:pay|get paid|invoice|bill|collect)\b",
    r"\b(?:past due|overdue|late payment|behind on)\b",
    r"\b(?:emergency|crisis|disaster|nightmare)\b",
    r"\bdeadline\b",
    r"\b(?:GC|client|owner) (?:won't|isn't|refuses to) (?:pay|approve|sign|release)\b",
    r"\bcash flow\b",
    r"\b(?:30|60|90) days? (?:late|overdue|out|past)\b",
    r"\bDSO\b",  # days sales outstanding — pure billing-pain jargon
]

# Frequency markers — recurring pain has bigger TAM than one-off
# annoyance. "Every month" beats "this one time" by 12x.
LIENCLEAR_FREQUENCY_PATTERNS = [
    r"\bevery (?:day|week|month|project|job|pay app|invoice|sub|trade)\b",
    r"\b(?:daily|weekly|monthly|quarterly)\b",
    r"\b(?:constantly|continually|always|all the time)\b",
    r"\b(?:over and over|again and again|each time|every time)\b",
    r"\beach (?:month|project|job|pay (?:period|app)|invoice)\b",
    r"\b(?:recurring|ongoing|chronic|perennial)\b",
    r"\bmultiple (?:times|projects|jobs) (?:per|a) (?:day|week|month)\b",
]

LIENCLEAR_DIY_PATTERNS = [
    # Spreadsheet / Excel / Word / Google Sheets workarounds
    r"\b(?:Excel|spreadsheet) (?:template|hack|workflow|workaround|file|sheet)\b",
    r"\bWord (?:doc|template|workaround)\b",
    r"\bGoogle (?:Sheets?|Docs?)\b",
    r"\bin (?:Excel|Sheets?|Word)\b",
    # QuickBooks hacks
    r"\bQuickBooks (?:workaround|hack|template|custom)\b",
    # First-person build / hack patterns
    r"\bI (?:built|made|created|use|hacked|set up|coded|wrote) (?:a|my own|an?|our|the)\s+(?:spreadsheet|template|form|system|tool|macro|script|workflow|process)\b",
    r"\bwe (?:built|made|created|use|hacked|set up|coded|wrote) (?:a|our|the)\s+(?:spreadsheet|template|form|system|tool|macro|script|workflow|process)\b",
    # Generic automation / glue tools used as a Lienclear gap-filler
    r"\bZapier\b",
    r"\bMake\.com\b",
    r"\bn8n\b",
    r"\bmail merge\b",
    # Manual labor signal
    r"\bmanually (?:do|fill out|create|update|send|generate|track)\b",
    r"\bcopy.?paste\b",
    r"\bhand[-\s]?type\b",
    # Explicit "doing it in" pattern
    r"\bdoing (?:it|them|this|these) in (?:Excel|Sheets?|Word|QuickBooks)\b",
]

# Score component weights for compute_lienclear_relevance (sum = 1.0)
LIENCLEAR_RELEVANCE_WEIGHTS = {
    "domain_hit": 0.40,
    "state_match": 0.20,
    "dollar_anchor": 0.15,
    "icp_role": 0.15,
    "competitor_mention": 0.10,
}

# Role multipliers applied to final score
LIENCLEAR_ROLE_MULTIPLIERS = {
    "office_manager": 1.0,
    "owner_operator": 1.0,
    "bookkeeper": 0.9,
    "gc": 0.35,
    "homeowner": 0.25,
}

# ---------------------------------------------------------------------------
# Phase 3 — LLM extraction budget + mode config
# Guardrails apply to both `analyze --llm-extract --mode api` (Anthropic SDK)
# and `--mode batch` (Claude Code session workflow — exports posts to markdown
# batches, operator processes them in a Max-sub session, imports JSON back).
# Circuit breakers fire before extraction fans out; exceeding any limit
# aborts the run with a clear message. Tune per session.
# ---------------------------------------------------------------------------

# Default extraction mode. "batch" = export-to-file + process in a Claude
# Code session (zero marginal $, uses your Max quota). "api" = direct
# Anthropic SDK calls (paid, automated). Override via --mode on the CLI.
LLM_DEFAULT_MODE = "batch"

# Max posts processed in a single `analyze --llm-extract` invocation. Hard
# circuit breaker — prevents a runaway re-extract after a prompt-version
# bump from blasting through the whole corpus unintentionally. Raise via
# --max-posts when you genuinely want a backfill.
LLM_MAX_POSTS_PER_RUN = 1000

# Subs excluded from LLM extraction. Tuned from v0.1 backfill yield data:
# these subs produced 0% pain-rate (trade-photo/meme/career posts dominate)
# OR <10% pain-rate (SideProject is mostly "look at my project" promo).
# Posts from these subs still land in the posts table + clustering pipeline;
# only the LLM-extraction step skips them so we don't burn batch slots.
LLM_PREFILTER_SKIP_SUBS = {
    "Flooring", "Concrete", "estimators", "Carpentry", "Welding",
    "Plumbing", "HVAC", "Roofing", "electricians", "Painting",
    "SideProject",
}

# Per-sub caps to force diversity in the LLM extraction pool. Subs not
# listed have no cap. Tuned from v0.1 yield data — smallbusiness was 100/500
# at 20% and Contractor was 64/500 at 31%, both over-represented relative
# to higher-yield subs (ecommerce, productivity, Entrepreneur) starving for
# slots.
LLM_PREFILTER_SUB_CAPS = {
    "smallbusiness": 50,
    "Contractor": 50,
}

# Soft dollar ceiling for `--mode api` runs only (batch mode is $0 marginal).
# Computed against per-call usage from the Anthropic response. Hitting it
# aborts mid-run; bypass via --budget USD.
LLM_MAX_USD_PER_RUN = 5.00

# Batch-mode export: posts per batch file. Sized for ~50K input tokens so a
# single batch fits comfortably in a Claude Code session turn alongside
# instructions, the schema, and headroom for retries.
LLM_BATCH_SIZE = 50

# Where batch files live. Gitignored — see .gitignore data/.
LLM_BATCH_DIR = DATA_DIR / "llm_batches"

# Rough token estimates for the API-mode pre-flight $ check. Real usage
# comes from the API response; these are only used to refuse a run we
# already know will blow the budget.
LLM_ESTIMATED_INPUT_TOKENS_PER_POST = 800
LLM_ESTIMATED_OUTPUT_TOKENS_PER_POST = 300

# Approximate per-million-token rates ($USD). VERIFY against the live
# Anthropic pricing page (anthropic.com/pricing) before any production
# API-mode run — these are budget-planning ballparks, not billing source
# of truth. Conservative side; refresh when 4.X rates are confirmed.
LLM_PRICING = {
    "claude-haiku-4-5": {
        "input_per_m": 1.00, "output_per_m": 5.00, "cache_read_per_m": 0.10,
    },
    "claude-sonnet-4-6": {
        "input_per_m": 3.00, "output_per_m": 15.00, "cache_read_per_m": 0.30,
    },
    "claude-opus-4-7": {
        "input_per_m": 15.00, "output_per_m": 75.00, "cache_read_per_m": 1.50,
    },
}

# Default model for --mode api. Haiku 4.5 = cheapest path that still
# produces useful structured facets. Sonnet for when extraction quality
# matters more than throughput; Opus rarely needed for structured tasks.
LLM_DEFAULT_MODEL = "claude-haiku-4-5"

# RAG pre-filter: when True, only posts whose RAG-classifier similarity
# crosses SIMILARITY_THRESHOLD get LLM-extracted. Cuts cost ~3-4x in api
# mode at the price of inheriting RAG's recall ceiling. Recommended on
# for Haiku (cost-dominant) + batch mode (your session minutes are
# finite); off for Sonnet+ when accuracy matters more.
LLM_RAG_PREFILTER = True

# Extraction prompt version. Increment when the prompt or output schema
# changes; pain_facets rows store the version they were extracted under
# so re-extraction targets only stale rows. Without this guard a single
# prompt tweak triggers a full-corpus re-run at full cost.
# v0.2 (2026-05-31): adds behavioral-WTP facets (workaround_effort, time_cost,
# solution_seeking). Lockstep with FACET_FIELDS — the schema_fingerprint changed,
# so the importer refuses files generated against v0.1. Green-field corpus
# re-faceted at v0.2; old corpus stays v0.1 and resolves via best-version reader.
LLM_PROMPT_VERSION = "v0.2"

# ---------------------------------------------------------------------------
# Phase 4 — niche scoring from pain_facets
# Replaces the Phase-1 dumb scorer (revenue=avg opportunity, complexity=0.5
# constant) with rule-based functions in analysis/niche_scorer.py. Weights
# below are UNCALIBRATED v0 heuristics — Phase 5 verdict capture will
# calibrate against real build/watch/kill decisions. Tune freely; rank
# instability between runs is fine until verdicts exist.
# ---------------------------------------------------------------------------

# Revenue signal weights (must sum to 1.0).
REVENUE_SCORE_WEIGHTS = {
    "willingness_to_pay": 0.30,
    "max_dollar_anchor":  0.20,
    "market_size_signal": 0.20,
    "urgency":            0.20,
    "buyer_role":         0.10,
}

# Complexity signal weights (must sum to 1.0). Domain heuristic deliberately
# excluded — collinear with market_size_signal and would double-count the
# Lienclear sub-weighting bias.
COMPLEXITY_SCORE_WEIGHTS = {
    "integrations_count": 0.40,
    "market_size_signal": 0.20,
    "complexity_keywords": 0.40,
}

# W4-1 (2026-05-28) — saturation penalty applied multiplicatively to rank.
# `saturation = 1 - 1/(1 + K · log(1 + n_distinct_tools))` derived from
# pain_facets.integrations_mentioned + current_solution. Then
# `rank = (rev/(1+comp)) · max(FLOOR, 1 - saturation)`. The floor caps damage
# at 50% by default — saturated niches never disappear, just stop dominating.
# Supersedes 2026-05-25's display-only call (DECISIONS.md): the display chip
# proved insufficient — Niche #1 (PM software OPS-view) ranked #1 in a
# 450+-product red ocean. Tunable; rerun `analyze --rescore-niches` after.
SATURATION_K = 0.3              # decay constant — higher = steeper penalty
SATURATION_PENALTY_FLOOR = 0.5  # max multiplicative penalty (0.5 = 50% cap)
SATURATION_TAG_THRESHOLD = 0.30 # digest renders 🚨 RED OCEAN at/above this

# ---------------------------------------------------------------------------
# Buyer-side validation gate (2026-05-31) — the lienclear lesson, hardcoded.
# Three straight top-niche kills (Niche #1, lienclear, the 2026-05-31 digest)
# died because the pain-posters were OPERATORS (employees/PMs who feel the
# pain) while OWNERS control spend — so the `would_pay` signal was contaminated
# (see [[feedback-buyer-side-validation-mandatory]],
# [[feedback-construction-buyer-operator-split]]). Mirrors the W4-1 saturation
# pattern: a multiplicative rank penalty + digest tag, plus a HARD ⛔ block when
# buyer-side would-pay evidence is too thin to scope a build. Reads
# pain_facets.buyer_role + willingness_to_pay. Tunable; rerun
# `analyze --rescore-niches` (or any digest) after changing.
BUYER_SIDE_PENALTY_FLOOR = 0.5  # max multiplicative penalty (0.5 = 50% cap)
BUYER_SIDE_TAG_THRESHOLD = 0.40 # buyer_ratio below this → 🚩 OPERATOR-ONLY tag
MIN_BUYER_EVIDENCE = 3          # owner/finance would-pay facets to clear the ⛔
                                # hard gate — ties to the "3+ owner paid pilots"
                                # rule in [[feedback-buyer-side-validation-mandatory]]
BUYER_SIDE_BUYER_ROLES = {"owner", "finance"}        # control the spend
BUYER_SIDE_OPERATOR_ROLES = {"individual_contributor", "manager"}  # feel the pain

# ---------------------------------------------------------------------------
# Latent-demand signal (2026-05-31) — behavioral WTP, display-only.
# The 2026-05-31 green-field probe proved verbalized would_pay is ~0 in
# under-tooled operator markets (they vent pain but don't tool-shop —
# [[feedback-greenfield-wtp-absent]]). But the same posts reveal demand
# BEHAVIORALLY: a manual/labor workaround in current_solution ("spreadsheet",
# "by hand", "hired someone") = already paying in effort; recurring/blocking
# urgency = ongoing pain; a $ anchor = economic magnitude. Those are captured
# in pain_facets but feed the opportunity score nowhere (current_solution is
# read only by saturation, to EXCLUDE tools). This signal mines them to detect
# the OFF-DIAGONAL: high latent demand + low saturation = the green-field
# quadrant the would_pay-driven scorer is blind to. DISPLAY-ONLY this pass (no
# rank effect), mirroring how saturation shipped before W4-1.
LATENT_DEMAND_WEIGHTS = {       # blended over PRESENT sub-signals (renormalized),
                                # so v0.1 facets (missing the v0.2 fields) still score
    "workaround_effort": 0.35,  # v0.2 field; manual=0.6 / hired=1.0. Falls back to
                                # current_solution manual-term match on v0.1 facets.
    "time_cost":         0.20,  # v0.2 field; light/moderate/heavy
    "solution_seeking":  0.20,  # v0.2 field; asking/evaluating/switching
    "urgency":           0.15,
    "dollar_present":    0.10,
}
LATENT_DEMAND_TAG_THRESHOLD = 0.40   # 💡 tag + green-field eligibility floor
GREENFIELD_SATURATION_CEILING = 0.20 # saturation must be BELOW this for off-diagonal
GREENFIELD_MIN_FACETS = 3            # min eligible pain-facets for the green-field scan
# Manual/labor workarounds = POSITIVE demand (author invests effort/money on the
# problem). Substring-matched against current_solution. Deliberately SEPARATE from
# saturation._NON_TOOL_SOLUTIONS: "nothing/none" is genuine no-signal and is NOT
# here. The split is the crux — "I do it manually" != "I do nothing".
MANUAL_WORKAROUND_TERMS = {
    "spreadsheet", "excel", "google sheet", "manual", "by hand",
    "pen and paper", "paper", "notebook", "hired", "outsourc",
    "virtual assistant", "assistant", "whiteboard", "sticky note",
}

# Per-facet confidence is clipped to this range before weighting. Lower
# bound prevents low-confidence niches from being arbitrarily depressed;
# upper bound prevents a single confident outlier from dominating ten
# weaker agreements. Both ends are deliberately not 0 or 1.
FACET_CONFIDENCE_CLIP = (0.3, 0.85)

# Minimum sum of clipped confidences across a niche's faceted members for
# the niche to be eligible for facet-based scoring. Below this, fall back
# to the Phase-1 dumb scorer regardless of how many facet rows exist.
NICHE_MIN_EFFECTIVE_N = 1.5

# Scanned against pain_summary AND integrations_mentioned. Each hit adds
# 0.2 to the keyword sub-score (capped at 1.0). Keep small.
COMPLEXITY_KEYWORDS = [
    "real-time", "multi-state", "compliance", "auth", "PII",
    "scale", "enterprise integration",
]

# ---------------------------------------------------------------------------
# Phase 5 — verdict capture, taste-learning, saturation display
# Knobs for the build/watch/kill feedback loop, the cosine-based taste
# boost applied to niches similar to past `build` verdicts, and the
# growth-delta highlighting on `watch`-marked niches. Saturation ships
# as display-only (no threshold knob — the operator's eyes do the heavy
# /light judgment).
# ---------------------------------------------------------------------------

# Cosine similarity threshold to trigger a taste-boost on a niche. Above
# this against any prior `build`-verdict centroid, the niche gets
# rank * TASTE_BOOST_MULTIPLIER. 0.70 is conservative — only strongly-
# similar niches boost; 0.50 would surface looser matches.
TASTE_SIM_THRESHOLD = 0.70

# Multiplier applied to rank_score when taste-boost activates. 1.20 is a
# gentle nudge (a build-similar niche jumps roughly one rank position);
# 1.5+ starts to dominate the digest ordering.
TASTE_BOOST_MULTIPLIER = 1.20

# Don't activate taste-boost until at least this many build verdicts
# exist. N=1 is pure operator-bias amplification (one click pins all
# future digests); N=2 is the minimum for "this is a pattern, not a
# one-off." When N==1, the digest header shows a hint instead.
TASTE_MIN_BUILD_VERDICTS = 2

# Watched niche growth highlight threshold (fraction). When post_count
# or facet_count grew by this much since the watch verdict snapshot,
# the digest emphasizes the watched row. Below this, the delta is shown
# as plain text without emphasis.
WATCH_GROWTH_HIGHLIGHT_PCT = 0.20

# ---------------------------------------------------------------------------
# Gaming pivot — companion-tool discovery for game communities.
# Monetization model: free-with-ads OR micro-subs ($1-3/mo), NOT paid app
# sales. Audience reach (subreddit subscriber scale) replaces per-user WTP
# as the viability proxy. "should be free" is NOT a negative signal under
# this model — only "publisher should add this" (GAMING_KILL_PATTERNS)
# kills it. Per-game profiles compose these patterns with game-specific
# domain blocks (see FORZA_* below).
# ---------------------------------------------------------------------------

# Game-agnostic tool-request intent. Primary signal under the ad model —
# every "is there a tool for X" view is a future page-view on the tool we
# ship. Patterns allow 0-3 modifier words between the article and the
# tool-type noun ("a tune calculator", "a livery library site") since
# gaming asks rarely use bare nouns.
GAMING_TOOL_REQUEST_PATTERNS = [
    r"\banyone (?:made|built|know of|aware of|got|seen) (?:an? |the )?(?:\w+\s+){0,3}(?:app|site|tool|calculator|tracker|spreadsheet|sheet|website|bot|database|wiki)\b",
    r"\bis there (?:an? |the |any )?(?:\w+\s+){0,3}(?:app|tool|website|site|calculator|tracker|spreadsheet|sheet|bot|database|wiki)\b",
    r"\bwish (?:someone|there was|we had|i had) (?:would (?:make|build) )?(?:an? |the )?(?:\w+\s+){0,3}(?:app|tool|site|calculator|tracker|spreadsheet|sheet|bot)\b",
    r"\bwe need (?:an? |the )?(?:\w+\s+){0,3}(?:tool|app|site|calculator|tracker|bot|database)\b",
    r"\bdoes (?:anyone know of|a tool exist|an app exist|a site exist)\b",
    r"\bwhere(?:'s| is) the (?:\w+\s+){0,3}(?:app|tool|site|calculator|tracker|spreadsheet|sheet|database)\b",
    r"\bsomeone (?:should|please|needs to) (?:make|build|create) (?:a |an |the )?(?:\w+\s+){0,3}(?:tool|app|site|calculator|tracker|bot|database)\b",
    r"\b(?:looking for|need) (?:an? |the )?(?:\w+\s+){0,3}(?:app|tool|site|calculator|tracker|spreadsheet|database)\b",
]

# DIY workaround — strongest conviction signal. Someone who built a
# spreadsheet will gladly use a free ad-supported web version. Mirrors
# the LIENCLEAR_DIY_PATTERNS playbook.
GAMING_DIY_PATTERNS = [
    r"\bI (?:made|built|created|coded|wrote|set up) (?:a |my own |an? )?(?:spreadsheet|google sheet|discord bot|website|app|tool|tracker|calculator)\b",
    r"\bwe (?:made|built|created|coded|wrote) (?:a |our own )?(?:spreadsheet|google sheet|discord bot|website|app|tool|tracker|calculator)\b",
    r"\bbuilt my own (?:tool|tracker|calculator|sheet|spreadsheet|app)\b",
    r"\bhacked together (?:a |an? )?(?:sheet|bot|tool|script)\b",
    r"\bin (?:Excel|Google Sheets?|a spreadsheet|Notion)\b",
    r"\bmy (?:spreadsheet|google sheet|tracker|calculator) for\b",
]

# Bonus micro-sub viability hints. NOT a gate — most gaming tools never
# see one of these and still monetize fine via ads. Applies as a small
# multiplier on the final relevance score.
GAMING_PATREON_PATTERNS = [
    r"\bsupport the dev(?:eloper)?\b",
    r"\bPatreon\b",
    r"\bko-?fi\b",
    r"\bbuy me a coffee\b",
    r"\btip jar\b",
    r"\bdonat(?:e|ion)\b",
    r"\$\s*(?:1|2|3|5)\s*(?:/mo|/month|per month|a month)\b",
]

# Kill the opportunity: post wants the publisher to build it, not the
# market. Narrowly scoped — does NOT include generic "free please"
# complaints (those are compatible with the ad-revenue model).
GAMING_KILL_PATTERNS = [
    r"\bshould be in (?:the )?(?:base )?game\b",
    r"\b(?:Microsoft|Playground|Turn\s?10|Sony|Bethesda|Capcom|Activision|Ubisoft|EA|Bungie|Arrowhead) should add\b",
    r"\bdevs (?:need to|should) add\b",
    r"\bbase game (?:should|needs to) (?:include|have)\b",
    r"\bwhy isn'?t this in the game\b",
]

GAMING_URGENCY_PATTERNS = [
    r"\bsince the (?:update|patch|launch|drop|release)\b",
    r"\bpost[- ]launch\b",
    r"\bbefore (?:season|event|playlist) ends\b",
    r"\bthis (?:season|playlist|week)\b",
    r"\bFOMO\b",
    r"\bweekly (?:reset|playlist|rotation)\b",
]

# Relevance score weights (sum = 1.0). Note `audience_reach` replaces the
# B2B-pipeline `monetization` slot — under the ad model, reach IS the
# viability signal. Patreon and kill patterns modify the score via
# multiplier, not a weighted component.
GAMING_RELEVANCE_WEIGHTS = {
    "tool_request":   0.40,
    "diy_evidence":   0.25,
    "audience_reach": 0.20,
    "domain_hit":     0.15,
}

# Reach ceiling — recalibrated for gaming-sub scale (vs B2B 10M ceiling).
# r/forzahorizon5 ~150K, r/Helldivers ~700K, r/leagueoflegends ~7M.
# Reach-score = min(1.0, subscribers / ceiling).
GAMING_AUDIENCE_REACH_CEILING = 500_000

# Multipliers applied AFTER weighted score sum
GAMING_PATREON_MULTIPLIER = 1.10   # bonus when WTP-via-tip signal present
GAMING_KILL_MULTIPLIER    = 0.4    # demand pointed at publisher, not market

# ---------------------------------------------------------------------------
# Forza profile — first game-specific gaming overlay
# Triggered by new Forza launch 2026-05-19. Domain: tuning, livery, online,
# progression. Pattern parallel to LIENCLEAR_* — copy this block when
# adding Helldivers / Marvel Rivals / etc.
# ---------------------------------------------------------------------------

FORZA_DOMAIN_KEYWORDS = [
    # Game name anchors — strongest signal a post is on-topic
    r"\bForza\b", r"\bFH[456]\b",
    r"\bforza horizon\b", r"\bforza motorsport\b",
    # Forza-specific class system — only S1/S2/X are Forza-exclusive.
    # `class A` / `class B` / `class C` leak into real estate (property class),
    # construction (building grade), networking (IP class), etc. They're
    # legitimate Forza vocab too but the false-positive risk dominates;
    # legitimate Forza posts will hit other patterns (\bForza\b, \bFH[456]\b).
    r"\bclass S[12]\b", r"\bclass X\b",
    # PI ratings — only match when anchored to a tune/build/setup bigram.
    r"\b(?:tune|build|setup|spec)\s+(?:for|at|on|@)\s+(?:[ABCDE]|S[12]|X)\s?\d{3}\b",
    # Sim-rig + FFB — narrow enough to be Forza/sim-racing exclusive
    r"\bFFB\b", r"\bforce feedback\b", r"\bwheelbase\b",
    r"\bFanatec\b", r"\bMoza\b",
    r"\bdeadzone\b", r"\bsensitivity curve\b",
    # Tuning vocabulary — bigrams only (bare "tune" too leaky into business
    # / piano-tuner / fine-tuning false positives)
    r"\btune (?:for|sheet|file|setup|guide|code|calculator|share|trade)\b",
    r"\b(?:share|trade|swap|find|drop|sell|sharing|trading) (?:my )?tunes?\b",
    r"\btuning (?:guide|sheet|tool|app|calculator|setup|file|app|spreadsheet)\b",
    r"\bgear ratios? (?:for|of|setup)\b",
    r"\bbrake bias\b",
    r"\bdyno (?:tune|run|sheet|chart)\b",
    # Cosmetic — bigrams
    r"\blivery code\b", r"\blivery share\b", r"\bshare liveries\b",
    r"\bliveries (?:for|of|on|in)\b", r"\bvinyl group\b",
    r"\beventlab\b", r"\bphoto mode\b",
    # Online / progression — Forza-specific terms
    r"\bdrivatar\b", r"\bfestival playlist\b",
    r"\bcar pass\b", r"\brivals (?:mode|time|leaderboard)\b",
    r"\brace regulations?\b",
    r"\bcredits? farm\b", r"\bwheelspin\b",
    # Telemetry — bigrams
    r"\btelemetry (?:overlay|data|app|export)\b",
    r"\blap time(?:s)? (?:for|on|in)\b", r"\bsplit times?\b",
]

FORZA_COMPETITORS = [
    "ForzaTune Pro", "ForzaTune", "Forza Race Engineer",
    "Tuneberg", "Forzatools", "ForzaHub", "TuneOptimiser",
    "Forza Stats",
]

# Highest-topic-wins on multi-hit (parallels LIENCLEAR_PHASE_PATTERNS).
FORZA_TOPIC_PATTERNS = {
    1: [  # tuning & telemetry
        r"\btun(?:e|es|ing|er)\b", r"\bFFB\b", r"\bforce feedback\b",
        r"\bdyno\b", r"\bgear ratios?\b", r"\btelemetry\b",
        r"\bdeadzone\b", r"\bsensitivity curve\b", r"\bcamber\b",
        r"\bbrake bias\b", r"\bwheelbase\b",
    ],
    2: [  # cosmetic & creative
        r"\blivery\b", r"\bliveries\b", r"\bvinyl\b",
        r"\bphoto mode\b", r"\beventlab\b", r"\bblueprint\b",
    ],
    3: [  # online & competitive
        r"\brivals (?:mode)?\b", r"\bleaderboard\b", r"\bchampionship\b",
        r"\brace regulations?\b", r"\bdrivatar\b", r"\blobby\b",
        r"\bsplit times?\b", r"\blap time\b",
    ],
    4: [  # progression & economy
        r"\baccolade\b", r"\bfestival playlist\b", r"\bcar pass\b",
        r"\bcredits? farm\b", r"\bwheelspin\b",
    ],
}

FORZA_TOPIC_LABELS = {
    1: "Tuning & telemetry",
    2: "Liveries & creative",
    3: "Online & competitive",
    4: "Progression & economy",
}

FORZA_PLAYER_PATTERNS = {
    "tuner": [
        r"\btune for\b", r"\btuning sheet\b", r"\bshare (?:tunes?|tuning)\b",
        r"\btuning guide\b", r"\bmy tunes?\b",
    ],
    "livery_artist": [
        r"\bshare liveries\b", r"\blivery code\b", r"\bvinyl group\b",
        r"\bmy liveries\b", r"\bpaint(?:er|ing) job\b",
    ],
    "sim_racer": [
        r"\bwheelbase\b", r"\bFanatec\b", r"\bMoza\b",
        r"\bLogitech (?:G\d+|wheel)\b",
        r"\bsim setup\b", r"\bFFB settings\b", r"\bsim racer\b",
    ],
    "casual": [
        r"\bfirst Forza\b", r"\bnew to (?:forza|the series|the game)\b",
        r"\bjust started\b", r"\bcasual (?:player|gamer)\b",
    ],
}

# Casual posts less likely to convert to ad-revenue traffic (lower
# session depth, more transient engagement).
FORZA_PLAYER_MULTIPLIERS = {
    "tuner":         1.0,
    "livery_artist": 1.0,
    "sim_racer":     1.0,
    "casual":        0.6,
}

# Score component weights (sum = 1.0). `audience_reach` replaces per-user
# `monetization` per the ad-revenue model.
FORZA_RELEVANCE_WEIGHTS = {
    "domain_hit":         0.30,
    "tool_request":       0.25,
    "diy_evidence":       0.20,
    "audience_reach":     0.15,
    "competitor_mention": 0.10,
}

# Profile overlays — selected via `--profile` CLI flag on export
PROFILES = {
    "lienclear": {
        "min_relevance": 0.30,
        "strong_relevance": 0.40,
        "min_cluster_posts": 2,
        "rank_by": "lienclear_relevance",
        "include_competitor_gap_section": True,
        "boost_subs": {
            "Construction", "Contractor", "ConstructionManagers",
            "Electricians", "HVAC", "Plumbing", "Roofing",
            "Concrete", "Carpentry", "Painting", "Flooring",
            "Welding", "Estimators",
        },
    },
    "forza": {
        "min_relevance": 0.25,            # lower than lienclear — launch corpus is thin
        "strong_relevance": 0.40,
        "min_cluster_posts": 2,
        "rank_by": "forza_relevance",
        "include_tool_gap_section": True,
        "boost_subs": {
            "forza", "ForzaHorizon", "forzahorizon6", "forzahorizon5",
            "ForzaMotorsport", "forzahorizon4", "simracing",
        },
    },
}
