# Why: Local embeddings for dedup and search
# Deps: Ollama HTTP API, config, json
# How: Calls Ollama, compares cosine similarity, graceful fallback

import json
import math

import requests

from config import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL

_OLLAMA_AVAILABLE: bool | None = None


def _check_ollama() -> bool:
    """Ping Ollama once per process to avoid repeated connection failures."""
    global _OLLAMA_AVAILABLE
    if _OLLAMA_AVAILABLE is not None:
        return _OLLAMA_AVAILABLE
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        _OLLAMA_AVAILABLE = resp.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        _OLLAMA_AVAILABLE = False
    return _OLLAMA_AVAILABLE


def reset_ollama_check():
    """Reset the cached availability flag (useful after starting Ollama)."""
    global _OLLAMA_AVAILABLE
    _OLLAMA_AVAILABLE = None


def get_embedding(text: str) -> list[float] | None:
    """Embed text using Ollama. Returns a float vector or None if unavailable."""
    if not text or not _check_ollama():
        return None
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={"model": OLLAMA_EMBED_MODEL, "input": text},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        return None
    except Exception:
        return None


def get_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Embed multiple texts. Returns a list aligned with the input."""
    if not texts or not _check_ollama():
        return [None] * len(texts)
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={"model": OLLAMA_EMBED_MODEL, "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings", [])
        result = []
        for i in range(len(texts)):
            result.append(embeddings[i] if i < len(embeddings) else None)
        return result
    except Exception:
        return [None] * len(texts)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Pure Python, no numpy needed."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def find_most_similar(
    query_embedding: list[float],
    candidates: list[tuple[int, list[float]]],
    top_n: int = 5,
    threshold: float = 0.0,
) -> list[tuple[int, float]]:
    """
    Find the most similar items from a list of (id, embedding) tuples.
    Returns list of (id, similarity_score) sorted by score descending.
    """
    scored = []
    for item_id, emb in candidates:
        sim = cosine_similarity(query_embedding, emb)
        if sim >= threshold:
            scored.append((item_id, sim))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


def is_semantically_duplicate(
    new_embedding: list[float],
    existing_embeddings: list[list[float]],
    threshold: float = 0.85,
) -> bool:
    """Check if a new embedding is too similar to any existing one."""
    for emb in existing_embeddings:
        if cosine_similarity(new_embedding, emb) >= threshold:
            return True
    return False


def serialize_embedding(embedding: list[float] | None) -> str | None:
    """Serialize a float vector to JSON string for DB storage."""
    if embedding is None:
        return None
    return json.dumps(embedding)


def deserialize_embedding(data: str | None) -> list[float] | None:
    """Deserialize a JSON string back to a float vector."""
    if not data:
        return None
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None
