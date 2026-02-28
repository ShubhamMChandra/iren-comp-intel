"""
Tests for ai/embeddings.py — math correctness, dedup logic, and fallback behavior.

All tests use mock embeddings so Ollama doesn't need to be running.
"""

import math
from unittest.mock import patch

import pytest

from ai.embeddings import (
    cosine_similarity,
    deserialize_embedding,
    find_most_similar,
    get_embedding,
    is_semantically_duplicate,
    serialize_embedding,
)


# ---------------------------------------------------------------------------
# cosine_similarity math
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_known_angle(self):
        """45-degree angle between [1,0] and [1,1] → cos(45°) ≈ 0.7071."""
        a = [1.0, 0.0]
        b = [1.0, 1.0]
        expected = 1.0 / math.sqrt(2)
        assert cosine_similarity(a, b) == pytest.approx(expected, abs=1e-6)

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0

    def test_high_dimensional(self):
        """768-dim vectors (nomic-embed-text output size)."""
        a = [float(i) for i in range(768)]
        b = [float(i) for i in range(768)]
        assert cosine_similarity(a, b) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# is_semantically_duplicate
# ---------------------------------------------------------------------------

class TestIsSemanticDuplicate:
    def test_duplicate_detected(self):
        new = [1.0, 0.0, 0.0]
        existing = [[0.99, 0.1, 0.0]]  # very similar
        assert is_semantically_duplicate(new, existing, threshold=0.9)

    def test_not_duplicate(self):
        new = [1.0, 0.0, 0.0]
        existing = [[0.0, 1.0, 0.0]]  # orthogonal
        assert not is_semantically_duplicate(new, existing, threshold=0.85)

    def test_empty_existing(self):
        new = [1.0, 0.0, 0.0]
        assert not is_semantically_duplicate(new, [], threshold=0.85)

    def test_threshold_boundary(self):
        a = [1.0, 0.0]
        b = [1.0, 0.0]
        assert is_semantically_duplicate(a, [b], threshold=1.0)

    def test_multiple_existing_one_match(self):
        new = [1.0, 0.0, 0.0]
        existing = [
            [0.0, 1.0, 0.0],  # orthogonal
            [0.0, 0.0, 1.0],  # orthogonal
            [0.98, 0.1, 0.1],  # very similar
        ]
        assert is_semantically_duplicate(new, existing, threshold=0.9)


# ---------------------------------------------------------------------------
# find_most_similar
# ---------------------------------------------------------------------------

class TestFindMostSimilar:
    def test_returns_sorted(self):
        query = [1.0, 0.0]
        candidates = [
            (1, [0.0, 1.0]),   # orthogonal → ~0.0
            (2, [1.0, 0.0]),   # identical → 1.0
            (3, [0.7, 0.7]),   # diagonal → ~0.7
        ]
        results = find_most_similar(query, candidates, top_n=3)
        ids = [r[0] for r in results]
        assert ids[0] == 2  # most similar first

    def test_top_n_limit(self):
        query = [1.0, 0.0]
        candidates = [(i, [1.0, 0.0]) for i in range(10)]
        results = find_most_similar(query, candidates, top_n=3)
        assert len(results) == 3

    def test_threshold_filters(self):
        query = [1.0, 0.0]
        candidates = [
            (1, [0.0, 1.0]),  # sim ≈ 0.0
            (2, [1.0, 0.0]),  # sim = 1.0
        ]
        results = find_most_similar(query, candidates, top_n=10, threshold=0.5)
        assert len(results) == 1
        assert results[0][0] == 2


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_round_trip(self):
        vec = [0.1, 0.2, 0.3, -0.5]
        serialized = serialize_embedding(vec)
        deserialized = deserialize_embedding(serialized)
        assert deserialized == pytest.approx(vec)

    def test_none_input(self):
        assert serialize_embedding(None) is None
        assert deserialize_embedding(None) is None

    def test_empty_string(self):
        assert deserialize_embedding("") is None

    def test_bad_json(self):
        assert deserialize_embedding("not json") is None


# ---------------------------------------------------------------------------
# Fallback when Ollama is unavailable
# ---------------------------------------------------------------------------

class TestOllamaFallback:
    @patch("ai.embeddings._check_ollama", return_value=False)
    def test_get_embedding_returns_none(self, mock_check):
        result = get_embedding("some text")
        assert result is None

    @patch("ai.embeddings._check_ollama", return_value=False)
    def test_empty_text_returns_none(self, mock_check):
        result = get_embedding("")
        assert result is None

    @patch("ai.embeddings._check_ollama", return_value=True)
    @patch("ai.embeddings.requests.post")
    def test_successful_embedding(self, mock_post, mock_check):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "embeddings": [[0.1, 0.2, 0.3]]
        }
        mock_post.return_value.raise_for_status = lambda: None

        result = get_embedding("test text")
        assert result == [0.1, 0.2, 0.3]

    @patch("ai.embeddings._check_ollama", return_value=True)
    @patch("ai.embeddings.requests.post", side_effect=Exception("connection failed"))
    def test_network_error_returns_none(self, mock_post, mock_check):
        result = get_embedding("test text")
        assert result is None
