from datetime import date

from minigraphrag.evaluation import context_recall, exact_match, llm_judge_pairwise, run_eval, token_f1
from minigraphrag.search.common import SearchResult
from minigraphrag.search.text2cypher import generate_cypher, graph_schema, graph_to_cypher_statements, validate_cypher
from minigraphrag.temporal import add_fact, as_of, holders, kestrel_timeline, new_temporal_graph


def test_cto_change_invalidates_previous_fact():
    G = new_temporal_graph()
    add_fact(G, "Jonas Vehl", "CTO_OF", "Kestrel Labs", "2021", recorded_at="2021-10-04")
    add_fact(G, "Priya Nair", "CTO_OF", "Kestrel Labs", "2026-03", recorded_at="2026-03-26")
    old = next(d for u, _, d in G.edges(data=True) if u == "Jonas Vehl")
    assert old["valid_to"] == date(2026, 3, 1) and old["invalidated_at"] == date(2026, 3, 26)
    assert G.number_of_edges() == 2  # history is kept, not deleted
    assert holders(G, "CTO_OF", "Kestrel Labs", "2024-08") == ["Jonas Vehl"]
    assert holders(G, "CTO_OF", "Kestrel Labs", "2026-04") == ["Priya Nair"]
    # What did we believe in January 2026 about April 2026? We didn't know about the change yet.
    assert holders(G, "CTO_OF", "Kestrel Labs", "2026-04", known_at="2026-01-01") == ["Jonas Vehl"]


def test_non_exclusive_relations_coexist():
    G = new_temporal_graph()
    add_fact(G, "Jonas Vehl", "CO_FOUNDED", "Kestrel Labs", "2021")
    add_fact(G, "Dr. Mira Okafor", "CO_FOUNDED", "Kestrel Labs", "2021")
    assert len(holders(G, "CO_FOUNDED", "Kestrel Labs", "2025")) == 2


def test_kestrel_timeline():
    G = kestrel_timeline()
    assert holders(G, "SUPPLIED", "Kestrel Labs", "2024-06") == ["Deepcast"]
    assert holders(G, "SUPPLIED", "Kestrel Labs", "2025-09") == []
    assert as_of(G, "2014").number_of_edges() == 0


def test_validate_cypher():
    labels = ["Entity", "Organization"]
    assert validate_cypher('MATCH (n:Entity {name: "DEEPCAST"})-[r]-(m) RETURN m.name', labels) == []
    assert any("write" in e for e in validate_cypher("MATCH (n) DETACH DELETE n RETURN n", labels))
    assert any("unknown label" in e for e in validate_cypher("MATCH (n:Spaceship) RETURN n", labels))
    assert any("unbalanced" in e for e in validate_cypher("MATCH (n:Entity RETURN n", labels))
    assert validate_cypher('MATCH (n:Entity {name: "CREATE"}) RETURN n', labels) == []  # strings are ignored
    assert validate_cypher("MATCH (a)-[:KNOWS]->(b) RETURN b", labels, ["RELATED_TO"])


def test_cypher_export_and_generation(index, llm):
    stmts = graph_to_cypher_statements(index.graph)
    assert len(stmts) == index.graph.number_of_nodes() + index.graph.number_of_edges()
    assert any("MERGE (n:Entity:Organization" in s for s in stmts)
    assert "Organization" in graph_schema(index.graph)["labels"]
    assert "DEEPCAST" in generate_cypher(llm, "Who is connected to Deepcast?", index.graph)


def test_answer_metrics():
    assert exact_match("The Deepcast.", "deepcast") == 1.0
    assert token_f1("Priya Nair since March 2026", "Priya Nair") == 2 * (2 / 5) * 1 / (2 / 5 + 1)
    assert token_f1("", "x") == 0.0
    assert context_recall(["a", "b"], ["b", "c"]) == 0.5


def test_judge_and_run_eval(llm):
    verdict = llm_judge_pairwise(llm, "q", "Short.", "A much longer answer with many different words [Data: Sources (1)].")
    assert verdict["comprehensiveness"]["winner"] == "B"
    assert verdict["directness"]["winner"] == "A"
    questions = [{"id": "x", "type": "single-hop", "question": "q", "answer": "Deepcast", "supporting_docs": ["d1"]}]
    result = run_eval(questions, {"echo": lambda q: SearchResult("Deepcast", "echo", sources=["d1"])})
    assert result["summary"]["echo"]["all"]["exact_match"] == 1.0
    assert result["summary"]["echo"]["single-hop"]["context_recall"] == 1.0
