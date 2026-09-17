import json

import pytest

from minigraphrag.cli import main
from minigraphrag.context import parse_tables, to_adjacency_text, to_json, to_markdown_tables, triples_to_text
from minigraphrag.search.basic import basic_search
from minigraphrag.search.global_ import NO_DATA_ANSWER, drift_search, dynamic_community_selection, global_search, reports_at_level
from minigraphrag.search.hybrid import hybrid_search
from minigraphrag.search.lightrag import extract_keywords, lightrag_search
from minigraphrag.search.local import build_local_context, local_search, map_query_to_entities
from minigraphrag.search.ppr import hipporag_search
from minigraphrag.search.subgraph import subgraph_search
from minigraphrag.tokens import count_tokens

from .conftest import CORPUS, QUESTIONS

CANONICAL = [
    "Why did Kestrel Labs start Project Tern?",
    "Which investor's board member oversees the company whose drones detected the Halden Reef bleaching?",
    "What connects Priya Nair to Deepcast?",
    "What are the main themes in this corpus?",
    "What risks does Kestrel Labs face?",
    "Who is the CTO of Kestrel Labs?",
    "Who supplied Kestrel's sonar in 2024?",
]


def test_questions_file():
    rows = [json.loads(line) for line in QUESTIONS.read_text().splitlines()]
    assert len(rows) >= 22 and [r["question"] for r in rows[:7]] == CANONICAL
    docs = {p.stem for p in CORPUS.glob("*.md")}
    assert all(set(r["supporting_docs"]) <= docs for r in rows)
    assert {r["type"] for r in rows} == {"multi-hop", "global", "temporal", "single-hop"}


def test_local_context(index):
    assert map_query_to_entities(index, "What connects Priya Nair to Deepcast?")[:2] == ["DEEPCAST", "PRIYA NAIR"] or \
        {"DEEPCAST", "PRIYA NAIR"} <= set(map_query_to_entities(index, "What connects Priya Nair to Deepcast?")[:2])
    context, data = build_local_context(index, "Why did Kestrel Labs start Project Tern?", max_context_tokens=8000)
    assert set(parse_tables(context)) == {"Reports", "Entities", "Relationships", "Sources"}
    assert any(e["entity"] == "PROJECT TERN" for e in data["entities"])
    assert count_tokens(context) <= 8000 * 1.1
    assert all("id" in r for r in data["relationships"])


@pytest.mark.parametrize("question", CANONICAL)
def test_graph_methods_answer_canonical_questions(index, llm, question):
    for fn in (local_search, global_search, hipporag_search, hybrid_search):
        result = fn(index, question, llm)
        assert result.answer.strip(), fn.__name__
        assert result.answer != NO_DATA_ANSWER, fn.__name__


def test_multi_hop_retrieval_reaches_supporting_docs(index, llm):
    result = local_search(index, "What connects Priya Nair to Deepcast?", llm)
    assert {"05_kestrel_blog_priya_nair", "07_marlow_acquires_deepcast"} <= set(result.sources)
    assert "[Data:" in result.answer


def test_other_methods(index, llm):
    for fn in (basic_search, lightrag_search, drift_search, subgraph_search):
        result = fn(index, "Why did Kestrel Labs start Project Tern?", llm)
        assert result.answer.strip() and result.llm_calls >= 1, fn.__name__
    high, low = extract_keywords(llm, "What connects Priya Nair to Deepcast?")
    assert "Deepcast" in low and high


def test_global_search_details(index, llm):
    assert reports_at_level(index, 0)
    result = global_search(index, "What are the main themes in this corpus?", llm)
    assert result.context_data["points"] and result.llm_calls >= 2
    scores = [p["score"] for p in result.context_data["points"]]
    assert scores == sorted(scores, reverse=True)
    none = global_search(index, "zzzz qqqq", llm)
    assert none.answer == NO_DATA_ANSWER
    selected, calls = dynamic_community_selection(index, "Deepcast Marlow Dynamics acquisition", llm)
    assert selected and calls >= len(reports_at_level(index, 0))
    assert global_search(index, "What risks does Kestrel Labs face?", llm, dynamic=True).answer


def test_linearization(index):
    G = index.graph
    nodes = ["DEEPCAST", "MARLOW DYNAMICS"]
    assert "DEEPCAST" in triples_to_text(G, [tuple(nodes)])
    assert to_markdown_tables(G, nodes).startswith("| id | entity")
    assert "MARLOW DYNAMICS" in to_adjacency_text(G, nodes)
    assert len(json.loads(to_json(G, nodes))["nodes"]) == 2


def test_cli_end_to_end(tmp_path, capsys):
    out = tmp_path / "idx"
    assert main(["index", "--input", str(CORPUS), "--output", str(out)]) == 0
    for method in ("local", "global", "drift", "basic", "lightrag", "ppr", "hybrid"):
        assert main(["query", "--index", str(out), "--method", method, "Why did Kestrel Labs start Project Tern?"]) == 0
        printed = capsys.readouterr().out
        assert f"[method={method}" in printed and len(printed) > 80
    assert main(["eval", "--index", str(out), "--questions", str(QUESTIONS), "--methods", "basic,local",
                 "--limit", "3", "--judge"]) == 0
    assert "Pairwise judge" in capsys.readouterr().out
