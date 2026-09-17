"""A tiny in-memory vector store.

Production systems use FAISS, LanceDB, pgvector, etc. The interface they share
is small: add (id, vector, metadata), search by vector, persist. Brute-force
cosine over a numpy matrix is exact and plenty fast for thousands of rows.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .embeddings import cosine_top_k


class VectorStore:
    def __init__(self, dim: int | None = None):
        self.ids: list[str] = []
        self.metadata: list[dict] = []
        self.matrix = np.zeros((0, dim or 0), dtype=np.float32)

    def __len__(self) -> int:
        return len(self.ids)

    def add(self, ids: list[str], vectors: np.ndarray, metadata: list[dict] | None = None) -> None:
        vectors = np.asarray(vectors, dtype=np.float32)
        if len(ids) != len(vectors):
            raise ValueError("ids and vectors must have the same length")
        self.matrix = vectors if len(self.ids) == 0 else np.vstack([self.matrix, vectors])
        self.ids.extend(ids)
        self.metadata.extend(metadata or [{} for _ in ids])

    def search(self, query_vec: np.ndarray, k: int = 5) -> list[tuple[str, float, dict]]:
        """Return up to k (id, score, metadata) tuples, best first."""
        return [(self.ids[i], s, self.metadata[i]) for i, s in cosine_top_k(query_vec, self.matrix, k)]

    def save(self, path: str | Path) -> None:
        """Write `<path>.npz` (vectors) and `<path>.json` (ids + metadata)."""
        path = Path(path)
        np.savez_compressed(path.with_suffix(".npz"), matrix=self.matrix)
        path.with_suffix(".json").write_text(json.dumps({"ids": self.ids, "metadata": self.metadata}))

    @classmethod
    def load(cls, path: str | Path) -> "VectorStore":
        path = Path(path)
        store = cls()
        store.matrix = np.load(path.with_suffix(".npz"))["matrix"]
        data = json.loads(path.with_suffix(".json").read_text())
        store.ids, store.metadata = data["ids"], data["metadata"]
        return store
