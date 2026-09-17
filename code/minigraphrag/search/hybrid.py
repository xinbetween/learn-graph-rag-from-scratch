"""Hybrid retrieval with Reciprocal Rank Fusion.

Keyword search (BM25), dense vectors and graph traversal fail on different
questions, so production systems run several retrievers and fuse the results.
Scores from different retrievers aren't comparable (BM25 ~ 7.3, cosine ~ 0.4),
so RRF ignores scores and uses only ranks:

    RRF(d) = sum over retrievers r of  weight_r / (k + rank_r(d))

k = 60 (from the original paper) damps the advantage of being ranked #1, so a
document that is decent in every list beats one that is top in only one.
"""

from __future__ import annotations

from ..context import format_table
from ..llm import LLM
from ..tokens import count_tokens
from .bm25 import BM25
from .common import DEFAULT_RESPONSE_TYPE, SearchResult, doc_ids_for_units, generate_answer
from .ppr import link_query_to_nodes, personalized_pagerank, rank_passages


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60, weights: list[float] | None = None) -> list[tuple[str, float]]:
    """Fuse several ranked id lists (best first). Returns (id, fused score), best first."""
    weights = weights or [1.0] * len(rankings)
    scores: dict[str, float] = {}
    for ranking, w in zip(rankings, weights):
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + w / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def hybrid_search(index, query: str, llm: LLM, top_k: int = 5, rrf_k: int = 60, candidates: int = 20,
                  max_context_tokens: int = 4000, response_type: str = DEFAULT_RESPONSE_TYPE) -> SearchResult:
    """Fuse BM25, vector and PPR-graph rankings of text units, then answer."""
    unit_ids = list(index.text_units)
    bm25 = BM25([index.text_units[u].text for u in unit_ids])
    keyword = [unit_ids[i] for i, _ in bm25.search(query, candidates)]
    vector = [uid for uid, _, _ in index.text_unit_store.search(index.embedder.embed([query])[0], k=candidates)]
    ppr = personalized_pagerank(index.graph, link_query_to_nodes(index, query))
    graph = [uid for uid, _ in rank_passages(index, ppr)[:candidates]]

    fused = reciprocal_rank_fusion([keyword, vector, graph], k=rrf_k)
    rows, used = [], 0
    for uid, score in fused[:top_k]:
        text = index.text_units[uid].text
        if used + count_tokens(text) > max_context_tokens:
            break
        rows.append([uid, text])
        used += count_tokens(text)
    context = format_table("Sources", ["id", "text"], rows)
    answer = generate_answer(llm, query, context, response_type)
    data = {"rankings": {"bm25": keyword, "vector": vector, "graph": graph}, "fused": fused[:top_k],
            "sources": [{"id": r[0], "text": r[1]} for r in rows]}
    return SearchResult(answer, "hybrid", context, data, doc_ids_for_units(index, [r[0] for r in rows]), llm_calls=1)
