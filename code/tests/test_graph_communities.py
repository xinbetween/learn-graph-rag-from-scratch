import networkx as nx
import pytest

from minigraphrag.communities import hierarchical_communities, louvain_communities, modularity
from minigraphrag.extraction import Entity, ExtractionResult, Relationship
from minigraphrag.graph_build import build_graph


def test_build_graph_merges_duplicates(llm):
    ex1 = ExtractionResult("u1", [Entity("DEEPCAST", "ORGANIZATION", "Sonar supplier", "u1"),
                                  Entity("KESTREL", "ORGANIZATION", "Startup", "u1")],
                           [Relationship("DEEPCAST", "KESTREL", "supplies sonar", 5, "u1")])
    ex2 = ExtractionResult("u2", [Entity("DEEPCAST", "ORGANIZATION", "Acquired by Marlow", "u2"),
                                  Entity("KESTREL LABS", "ORGANIZATION", "Drone company", "u2")],
                           [Relationship("KESTREL LABS", "DEEPCAST", "bought sonar from", 3, "u2"),
                            Relationship("KESTREL", "KESTREL LABS", "same thing", 9, "u2")])
    G = build_graph([ex1, ex2], name_map={"KESTREL": "KESTREL LABS"})
    assert set(G.nodes) == {"DEEPCAST", "KESTREL LABS"}
    assert G.nodes["DEEPCAST"]["descriptions"] == ["Sonar supplier", "Acquired by Marlow"]
    assert G.nodes["KESTREL LABS"]["aliases"] == ["KESTREL"]
    assert G.edges["DEEPCAST", "KESTREL LABS"]["weight"] == 8  # summed; alias self-loop dropped
    assert G.edges["DEEPCAST", "KESTREL LABS"]["source_ids"] == ["u1", "u2"]
    assert G.nodes["DEEPCAST"]["degree"] == 1 and "human_id" in G.nodes["DEEPCAST"]

    summarised = build_graph([ex1, ex2], llm=llm, name_map={"KESTREL": "KESTREL LABS"})
    assert summarised.nodes["DEEPCAST"]["description"]


def test_modularity_matches_networkx():
    G = nx.karate_club_graph()
    parts = louvain_communities(G, seed=1)
    assert modularity(G, parts) == pytest.approx(nx.community.modularity(G, parts))


def test_louvain_on_planted_partition():
    G = nx.planted_partition_graph(4, 12, p_in=0.7, p_out=0.02, seed=7)
    parts = louvain_communities(G, seed=42)
    assert modularity(G, parts) > 0.3
    assert len(parts) == 4
    truth = [set(range(i * 12, (i + 1) * 12)) for i in range(4)]
    assert sorted(map(sorted, parts)) == sorted(map(sorted, truth))
    assert louvain_communities(G, seed=42) == parts  # deterministic given the seed


def test_louvain_edge_cases():
    G = nx.Graph()
    G.add_nodes_from(["a", "b"])
    assert louvain_communities(G) == [{"a"}, {"b"}]


def test_hierarchical_communities():
    G = nx.planted_partition_graph(2, 20, p_in=0.5, p_out=0.01, seed=3)
    comms = hierarchical_communities(G, max_cluster_size=10, seed=42, use_leiden=False)
    level0 = [c for c in comms if c.level == 0]
    assert sorted(n for c in level0 for n in c.nodes) == sorted(G.nodes)
    for c in comms:
        if c.children:
            child_nodes = sorted(n for ch in c.children for n in comms[ch].nodes)
            assert child_nodes == sorted(c.nodes)
            assert all(comms[ch].parent == c.id and comms[ch].level == c.level + 1 for ch in c.children)
    assert any(c.level == 1 for c in comms)


def test_corpus_graph_has_expected_structure(index):
    G = index.graph
    assert {"KESTREL LABS", "DEEPCAST", "MARLOW DYNAMICS", "PRIYA NAIR", "TIDEWATER INSTITUTE"} <= set(G.nodes)
    assert "TWI" in G.nodes["TIDEWATER INSTITUTE"]["aliases"]
    assert "OKAFOR" in G.nodes["DR. MIRA OKAFOR"]["aliases"]
    assert modularity(G, louvain_communities(G)) > 0.15
    same = [c for c in index.communities if {"DEEPCAST", "MARLOW DYNAMICS"} <= set(c.nodes)]
    assert same and len(same[0].nodes) <= 4
