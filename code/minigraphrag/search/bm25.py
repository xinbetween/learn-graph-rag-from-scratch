"""BM25 keyword ranking, from scratch.

Dense embeddings miss exact identifiers ("Series B", "RN-2024-07", rare names);
BM25 nails them. Score of document d for query q:

    sum over terms t in q of  IDF(t) * tf(t,d) * (k1 + 1) / (tf(t,d) + k1 * (1 - b + b * |d| / avgdl))

- IDF rewards rare terms; tf saturates (the 10th occurrence adds little, via k1);
- b normalises for document length (long documents match everything a bit).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable

import numpy as np

from ..embeddings import simple_tokenize


def tokenize(text: str) -> list[str]:
    return simple_tokenize(text)


class BM25:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75,
                 tokenizer: Callable[[str], list[str]] = tokenize):
        self.k1, self.b, self.tokenizer = k1, b, tokenizer
        self.doc_tfs = [Counter(tokenizer(d)) for d in documents]
        self.doc_lens = np.array([sum(tf.values()) for tf in self.doc_tfs], dtype=float)
        self.avgdl = float(self.doc_lens.mean()) if len(documents) else 0.0
        df = Counter(t for tf in self.doc_tfs for t in tf)
        n = len(documents)
        # The +1 inside the log keeps IDF positive even for terms in most documents.
        self.idf = {t: math.log((n - f + 0.5) / (f + 0.5) + 1) for t, f in df.items()}

    def get_scores(self, query: str) -> np.ndarray:
        scores = np.zeros(len(self.doc_tfs))
        for term in set(self.tokenizer(query)):
            if term not in self.idf:
                continue
            tf = np.array([d.get(term, 0) for d in self.doc_tfs], dtype=float)
            norm = self.k1 * (1 - self.b + self.b * self.doc_lens / (self.avgdl or 1))
            scores += self.idf[term] * tf * (self.k1 + 1) / (tf + norm)
        return scores

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        """(document index, score) pairs, best first; zero-score documents are omitted."""
        scores = self.get_scores(query)
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [(int(i), float(scores[i])) for i in order if scores[i] > 0]
