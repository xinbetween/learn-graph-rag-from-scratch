"""Community detection: Louvain from scratch, plus a hierarchy.

Global questions ("what are the main themes?") can't be answered from any
single chunk. GraphRAG's answer is to partition the entity graph into
communities of densely connected entities, summarise each, and reason over the
summaries. The partition quality measure is *modularity*:

    Q = sum over communities c of [ L_c / m  -  gamma * (d_c / 2m)^2 ]

L_c = weight of edges inside c, d_c = total degree of c, m = total edge weight.
The first term is "how much of the graph's weight is inside c", the second is
what you'd expect by chance given the degrees. Q > 0.3 usually means real structure.

Louvain greedily maximises Q in two repeating phases:
1. local moving: move each node to the neighbouring community with the best
   modularity gain until nothing improves;
2. aggregation: collapse each community into a single super-node and repeat.

GraphRAG uses hierarchical Leiden (a refinement of Louvain that guarantees
connected communities). We use graspologic's implementation when installed.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field, asdict

import networkx as nx


@dataclass
class Community:
    id: int
    level: int
    parent: int | None
    nodes: list[str]
    edges: list[tuple[str, str]]
    children: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def modularity(G: nx.Graph, partition: list[set], resolution: float = 1.0, weight: str = "weight") -> float:
    """Newman modularity of `partition` (a list of node sets covering G)."""
    m = G.size(weight=weight)
    if m == 0:
        return 0.0
    q = 0.0
    for community in partition:
        inside = G.subgraph(community).size(weight=weight)
        degree = sum(d for _, d in G.degree(community, weight=weight))
        q += inside / m - resolution * (degree / (2 * m)) ** 2
    return q


def _one_level(adj: dict, resolution: float, rng: random.Random) -> tuple[dict, bool]:
    """Phase 1 (local moving) on an adjacency dict {node: {nbr: weight}} that may contain self-loops."""
    # Self-loops count twice toward degree (both "ends" are on the node).
    k = {u: sum(w for v, w in nbrs.items() if v != u) + 2 * nbrs.get(u, 0.0) for u, nbrs in adj.items()}
    m = sum(k.values()) / 2
    node2com = {u: u for u in adj}
    sigma_tot = dict(k)  # total degree of each community
    improved = False
    nodes = list(adj)
    rng.shuffle(nodes)  # visiting order changes the result; the seed makes it reproducible

    moved = True
    while moved:
        moved = False
        for u in nodes:
            ku, current = k[u], node2com[u]
            # Weight from u into each neighbouring community.
            w2c: dict = defaultdict(float)
            for v, w in adj[u].items():
                if v != u:
                    w2c[node2com[v]] += w
            # Take u out of its community first...
            sigma_tot[current] -= ku
            # ...then the gain of inserting u into community C is
            #   k_{u,in}(C) / m  -  gamma * sigma_tot(C) * k_u / (2 m^2)
            best, best_gain = current, w2c[current] / m - resolution * sigma_tot[current] * ku / (2 * m * m)
            for com, w in sorted(w2c.items(), key=lambda x: str(x[0])):
                gain = w / m - resolution * sigma_tot[com] * ku / (2 * m * m)
                if gain > best_gain + 1e-12:
                    best, best_gain = com, gain
            sigma_tot[best] += ku
            if best != current:
                node2com[u] = best
                moved = improved = True
    return node2com, improved


def _aggregate(adj: dict, node2com: dict) -> dict:
    """Phase 2: build the graph whose nodes are communities. Internal weight becomes a self-loop."""
    new: dict = defaultdict(lambda: defaultdict(float))
    for u, nbrs in adj.items():
        cu = node2com[u]
        new[cu]  # make sure isolated communities survive
        for v, w in nbrs.items():
            cv = node2com[v]
            if u == v:
                new[cu][cu] += w
            elif cu == cv:
                new[cu][cu] += w / 2  # each internal edge is seen from both ends
            else:
                new[cu][cv] += w
    return {u: dict(nbrs) for u, nbrs in new.items()}


def louvain_communities(G: nx.Graph, resolution: float = 1.0, seed: int = 42, weight: str = "weight") -> list[set]:
    """Partition G with the Louvain method. Returns a list of node sets, largest first."""
    if G.number_of_edges() == 0:
        return [{n} for n in G.nodes()]
    rng = random.Random(seed)
    adj = {u: {} for u in G.nodes()}
    for u, v, d in G.edges(data=True):
        w = float(d.get(weight, 1.0))
        adj[u][v] = adj[u].get(v, 0.0) + w
        if u != v:
            adj[v][u] = adj[v].get(u, 0.0) + w
    membership = {n: n for n in G.nodes()}  # original node -> current super-node

    while True:
        node2com, improved = _one_level(adj, resolution, rng)
        if not improved:
            break
        membership = {n: node2com[c] for n, c in membership.items()}
        adj = _aggregate(adj, node2com)

    groups: dict = defaultdict(set)
    for n, c in membership.items():
        groups[c].add(n)
    return sorted(groups.values(), key=lambda s: (-len(s), sorted(map(str, s))))


def _leiden_hierarchy(G: nx.Graph, max_cluster_size: int, seed: int) -> list[Community] | None:
    try:
        from graspologic.partition import hierarchical_leiden
    except ImportError:
        return None
    clusters = hierarchical_leiden(G, max_cluster_size=max_cluster_size, random_seed=seed)
    by_id: dict[int, dict] = {}
    for c in clusters:
        entry = by_id.setdefault(c.cluster, {"level": c.level, "parent": c.parent_cluster, "nodes": []})
        entry["nodes"].append(c.node)
    communities = [
        Community(cid, e["level"], e["parent"], sorted(e["nodes"]),
                  sorted(tuple(sorted(x)) for x in G.subgraph(e["nodes"]).edges()))
        for cid, e in sorted(by_id.items())
    ]
    index = {c.id: c for c in communities}
    for c in communities:
        if c.parent is not None and c.parent in index:
            index[c.parent].children.append(c.id)
    return communities


def hierarchical_communities(
    G: nx.Graph, max_cluster_size: int = 10, seed: int = 42, use_leiden: bool | None = None
) -> list[Community]:
    """Recursive partition: any community larger than `max_cluster_size` is split again one level down.

    Level 0 is the coarsest partition. Uses graspologic's hierarchical Leiden
    if installed (or `use_leiden=True`), otherwise recursive Louvain.
    """
    if use_leiden is not False:
        result = _leiden_hierarchy(G, max_cluster_size, seed)
        if result is not None:
            return result
        if use_leiden:
            raise ImportError("graspologic is not installed (pip install minigraphrag[leiden])")

    communities: list[Community] = []

    def recurse(nodes: set, level: int, parent: int | None) -> None:
        parts = louvain_communities(G.subgraph(nodes), seed=seed)
        if parent is not None and len(parts) <= 1:
            return  # Louvain can't split it further; stop here
        for part in parts:
            c = Community(len(communities), level, parent, sorted(part),
                          sorted(tuple(sorted(e)) for e in G.subgraph(part).edges()))
            communities.append(c)
            if parent is not None:
                communities[parent].children.append(c.id)
            if len(part) > max_cluster_size:
                recurse(set(part), level + 1, c.id)

    recurse(set(G.nodes()), 0, None)
    return communities
