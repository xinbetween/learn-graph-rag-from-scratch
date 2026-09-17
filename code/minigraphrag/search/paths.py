"""Relational paths between entities (PathRAG-style).

"What connects Priya Nair to Deepcast?" is literally a path question:
PRIYA NAIR - MARLOW DYNAMICS - DEEPCAST. Enumerating all paths explodes
combinatorially, so PathRAG prunes with a *flow* model: each source starts
with 1 unit of resource that spreads to neighbours, divided by the node's
degree and multiplied by a decay factor per hop. Nodes whose resource drops
below a threshold are not expanded. Paths through well-supplied nodes score
highest; hubs dilute their flow, so paths don't all route through them.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import islice

import networkx as nx


def k_shortest_paths(G: nx.Graph, source: str, target: str, k: int = 3, weight: str | None = None) -> list[list[str]]:
    """The k shortest simple paths (Yen's algorithm via networkx)."""
    try:
        return list(islice(nx.shortest_simple_paths(G, source, target, weight=weight), k))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def _flow_from(G: nx.Graph, source: str, max_hops: int, decay: float,
               threshold: float) -> tuple[dict[str, float], set[str]]:
    """Resource reaching each node when spreading hop by hop from `source`, and the nodes that were expanded."""
    flow = {source: 1.0}
    frontier = {source: 1.0}
    expanded: set[str] = set()
    for _ in range(max_hops):
        nxt: dict[str, float] = defaultdict(float)
        for v, resource in frontier.items():
            share = decay * resource / max(1, G.degree(v))
            if share < threshold:
                continue  # pruned: too little resource left to be worth following
            expanded.add(v)
            for u in G.neighbors(v):
                if u not in flow:
                    nxt[u] += share
        flow.update(nxt)
        frontier = nxt
    return flow, expanded


def find_relational_paths(G: nx.Graph, sources: list[str], targets: list[str], max_hops: int = 3,
                          decay: float = 0.8, threshold: float = 0.02, top_k: int = 10) -> list[tuple[list[str], float]]:
    """Scored simple paths from any source to any target, best first.

    Score = average flow of the nodes after the source (PathRAG's reliability).
    """
    results: list[tuple[list[str], float]] = []
    targets_set = set(targets)
    for s in sources:
        if s not in G:
            continue
        flow, expanded = _flow_from(G, s, max_hops, decay, threshold)

        def dfs(path: list[str]) -> None:
            node = path[-1]
            if node in targets_set and len(path) > 1:
                results.append((list(path), sum(flow[n] for n in path[1:]) / (len(path) - 1)))
                return
            if len(path) > max_hops or node not in expanded:
                return  # hop limit reached, or this node's flow was pruned
            for nbr in sorted(G.neighbors(node)):
                if nbr in flow and nbr not in path:
                    dfs(path + [nbr])

        dfs([s])
    results.sort(key=lambda x: (-x[1], len(x[0])))
    return results[:top_k]


def paths_to_text(G: nx.Graph, paths: list) -> str:
    """Render paths as narrated chains, e.g. `A --[desc]--> B --[desc]--> C`."""
    lines = []
    for item in paths:
        path, score = (item, None) if isinstance(item[0], str) else item
        hops = [path[0]]
        for u, v in zip(path, path[1:]):
            desc = G.edges[u, v].get("description", "related to")
            hops.append(f" --[{desc[:200]}]--> {v}")
        lines.append("".join(hops) + (f"  (score {score:.3f})" if score is not None else ""))
    return "\n".join(lines)
