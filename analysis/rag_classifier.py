"""RAG-based pain-point classifier using sentence-transformers + ChromaDB."""

import json

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from analysis.keywords import INTENT_PRIORITY
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
    ],
    "would_pay": [
        "I would gladly pay for a solution to this problem",
        "Shut up and take my money if someone builds this",
        "I'm willing to pay good money for something that actually works",
        "This is worth paying for, I've been dealing with this for years",
        "I'd pay $50/month easily if it solved this",
    ],
    "frustrated": [
        "I'm so frustrated with the existing tools, they're all terrible",
        "Why is it so hard to find something that just works?",
        "Every app I've tried is buggy and unusable",
        "The current options are garbage for small businesses",
        "I can't stand how clunky this software is",
        "Nothing on the market actually handles this properly",
        "Struggling with this workflow for months and can't find a fix",
    ],
    "feature_request": [
        "I wish there was a simple way to do this",
        "Someone should build a tool for this gap",
        "Why hasn't anyone made something that does X and Y together?",
        "This feature is missing from every app I've tried",
        "The tool I use doesn't support this integration at all",
    ],
    "unbundle": [
        "It's overkill for what I actually need",
        "I just need the simple version, not a full enterprise suite",
        "Paying for features I'll never use",
        "All I need is a lightweight tool, not another bloated platform",
        "I don't need half of what they're selling me",
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

    def _ensure_seeds(self):
        existing = self._collection.count()
        if existing > 0:
            return
        docs, ids, metas = [], [], []
        for category, phrases in SEEDS.items():
            for i, phrase in enumerate(phrases):
                docs.append(phrase)
                ids.append(f"{category}_{i}")
                metas.append({"category": category})
        embeddings = self._model.encode(docs, normalize_embeddings=True).tolist()
        self._collection.add(documents=docs, embeddings=embeddings, ids=ids, metadatas=metas)

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

        # Pick highest-priority category among hits
        categories_seen: dict[str, float] = {}
        for similarity, category in hits:
            priority = INTENT_PRIORITY.get(category, 0)
            if category not in categories_seen or priority > INTENT_PRIORITY.get(
                list(categories_seen.keys())[-1], 0
            ):
                categories_seen[category] = similarity

        primary_category = max(categories_seen, key=lambda c: INTENT_PRIORITY.get(c, 0))
        top_similarity = categories_seen[primary_category]

        # Sentiment intensity: normalize top similarity to [0, 1] relative to threshold
        sentiment_intensity = min(1.0, (top_similarity - SIMILARITY_THRESHOLD) / (1.0 - SIMILARITY_THRESHOLD))

        return {
            "matched_patterns": json.dumps([c for _, c in hits]),
            "intent_category": primary_category,
            "sentiment_intensity": round(sentiment_intensity, 4),
        }
