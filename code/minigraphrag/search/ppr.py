"""Personalized PageRank retrieval (HippoRAG).

HippoRAG treats the entity graph like the hippocampus's associative index:
the query "activates" a few entities, and activation spreads along edges.
Personalized PageRank is that spreading process. A random walker starts at a
seed entity; at each step it follows an edge with probability `alpha` or jumps
back to a seed with probability `1 - alpha`. The stationary distribution
concentrates on nodes that are close to *several* seeds, which is exactly
what a multi-hop question needs. Passages are then ranked by the total PPR mass
of the entities they mention.
"""

from __future__ import annotations

import re

import networkx as nx
import numpy as np

from ..context import format_table
from ..llm import LLM, parse_json_response
from .. import prompts as P
from ..tokens import count_tokens
from .common import DEFAULT_RESPONSE_TYPE, SearchResult, doc_ids_for_units, generate_answer


def personalized_pagerank(G: nx.Graph, seeds: dict[str, float], alpha: float = 0.85, iters: int = 50,
                          tol: float = 1e-10, weight: str = "weight") -> dict[str, float]:
    """Power iteration: p <- (1 - alpha) * s + alpha * (M p + dangling mass * s)."""
    nodes = list(G.nodes())
    if not nodes:
        return {}
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    s = np.zeros(n)
    for node, w in seeds.items():
        if node in idx:
            s[idx[node]] += max(w, 0.0)
    s = s / s.sum() if s.sum() > 0 else np.full(n, 1.0 / n)  # no valid seeds: plain PageRank

    # Column-stochastic transition matrix: M[i, j] = P(step j -> i).
    W = np.zeros((n, n))
    for u, v, d in G.edges(data=True):
        w = float(d.get(weight, 1.0))
        W[idx[v], idx[u]] += w
        if u != v:
            W[idx[u], idx[v]] += w
    out = W.sum(axis=0)
    dangling = out == 0  # nodes with no edges: their walker teleports back to the seeds
    M = W / np.where(dangling, 1.0, out)

    p = s.copy()
    for _ in range(iters):
        new = (1 - alpha) * s + alpha * (M @ p + p[dangling].sum() * s)
        if np.abs(new - p).sum() < tol:
            p = new
            break
        p = new
    return {node: float(p[i]) for node, i in idx.items()}


def link_query_to_nodes(index, query: str, llm: LLM | None = None, top_k: int = 5) -> dict[str, float]:
    """Seed weights for PPR: query entities linked to graph nodes.

    HippoRAG runs NER on the query with an LLM; we use the keyword prompt when
    an LLM is given, plus literal name/alias matches, plus embedding matches.
    Seeds are weighted by *node specificity* (1 / number of passages mentioning
    the node) so that hubs like "KESTREL LABS" don't drown out rarer entities.
    """
    G = index.graph
    scores: dict[str, float] = {}
    q = query.upper()
    for n, d in G.nodes(data=True):
        if any(re.search(rf"(?<!\w){re.escape(s)}(?!\w)", q) for s in [n, *d.get("aliases", [])]):
            scores[n] = 1.0
    phrases = []
    if llm is not None:
        data = parse_json_response(llm.complete(P.KEYWORD_EXTRACTION_PROMPT.format(query=query), json=True))
        phrases = [str(k) for k in data.get("low_level_keywords", [])]
    for phrase in phrases or [query]:
        for name, sim, _ in index.entity_store.search(index.embedder.embed([phrase])[0], k=1 if phrases else top_k):
            scores[name] = max(scores.get(name, 0.0), sim)
    top = dict(sorted(scores.items(), key=lambda x: -x[1])[:top_k])
    return {n: w / max(1, len(G.nodes[n].get("source_ids", []))) for n, w in top.items() if w > 0}


def rank_passages(index, node_scores: dict[str, float]) -> list[tuple[str, float]]:
    """Score each text unit by the summed PPR score of the entities extracted from it."""
    totals: dict[str, float] = {}
    for n, score in node_scores.items():
        for uid in index.graph.nodes[n].get("source_ids", []):
            totals[uid] = totals.get(uid, 0.0) + score
    return sorted(totals.items(), key=lambda x: (-x[1], x[0]))


def hipporag_search(index, query: str, llm: LLM, top_k_passages: int = 5, alpha: float = 0.85,
                    max_context_tokens: int = 4000, response_type: str = DEFAULT_RESPONSE_TYPE) -> SearchResult:
    seeds = link_query_to_nodes(index, query, llm)
    ppr = personalized_pagerank(index.graph, seeds, alpha=alpha)
    rows, used = [], 0
    for uid, score in rank_passages(index, ppr)[:top_k_passages]:
        text = index.text_units[uid].text
        if used + count_tokens(text) > max_context_tokens:
            break
        rows.append([uid, text])
        used += count_tokens(text)
    top_nodes = sorted(ppr.items(), key=lambda x: -x[1])[:10]
    context = format_table("Sources", ["id", "text"], rows)
    answer = generate_answer(llm, query, context, response_type)
    return SearchResult(answer, "ppr", context,
                        {"seeds": seeds, "top_nodes": top_nodes, "sources": [{"id": r[0], "text": r[1]} for r in rows]},
                        doc_ids_for_units(index, [r[0] for r in rows]), llm_calls=2)
