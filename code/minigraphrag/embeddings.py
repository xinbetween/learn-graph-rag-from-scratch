"""Embedding text into vectors.

Several steps need "semantic" lookup: mapping a query to entity descriptions
(local search), to relationships (LightRAG), to passages (baseline RAG). All we
need from an embedder is `embed(texts) -> (n, d)` array of unit vectors, so the
rest of the code never cares which model produced them.

`HashingEmbedder` is the offline stand-in: it hashes words into a fixed number
of buckets (the "hashing trick"). It captures lexical overlap only, not
meaning, but it is deterministic, needs no download, and is good enough to make
every retrieval algorithm in this package observable.
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol, Sequence

import numpy as np

STOPWORDS = frozenset(
    """a an and are as at be been but by did do does for from had has have he her his how i in into is it its
    of on or our she that the their them they this to was we were what when where which who whom why will with
    you your not than then there these those about after before can could would should also more most""".split()
)


def simple_tokenize(text: str) -> list[str]:
    """Lowercase words minus stopwords, with a crude plural strip ("drones" -> "drone")."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = []
    for w in words:
        if w in STOPWORDS:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


class Embedder(Protocol):
    def embed(self, texts: Sequence[str]) -> np.ndarray: ...


class HashingEmbedder:
    """Deterministic bag-of-words hashing embedder (offline)."""

    def __init__(self, dim: int = 512):
        self.dim = dim
        self.name = f"hashing:{dim}"

    def _bucket(self, token: str) -> tuple[int, float]:
        # Python's hash() is randomised per process, so use a stable digest.
        h = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "little")
        return h % self.dim, 1.0 if (h >> 63) & 1 else -1.0  # sign reduces collision bias

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        mat = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for tok in simple_tokenize(text):
                idx, sign = self._bucket(tok)
                mat[row, idx] += sign
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        return mat / np.where(norms == 0, 1.0, norms)


class OpenAIEmbedder:
    """OpenAI (or compatible) embeddings API. Requires the `openai` extra."""

    def __init__(self, model: str = "text-embedding-3-small", base_url: str | None = None, api_key: str | None = None):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.name = f"openai:{model}"

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        resp = self.client.embeddings.create(model=self.model, input=list(texts))
        mat = np.array([d.embedding for d in resp.data], dtype=np.float32)
        return mat / np.linalg.norm(mat, axis=1, keepdims=True)


class SentenceTransformerEmbedder:
    """Local neural embeddings via sentence-transformers. Requires the `st` extra."""

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model)
        self.name = f"st:{model}"

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        return np.asarray(self.model.encode(list(texts), normalize_embeddings=True), dtype=np.float32)


def get_embedder(name: str = "hashing") -> Embedder:
    """Build an embedder from a short spec: 'hashing', 'hashing:256', 'openai', 'st:<model>'."""
    kind, _, arg = name.partition(":")
    if kind == "hashing":
        return HashingEmbedder(int(arg) if arg else 512)
    if kind == "openai":
        return OpenAIEmbedder(arg or "text-embedding-3-small")
    if kind == "st":
        return SentenceTransformerEmbedder(arg or "all-MiniLM-L6-v2")
    raise ValueError(f"unknown embedder {name!r}")


def cosine_top_k(query_vec: np.ndarray, matrix: np.ndarray, k: int = 5) -> list[tuple[int, float]]:
    """Indices and cosine scores of the k rows of `matrix` most similar to `query_vec`.

    Vectors are assumed L2-normalised, so cosine similarity is a dot product.
    """
    if matrix.size == 0:
        return []
    scores = matrix @ query_vec.reshape(-1)
    k = min(k, len(scores))
    top = np.argpartition(-scores, k - 1)[:k]
    top = top[np.argsort(-scores[top], kind="stable")]
    return [(int(i), float(scores[i])) for i in top]
