"""RAG-based pain-point classifier using sentence-transformers + ChromaDB."""

import hashlib
import json

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from analysis.keywords import INTENT_PRIORITY, NOISE_CATEGORIES
from config import CHROMA_PATH, EMBEDDING_MODEL, SIMILARITY_THRESHOLD

COLLECTION_NAME = "pain_point_seeds"

# Archetype seed phrases per intent category.
# Each phrase represents a prototypical pain-point expression.
SEEDS: dict[str, list[str]] = {
    "seeking_tool": [
        "Is there an app or tool that can do this for me?",
        "What software do you use to manage this?",
        "Looking for a good alternative to handle invoicing",
        "Any recommendations for a tool that tracks leads automatically?",
        "Does anyone know a service that does this well?",
        "What do you all use for payroll and scheduling?",
        "Need something to automate my client onboarding",
        "What do you guys use for AIA G702 G703 pay applications?",
        "Is there a simple lien waiver tool that handles state-specific forms?",
        "Looking for a Levelset alternative now that Procore bought it",
        "Need software to generate conditional and unconditional waivers",
        "How do I record this transaction in QuickBooks?",
        "What's the best way to handle this in QBO?",
        "Anyone know a clean way to track this in QuickBooks Online?",
        "How do you handle multi-entity bookkeeping in QBO?",
        "What do you guys use to track time across multiple jobsites?",
        "Looking for a simple way to send progress invoices to my GCs",
        "Any tool that helps with change order tracking on commercial jobs?",
        "Need a way to manage T&M billing without spreadsheets",
        "How do you all handle retainage tracking across jobs?",
        "What software handles subcontractor payment workflow end to end?",
        "What software do you use to collect rent and track late payments?",
        "Looking for a small-landlord property management app that handles maintenance requests",
        "Any Buildium or AppFolio alternative for landlords with under 20 units?",
    ],
    "would_pay": [
        "I would gladly pay for a solution to this problem",
        "Shut up and take my money if someone builds this",
        "I'm willing to pay good money for something that actually works",
        "This is worth paying for, I've been dealing with this for years",
        "I'd pay $50/month easily if it solved this",
        "I would pay 99 a month for a lien waiver and pay app tool",
        "Honestly $150 a month would be worth it just to stop using Excel for pay apps",
        "I'd pay real money for something that just handles GC payment workflow end to end",
        "I would pay $30 a month easily for a tool that handles rent collection and tenant communication",
    ],
    "frustrated": [
        "I'm so frustrated with the existing tools, they're all terrible",
        "Why is it so hard to find something that just works?",
        "Every app I've tried is buggy and unusable",
        "The current options are garbage for small businesses",
        "I can't stand how clunky this software is",
        "Nothing on the market actually handles this properly",
        "Struggling with this workflow for months and can't find a fix",
        "Procore is way too expensive for a small sub like us",
        "Levelset got gutted after Procore acquired them, no real free tier anymore",
        "Textura charges us $25 every single pay application, absurd",
        "Every GC wants a different system, Procore Textura paper AIA forms",
        "Almost signed an unconditional final waiver before getting my check, would have given up lien rights",
        "QuickBooks has no clean way to handle this, every workaround breaks something else",
        "Spent hours trying to figure out how to record this properly in QBO and there's no good answer",
        "Net 60 from the GC is killing my cash flow this quarter",
        "Spent another weekend chasing down payment on a closed job",
        "Lost a $40k claim because I missed the preliminary notice deadline",
        "Buildium pricing is absurd for a small landlord with a handful of units",
        "Spent another month chasing rent from a tenant who keeps ghosting",
    ],
    "feature_request": [
        "I wish there was a simple way to do this",
        "Someone should build a tool for this gap",
        "Why hasn't anyone made something that does X and Y together?",
        "This feature is missing from every app I've tried",
        "The tool I use doesn't support this integration at all",
        "Need a cross-GC dashboard so I can see all my projects in one place",
        "Wish there was a sub-friendly portal that just does waivers and pay apps",
    ],
    "unbundle": [
        "It's overkill for what I actually need",
        "I just need the simple version, not a full enterprise suite",
        "Paying for features I'll never use",
        "All I need is a lightweight tool, not another bloated platform",
        "I don't need half of what they're selling me",
        "Procore has way too much we don't need, just want lien waivers and pay apps",
        "Don't need the full construction management suite, just billing",
    ],
    # ----- Noise categories (Prefilter v2) ----------------------------------
    # These cause classify() to return None when they win the priority tiebreak.
    # A pain seed that also fires on the same post still wins (priority > 0).
    "noise_career": [
        "Should I take this job offer or stay where I am?",
        "Is a college degree worth it for this trade?",
        "How much do you make as a project manager?",
        "What's your career path and how did you get into this industry?",
        "Thinking about going to trade school, is it worth it?",
        "What's everybody's career and what are we making? Share age, location, years",
        "How do I break into property management as a career?",
    ],
    "noise_support": [
        "Can I evict a tenant for not paying rent?",
        "Is this clause in my lease actually legal?",
        "Tenant won't leave after I served notice, what are my options?",
        "Security deposit dispute, what are my rights as a landlord?",
        "Can my landlord raise the rent this much in one year?",
        "Is it legal for my landlord to enter the unit without notice?",
        "How do I handle a hostile tenant who keeps complaining?",
    ],
    "noise_observer": [
        "I work with hundreds of agencies and the biggest issue I see is X",
        "Most of my clients struggle with this exact thing every week",
        "When I consult with SaaS founders they all say the same problem",
        "We help our clients solve this every day at our agency",
        "Founders I work with constantly complain about this gap",
        "From my experience working with B2B teams, the real gap is Z",
    ],
}


class RAGClassifier:
    """Classifies posts via semantic similarity to pain-point archetype seeds."""

    def __init__(self):
        self._model = None
        self._client = None
        self._collection = None

    def _load(self):
        if self._model is not None:
            return
        self._model = SentenceTransformer(EMBEDDING_MODEL)
        self._client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._ensure_seeds()

    def _seeds_hash(self) -> str:
        payload = json.dumps(SEEDS, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    def _ensure_seeds(self):
        current_hash = self._seeds_hash()
        existing = self._collection.count()
        # Reseed when the SEEDS dict changes — the collection's metadata stores
        # the hash of the last embedded seed set so version drift is detected.
        # Missing/None metadata reads as stale, which safely forces a reseed.
        existing_meta = self._collection.metadata or {}
        if existing > 0 and existing_meta.get("seeds_hash") == current_hash:
            return
        # Reseed needed. Drop any stale/partial collection first so we start
        # from a clean slate (no seeds_hash yet — it is stamped last, below).
        if existing > 0:
            self._client.delete_collection(name=COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        docs, ids, metas = [], [], []
        for category, phrases in SEEDS.items():
            for i, phrase in enumerate(phrases):
                docs.append(phrase)
                ids.append(f"{category}_{i}")
                metas.append({"category": category})
        embeddings = self._model.encode(docs, normalize_embeddings=True).tolist()
        self._collection.add(documents=docs, embeddings=embeddings, ids=ids, metadatas=metas)
        # Stamp the hash LAST — it is the commit marker. A crash before this
        # point leaves no/stale hash, so the next run reseeds rather than
        # trusting a partially embedded collection. Distance function is locked
        # at collection-create time (hnsw:space=cosine above), so we only stamp
        # seeds_hash here — chroma's modify() rejects any hnsw:space entry
        # even when the value matches.
        self._collection.modify(metadata={"seeds_hash": current_hash})

    def classify(self, title: str, body: str) -> dict | None:
        self._load()
        text = f"{title} {body}".strip()
        if not text:
            return None

        embedding = self._model.encode([text], normalize_embeddings=True).tolist()
        results = self._collection.query(
            query_embeddings=embedding,
            n_results=5,
            include=["metadatas", "distances"],
        )

        distances = results["distances"][0]
        metadatas = results["metadatas"][0]

        # ChromaDB cosine distance = 1 - similarity; convert back
        hits = [
            (1.0 - dist, meta["category"])
            for dist, meta in zip(distances, metadatas)
            if (1.0 - dist) >= SIMILARITY_THRESHOLD
        ]

        if not hits:
            return None

        # Only categories within a similarity margin of the top hit can win on
        # priority — prevents a barely-passing seed from outranking a much
        # stronger semantic match in a different (lower-priority) bucket.
        top_similarity = max(s for s, _ in hits)
        margin = 0.15
        candidates = [(s, c) for s, c in hits if s >= top_similarity - margin]

        primary_category = max(
            candidates,
            key=lambda sc: (INTENT_PRIORITY.get(sc[1], 0), sc[0]),
        )[1]

        # Prefilter v2: noise-only matches return None. A pain seed firing on
        # the same post wins the priority tiebreak (pain priorities are 1-5;
        # noise sits at 0), so borderline pain+noise overlaps still classify.
        if primary_category in NOISE_CATEGORIES:
            return None

        top_similarity = max(s for s, c in candidates if c == primary_category)

        # Sentiment intensity: normalize top similarity to [0, 1] relative to threshold
        sentiment_intensity = min(1.0, (top_similarity - SIMILARITY_THRESHOLD) / (1.0 - SIMILARITY_THRESHOLD))

        return {
            "matched_patterns": json.dumps([c for _, c in hits]),
            "intent_category": primary_category,
            "sentiment_intensity": round(sentiment_intensity, 4),
        }
