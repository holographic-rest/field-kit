"""
Field-Kit v0.1 Embeddings Module (Sprint 1)

Provides deterministic text embeddings for offline/test use and optional
real embeddings via OpenAI for development.

DESIGN NOTES:
- Uses hashlib.sha256 for stable hashing (NOT Python's built-in hash() which is salted)
- HashEmbeddingBackend uses char n-grams with signed hashing for determinism
- OpenAIEmbeddingBackend has disk cache to avoid repeated API calls
- Pure Python implementation (no numpy required, but API is compatible)

Usage:
    from fieldkit.embeddings import get_default_embedder, cosine_sim

    embedder = get_default_embedder()
    vecs = embedder.embed_texts(["hello world", "hi there"])
    sim = cosine_sim(vecs[0], vecs[1])
"""

import hashlib
import json
import math
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple, Union

# Type alias for embedding vectors (pure Python list of floats)
Vector = List[float]
Matrix = List[Vector]


# =============================================================================
# Utility Functions
# =============================================================================

def l2_normalize(vec: Vector) -> Vector:
    """
    L2 normalize a vector to unit length.

    Args:
        vec: Input vector as list of floats

    Returns:
        Normalized vector with L2 norm = 1.0
    """
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-12:
        return [0.0] * len(vec)
    return [x / norm for x in vec]


def cosine_sim(a: Vector, b: Vector) -> float:
    """
    Compute cosine similarity between two vectors.

    Both vectors should be L2 normalized for this to return values in [-1, 1].
    If not normalized, this computes: (a · b) / (|a| * |b|)

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity as float in range [-1, 1]
    """
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions must match: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0

    return dot / (norm_a * norm_b)


def pairwise_cosine_matrix(A: Matrix, B: Matrix) -> Matrix:
    """
    Compute pairwise cosine similarity matrix between two sets of vectors.

    Args:
        A: Matrix of shape (N, dim) - list of N vectors
        B: Matrix of shape (M, dim) - list of M vectors

    Returns:
        Matrix of shape (N, M) where result[i][j] = cosine_sim(A[i], B[j])
    """
    result = []
    for a in A:
        row = [cosine_sim(a, b) for b in B]
        result.append(row)
    return result


# =============================================================================
# Text Normalization
# =============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize text for embedding.

    - Lowercase
    - Collapse whitespace
    - Light punctuation stripping (keep apostrophes in contractions)

    Args:
        text: Raw input text

    Returns:
        Normalized text string
    """
    text = text.lower()
    # Remove most punctuation but keep apostrophes in contractions
    text = re.sub(r"[^\w\s']", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def text_hash(text: str) -> str:
    """
    Compute stable SHA256 hash of normalized text.

    Args:
        text: Input text (will be normalized first)

    Returns:
        Hex string of SHA256 hash
    """
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# =============================================================================
# Embedder Protocol / ABC
# =============================================================================

class Embedder(ABC):
    """Abstract base class for text embedding backends."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> Matrix:
        """
        Embed a list of texts into vectors.

        Args:
            texts: List of text strings to embed

        Returns:
            Matrix of shape (len(texts), dim) where each row is an embedding
        """
        pass

    @property
    @abstractmethod
    def dim(self) -> int:
        """Return the embedding dimension."""
        pass


# =============================================================================
# HashEmbeddingBackend (Deterministic, Offline, Test-Safe)
# =============================================================================

class HashEmbeddingBackend(Embedder):
    """
    Deterministic embedding backend using stable SHA256 hashing.

    Uses char n-grams AND word unigrams with signed hashing to produce dense vectors.
    Completely deterministic and requires no network calls.

    Design:
    - Extract char n-grams (default: 3-5 chars) for character-level patterns
    - Extract word unigrams for semantic signal
    - Hash each feature with SHA256 to get index and sign
    - Accumulate into dense vector with feature weighting
    - L2 normalize at the end

    Why SHA256 instead of Python hash():
    - Python's hash() is salted with PYTHONHASHSEED (randomized per process)
    - SHA256 is cryptographically stable across runs, machines, Python versions
    """

    def __init__(
        self,
        dim: int = 384,
        ngram_range: Tuple[int, int] = (3, 5),
        use_cache: bool = True,
        word_weight: float = 3.0,
    ):
        """
        Initialize hash embedding backend.

        Args:
            dim: Embedding dimension (default 384)
            ngram_range: Tuple of (min_n, max_n) for character n-grams
            use_cache: Whether to use in-memory cache
            word_weight: Weight multiplier for word features (default 3.0)
        """
        self._dim = dim
        self.ngram_range = ngram_range
        self.use_cache = use_cache
        self.word_weight = word_weight

        # In-memory cache: normalized_text_hash -> vector
        self._cache: dict = {}
        self.cache_hits = 0
        self.cache_misses = 0

    @property
    def dim(self) -> int:
        return self._dim

    def _extract_features(self, text: str) -> List[Tuple[str, float]]:
        """
        Extract features from normalized text.

        Returns list of (feature, weight) tuples.
        """
        normalized = normalize_text(text)
        features = []

        # Character n-grams (weight 1.0)
        min_n, max_n = self.ngram_range
        for n in range(min_n, max_n + 1):
            for i in range(len(normalized) - n + 1):
                ngram = normalized[i:i + n]
                features.append((f"c:{ngram}", 1.0))

        # Word unigrams (higher weight for semantic signal)
        words = normalized.split()
        for word in words:
            if len(word) >= 2:  # Skip single chars
                features.append((f"w:{word}", self.word_weight))

        # Word bigrams for phrase-level signal
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            features.append((f"wb:{bigram}", self.word_weight * 0.5))

        return features

    def _extract_ngrams(self, text: str) -> List[str]:
        """Extract character n-grams from normalized text (legacy method)."""
        normalized = normalize_text(text)
        ngrams = []
        min_n, max_n = self.ngram_range

        for n in range(min_n, max_n + 1):
            for i in range(len(normalized) - n + 1):
                ngrams.append(normalized[i:i + n])

        return ngrams

    def _hash_to_index_and_sign(self, feature: str) -> Tuple[int, int]:
        """
        Hash a feature string to (index, sign) using SHA256.

        Uses first 8 bytes for index, 9th byte for sign.
        """
        h = hashlib.sha256(feature.encode("utf-8")).digest()

        # Use first 8 bytes for index (gives plenty of entropy)
        index_bytes = h[:8]
        index = int.from_bytes(index_bytes, "big") % self._dim

        # Use 9th byte for sign: even = +1, odd = -1
        sign = 1 if h[8] % 2 == 0 else -1

        return index, sign

    def _embed_single(self, text: str) -> Vector:
        """Embed a single text string."""
        # Check cache
        if self.use_cache:
            cache_key = text_hash(text)
            if cache_key in self._cache:
                self.cache_hits += 1
                return self._cache[cache_key]
            self.cache_misses += 1

        # Extract features (n-grams + words)
        features = self._extract_features(text)

        # Initialize zero vector
        vec = [0.0] * self._dim

        # Accumulate with signed hashing and weights
        for feature, weight in features:
            idx, sign = self._hash_to_index_and_sign(feature)
            vec[idx] += sign * weight

        # L2 normalize
        vec = l2_normalize(vec)

        # Cache result
        if self.use_cache:
            self._cache[cache_key] = vec

        return vec

    def embed_texts(self, texts: List[str]) -> Matrix:
        """
        Embed a list of texts into vectors.

        Args:
            texts: List of text strings

        Returns:
            Matrix of shape (len(texts), dim)
        """
        return [self._embed_single(text) for text in texts]

    def clear_cache(self) -> None:
        """Clear the in-memory cache and reset counters."""
        self._cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0


# =============================================================================
# OpenAIEmbeddingBackend (Optional, Dev-Only)
# =============================================================================

class OpenAIEmbeddingBackend(Embedder):
    """
    OpenAI embedding backend with disk cache.

    Only used if OPENAI_API_KEY is available.
    Caches embeddings to disk to avoid repeated API calls.

    Cache location: ~/.cache/fieldkit/embeddings/<model>/<sha256>.json
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize OpenAI embedding backend.

        Args:
            model: OpenAI embedding model name
            api_key: API key (defaults to OPENAI_API_KEY env var)
            cache_dir: Cache directory (defaults to ~/.cache/fieldkit/embeddings)
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

        # Determine embedding dimension based on model
        self._dim = self._get_model_dim(model)

        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "fieldkit" / "embeddings"
        self.cache_dir = cache_dir / model
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Stats
        self.cache_hits = 0
        self.cache_misses = 0

    @property
    def dim(self) -> int:
        return self._dim

    def _get_model_dim(self, model: str) -> int:
        """Get embedding dimension for a model."""
        dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dims.get(model, 1536)

    def _cache_path(self, text: str) -> Path:
        """Get cache file path for a text."""
        h = text_hash(text)
        return self.cache_dir / f"{h}.json"

    def _cache_get(self, text: str) -> Optional[Vector]:
        """
        Get cached embedding for text.

        Args:
            text: Input text

        Returns:
            Cached vector or None if not cached
        """
        path = self._cache_path(text)
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    return data.get("embedding")
            except (json.JSONDecodeError, KeyError):
                return None
        return None

    def _cache_put(self, text: str, vec: Vector) -> None:
        """
        Cache embedding for text.

        Args:
            text: Input text
            vec: Embedding vector
        """
        path = self._cache_path(text)
        data = {
            "text": text,
            "model": self.model,
            "embedding": vec,
        }
        with open(path, "w") as f:
            json.dump(data, f)

    def _call_api(self, texts: List[str]) -> Matrix:
        """
        Call OpenAI API to get embeddings.

        Raises clear error if openai library not available or key missing.
        """
        if not self.api_key:
            raise RuntimeError(
                "OpenAI API key not set. Set OPENAI_API_KEY environment variable "
                "or pass api_key to OpenAIEmbeddingBackend."
            )

        try:
            import openai
        except ImportError:
            raise RuntimeError(
                "openai package not installed. Install with: pip install openai"
            )

        client = openai.OpenAI(api_key=self.api_key)

        response = client.embeddings.create(
            model=self.model,
            input=texts,
        )

        # Extract embeddings in order
        embeddings = [None] * len(texts)
        for item in response.data:
            embeddings[item.index] = item.embedding

        return embeddings

    def embed_texts(self, texts: List[str]) -> Matrix:
        """
        Embed texts, using cache where available.

        Args:
            texts: List of text strings

        Returns:
            Matrix of shape (len(texts), dim)
        """
        results = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached = self._cache_get(text)
            if cached is not None:
                results[i] = cached
                self.cache_hits += 1
            else:
                texts_to_embed.append(text)
                indices_to_embed.append(i)
                self.cache_misses += 1

        # Call API for uncached texts
        if texts_to_embed:
            new_embeddings = self._call_api(texts_to_embed)

            for idx, text, vec in zip(indices_to_embed, texts_to_embed, new_embeddings):
                results[idx] = vec
                self._cache_put(text, vec)

        return results


# =============================================================================
# Default Embedder Factory
# =============================================================================

def get_default_embedder() -> Embedder:
    """
    Get the default embedder based on environment.

    Returns:
        OpenAIEmbeddingBackend if OPENAI_API_KEY is set
        HashEmbeddingBackend otherwise
    """
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIEmbeddingBackend()
    else:
        return HashEmbeddingBackend()


def get_hash_embedder(dim: int = 384) -> HashEmbeddingBackend:
    """
    Get a HashEmbeddingBackend with specified dimension.

    Convenience function for tests.

    Args:
        dim: Embedding dimension

    Returns:
        HashEmbeddingBackend instance
    """
    return HashEmbeddingBackend(dim=dim)
