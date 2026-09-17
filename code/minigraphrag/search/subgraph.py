"""Query-specific subgraph retrieval (G-Retriever style).

G-Retriever gives every node a *prize* (high if similar to the query) and every
edge a *cost*, then solves the Prize-Collecting Steiner Tree problem: find a
connected subgraph maximising total prize minus total cost. The result is a
small, connected piece of the graph that links the relevant entities, including
"bridge" nodes that aren't similar to the query themselves.

Exact PCST is NP-hard; G-Retriever uses a fast Goemans-Williamson style solver.
`pcst_subgraph` is a simple *greedy approximation* for teaching:
1. start from the highest-prize node;
2. repeatedly attach the prize node whose shortest connecting path has the best
   positive net gain (new prizes - path edge costs);
3. prune leaves whose prize is below the cost of the edge holding them.
"""

from __future__ import annotations

import networkx as nx

from ..context import format_table
from ..llm import LLM
from .common import DEFAULT_RESPONSE_TYPE, SearchResult, doc_ids_for_units, generate_answer


def similarity_prizes(index, query: str, top_k: int = 10) -> dict[str, float]:
    """Rank-based prizes like G-Retriever: the i-th most similar entity gets prize top_k - i."""
    hits = index.entity_store.search(index.embedder.embed([query])[0], k=top_k)
    return {name: float(top_k - i) for i, (name, _, _) in enumerate(hits)}


def pcst_subgraph(G: nx.Graph, prizes: dict[str, float], edge_cost: float = 1.0, max_nodes: int = 20) -> nx.Graph:
    """Greedy prize-collecting Steiner tree approximation. Returns the selected subgraph (a copy)."""
    candidates = {n: p for n, p in prizes.items() if n in G and p > 0}
    if not candidates:
        return nx.Graph()
    tree = {max(candidates, key=lambda n: (candidates[n], n))}
    tree_edges: set[tuple[str, str]] = set()

    while len(tree) < max_nodes:
        paths = nx.multi_source_dijkstra_path(G, tree)  # shortest path from the tree to every node
        best, best_gain = None, 0.0
        for node, prize in candidates.items():
            if node in tree or node not in paths:
                continue
            path = paths[node]
            new_nodes = [n for n in path if n not in tree]
            gain = sum(prizes.get(n, 0.0) for n in new_nodes) - edge_cost * (len(path) - 1)
            if gain > best_gain and len(tree) + len(new_nodes) <= max_nodes:
                best, best_gain = path, gain
        if best is None:
            break
        tree.update(best)
        tree_edges.update(tuple(sorted(e)) for e in zip(best, best[1:]))

    # Strong pruning: a leaf that costs more to keep than it earns is removed.
    changed = True
    while changed and len(tree) > 1:
        changed = False
        degree = {n: 0 for n in tree}
        for u, v in tree_edges:
            degree[u] += 1
            degree[v] += 1
        for n in list(tree):
            if degree[n] == 1 and prizes.get(n, 0.0) < edge_cost:
                tree.discard(n)
                tree_edges = {e for e in tree_edges if n not in e}
                changed = True

    sub = nx.Graph()
    sub.add_nodes_from((n, G.nodes[n]) for n in tree)
    sub.add_edges_from((u, v, G.edges[u, v]) for u, v in tree_edges)
    return sub


def subgraph_search(index, query: str, llm: LLM, top_k: int = 10, edge_cost: float = 1.0,
                    response_type: str = DEFAULT_RESPONSE_TYPE) -> SearchResult:
    """Retrieve a PCST subgraph and answer from its markdown tables."""
    sub = pcst_subgraph(index.graph, similarity_prizes(index, query, top_k), edge_cost)
    context = "\n\n".join([
        format_table("Entities", ["id", "entity", "description"],
                     [[d.get("human_id"), n, d.get("description", "")] for n, d in sub.nodes(data=True)]),
        format_table("Relationships", ["id", "source", "target", "description"],
                     [[d.get("human_id"), u, v, d.get("description", "")] for u, v, d in sub.edges(data=True)]),
    ])
    units = [u for n in sub.nodes for u in sub.nodes[n].get("source_ids", [])]
    answer = generate_answer(llm, query, context, response_type)
    return SearchResult(answer, "subgraph", context, {"nodes": list(sub.nodes), "edges": list(sub.edges)},
                        doc_ids_for_units(index, units), llm_calls=1)
