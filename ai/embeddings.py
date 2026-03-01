# Why: Local embeddings for dedup and search
# Deps: Ollama HTTP API, HuggingFace API, config, json
# How: Tries Ollama first, falls back to HF Inference API, then None

import json
import math

import requests

from config import HF_EMBED_MODEL, HF_TOKEN, OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL

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


def _hf_embed(texts: list[str]) -> list[list[float] | None]:
    """Embed via HuggingFace Inference API. Returns None per item on failure."""
    if not HF_TOKEN:
        return [None] * len(texts)
    try:
        resp = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_EMBED_MODEL}",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": texts, "options": {"wait_for_model": True}},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, list) and len(result) == len(texts):
            return result
        return [None] * len(texts)
    except Exception:
        return [None] * len(texts)


def get_embedding(text: str) -> list[float] | None:
    """Embed text — tries Ollama first, then HF Inference API."""
    if not text:
        return None
    if _check_ollama():
        try:
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": OLLAMA_EMBED_MODEL, "input": text},
                timeout=10,
            )
            resp.raise_for_status()
            embeddings = resp.json().get("embeddings")
            if embeddings:
                return embeddings[0]
        except Exception:
            pass
    return _hf_embed([text])[0]


def get_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Embed multiple texts — tries Ollama first, then HF Inference API."""
    if not texts:
        return []
    if _check_ollama():
        try:
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": OLLAMA_EMBED_MODEL, "input": texts},
                timeout=30,
            )
            resp.raise_for_status()
            embeddings = resp.json().get("embeddings", [])
            result = [embeddings[i] if i < len(embeddings) else None for i in range(len(texts))]
            return result
        except Exception:
            pass
    return _hf_embed(texts)


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
