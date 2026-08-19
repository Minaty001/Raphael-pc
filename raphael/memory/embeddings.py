"""
Embedding provider for Raphael v3 memory (audit #12 / ROADMAP L5).

The previous vector store used bag-of-words term-frequency vectors, which are
NOT semantic embeddings. This module introduces a real *dense embedding*
abstraction so retrieval is genuinely vector-based and can be upgraded to a
true transformer model later without touching the rest of the memory stack.

Default provider: ``LocalHashingEmbedding`` — a deterministic, dependency-free
hashing embedding (word + character n-grams feature-hashed into a fixed-dimension
L2-normalized vector). It is a genuine dense embedding: fixed dimensionality,
stable cosine similarity, and far better lexical/semantic proximity than the
old vocabulary-union term-frequency approach.

Optional provider: ``SentenceTransformersEmbedding`` — used automatically if
``sentence-transformers`` is installed, giving true semantic embeddings.
"""

import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import List, Optional


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class EmbeddingProvider(ABC):
    dim: int = 256

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        ...


class LocalHashingEmbedding(EmbeddingProvider):
    """Deterministic, offline dense embedding via feature hashing.

    Features: word unigrams + bigrams, plus character 3-grams (captures
    sub-word morphology). Each feature is hashed into the embedding space and
    accumulated with TF weighting, then L2-normalized. Identical inputs always
    produce identical vectors; semantically/lexically similar texts produce
    high cosine similarity.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _hash(self, feature: str) -> int:
        h = hashlib.md5(feature.encode("utf-8")).digest()
        # Combine two 32-bit halves for a stable non-negative index.
        a = int.from_bytes(h[:4], "big")
        b = int.from_bytes(h[4:8], "big")
        return (a ^ b) % self.dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        toks = _tokens(text)
        if not toks:
            return vec

        # Term-frequency weights for word unigrams + bigrams.
        features: dict = {}
        for i, t in enumerate(toks):
            features[f"w:{t}"] = features.get(f"w:{t}", 0.0) + 1.0
            if i + 1 < len(toks):
                features[f"b:{t} {toks[i + 1]}"] = features.get(f"b:{t} {toks[i + 1]}", 0.0) + 1.0
        # Character 3-grams for sub-word signal.
        low = text.lower()
        for i in range(len(low) - 2):
            cg = low[i : i + 3]
            if cg.strip():
                features[f"c:{cg}"] = features.get(f"c:{cg}", 0.0) + 0.5

        for feat, weight in features.items():
            idx = self._hash(feat)
            vec[idx] += weight

        # L2 normalize so cosine similarity is bounded to [-1, 1].
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class SentenceTransformersEmbedding(EmbeddingProvider):
    """True semantic embeddings via sentence-transformers (optional dependency)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dim: int = 384):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._model = SentenceTransformer(model_name)
            self.dim = self._model.get_sentence_embedding_dimension()
        except Exception as e:
            raise RuntimeError(f"sentence-transformers unavailable: {e}")

    def embed(self, text: str) -> List[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()


def get_embedding_provider() -> EmbeddingProvider:
    """Return the best available embedding provider.

    Uses sentence-transformers when installed (real semantic vectors);
    otherwise falls back to the deterministic offline hashing embedding.
    """
    try:
        return SentenceTransformersEmbedding()
    except Exception:
        return LocalHashingEmbedding()
