import networkx as nx
import pytest

from minigraphrag.search.paths import find_relational_paths, k_shortest_paths, paths_to_text
from minigraphrag.search.ppr import personalized_pagerank, rank_passages
from minigraphrag.search.subgraph import pcst_subgraph, similarity_prizes


def test_ppr_sums_to_one_and_favours_seeds():
    G = nx.cycle_graph(10)
    scores = personalized_pagerank(G, {0: 1.0})
    assert sum(scores.values()) == pytest.approx(1.0)
    assert max(scores, key=scores.get) == 0
    assert scores[1] > scores[3] > scores[5]


def test_ppr_matches_networkx_and_handles_dangling_nodes():
    G = nx.karate_club_graph()
    G.add_node("isolated")
    ours = personalized_pagerank(G, {0: 1.0, 33: 1.0}, alpha=0.85, iters=200, weight=None)
    from networkx.algorithms.link_analysis.pagerank_alg import _pagerank_python  # no scipy needed

    ref = _pagerank_python(G, alpha=0.85, personalization={0: 1, 33: 1}, dangling={0: 1, 33: 1}, weight=None,
                           tol=1e-12, max_iter=500)
    for n in G:
        assert ours[n] == pytest.approx(ref[n], abs=1e-6)
    assert sum(ours.values()) == pytest.approx(1.0)


def test_ppr_bridges_two_seeds(index):
    scores = personalized_pagerank(index.graph, {"PRIYA NAIR": 1.0, "DEEPCAST": 1.0})
    passages = rank_passages(index, scores)
    assert passages and passages[0][1] >= passages[-1][1]


def test_paths_priya_to_deepcast(index):
    G = index.graph
    assert k_shortest_paths(G, "PRIYA NAIR", "DEEPCAST", k=3)
    paths = find_relational_paths(G, ["PRIYA NAIR"], ["DEEPCAST"], max_hops=3)
    assert paths and all(p[0] == "PRIYA NAIR" and p[-1] == "DEEPCAST" for p, _ in paths)
    scores = [s for _, s in paths]
    assert scores == sorted(scores, reverse=True)
    assert "--[" in paths_to_text(G, paths[:2])


def test_flow_pruning_limits_paths():
    G = nx.star_graph(50)  # hub 0 dilutes its flow across 50 neighbours
    nx.relabel_nodes(G, str, copy=False)
    G.add_edge("1", "x")
    G.add_edge("x", "2")
    loose = find_relational_paths(G, ["1"], ["2"], max_hops=3, threshold=0.0)
    strict = find_relational_paths(G, ["1"], ["2"], max_hops=3, threshold=0.05)
    assert len(strict) <= len(loose)
    assert strict[0][0] == ["1", "x", "2"]


def test_pcst_connects_prized_nodes():
    G = nx.path_graph(["a", "b", "c", "d", "e"])
    G.add_edge("a", "z")
    sub = pcst_subgraph(G, {"a": 5.0, "d": 5.0, "z": 0.1}, edge_cost=1.0)
    assert {"a", "b", "c", "d"} <= set(sub.nodes) and "z" not in sub.nodes and "e" not in sub.nodes
    assert nx.is_connected(sub)


def test_pcst_on_index(index):
    prizes = similarity_prizes(index, "Marlow Dynamics acquired Deepcast", top_k=5)
    sub = pcst_subgraph(index.graph, prizes)
    assert sub.number_of_nodes() >= 1 and nx.is_connected(sub)
