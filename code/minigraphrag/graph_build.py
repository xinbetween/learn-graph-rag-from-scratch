"""Assembling the knowledge graph from per-chunk extractions.

The same entity or relationship is usually extracted from several chunks, each
time with a slightly different description. GraphRAG's merge rule is simple:
keep *all* descriptions (and source ids), sum relationship weights, then ask
an LLM to summarise the description list into one text. Degree becomes the
entity's "rank", later used to prioritise what goes into limited contexts.
"""

from __future__ import annotations

import json
from collections import Counter

import networkx as nx

from . import prompts as P
from .extraction import ExtractionResult
from .llm import LLM
from .tokens import count_tokens


def build_graph(
    extractions: list[ExtractionResult],
    llm: LLM | None = None,
    name_map: dict[str, str] | None = None,
    summarize_max_tokens: int = 150,
) -> nx.Graph:
    """Merge extractions into an undirected weighted graph.

    `name_map` (from `resolve_entities`) rewrites aliases to canonical names
    before merging. If `llm` is given, descriptions are summarised.
    """
    name_map = name_map or {}
    canon = lambda n: name_map.get(n, n)  # noqa: E731
    G = nx.Graph()
    type_votes: dict[str, Counter] = {}

    for ex in extractions:
        for e in ex.entities:
            n = canon(e.name)
            if n not in G:
                G.add_node(n, descriptions=[], source_ids=[], aliases=[])
            d = G.nodes[n]
            if e.description and e.description not in d["descriptions"]:
                d["descriptions"].append(e.description)
            if e.source_id and e.source_id not in d["source_ids"]:
                d["source_ids"].append(e.source_id)
            if e.name != n and e.name not in d["aliases"]:
                d["aliases"].append(e.name)
            type_votes.setdefault(n, Counter())[e.type] += 1

        for r in ex.relationships:
            u, v = canon(r.source), canon(r.target)
            if u == v:
                continue  # an alias pair collapsed into a self-loop
            for n in (u, v):  # relationships may mention entities not extracted separately
                if n not in G:
                    G.add_node(n, descriptions=[], source_ids=[], aliases=[])
            if not G.has_edge(u, v):
                G.add_edge(u, v, descriptions=[], source_ids=[], weight=0.0)
            d = G.edges[u, v]
            if r.description and r.description not in d["descriptions"]:
                d["descriptions"].append(r.description)
            if r.source_id and r.source_id not in d["source_ids"]:
                d["source_ids"].append(r.source_id)
            d["weight"] += r.strength

    for n, d in G.nodes(data=True):
        d["type"] = type_votes[n].most_common(1)[0][0] if n in type_votes else ""
        d["description"] = " ".join(d["descriptions"])
        d["frequency"] = len(d["source_ids"])
    for _, _, d in G.edges(data=True):
        d["description"] = " ".join(d["descriptions"])

    if llm is not None:
        summarize_descriptions(llm, G, summarize_max_tokens)
    add_rank_attributes(G)
    return G


def add_rank_attributes(G: nx.Graph) -> None:
    """Degree as entity rank, sum of endpoint degrees as relationship rank, plus stable human ids."""
    for i, n in enumerate(sorted(G.nodes())):
        G.nodes[n]["degree"] = G.degree(n)
        G.nodes[n]["rank"] = G.degree(n)
        G.nodes[n]["human_id"] = i
    for i, (u, v) in enumerate(sorted(tuple(sorted(e)) for e in G.edges())):
        G.edges[u, v]["combined_degree"] = G.degree(u) + G.degree(v)
        G.edges[u, v]["rank"] = G.edges[u, v]["combined_degree"]
        G.edges[u, v]["human_id"] = i


def summarize_descriptions(llm: LLM, graph: nx.Graph, max_tokens: int = 150) -> nx.Graph:
    """Replace multi-description nodes/edges with one LLM summary (single descriptions are kept as is)."""

    def summarise(name: str, descriptions: list[str]) -> str:
        if len(descriptions) <= 1 and count_tokens(" ".join(descriptions)) <= max_tokens:
            return " ".join(descriptions)
        prompt = P.SUMMARIZE_DESCRIPTIONS_PROMPT.format(
            entity_name=name, description_list=json.dumps(sorted(descriptions)), max_tokens=max_tokens
        )
        return llm.complete(prompt).strip()

    for n, d in graph.nodes(data=True):
        d["description"] = summarise(n, d.get("descriptions", []))
    for u, v, d in graph.edges(data=True):
        d["description"] = summarise(json.dumps([u, v]), d.get("descriptions", []))
    return graph
