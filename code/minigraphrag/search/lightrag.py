"""LightRAG-style dual-level retrieval.

LightRAG skips community reports entirely. Instead it asks the LLM to split a
query into two kinds of keywords:

- low-level (specific entities: "Priya Nair", "Deepcast") -> matched against
  *entity* embeddings, then expanded to their one-hop relationships;
- high-level (themes: "supply chain", "risk") -> matched against
  *relationship* embeddings, then expanded to their endpoint entities.

`mode="local"` uses only low-level keywords, `"global"` only high-level ones,
`"hybrid"` both. It is much cheaper to index and update than GraphRAG.
"""

from __future__ import annotations

from collections import Counter

from .. import prompts as P
from ..context import format_table
from ..llm import LLM, parse_json_response
from ..tokens import count_tokens
from .common import DEFAULT_RESPONSE_TYPE, SearchResult, doc_ids_for_units, generate_answer


def extract_keywords(llm: LLM, query: str) -> tuple[list[str], list[str]]:
    """Return (high_level_keywords, low_level_keywords)."""
    data = parse_json_response(llm.complete(P.KEYWORD_EXTRACTION_PROMPT.format(query=query), json=True))
    return [str(k) for k in data.get("high_level_keywords", [])], [str(k) for k in data.get("low_level_keywords", [])]


def _fill(rows: list[list], budget: int) -> list[list]:
    kept, used = [], 0
    for row in rows:
        t = count_tokens("|".join(map(str, row)))
        if used + t > budget:
            break
        kept.append(row)
        used += t
    return kept


def build_lightrag_context(index, query: str, high_keywords: list[str], low_keywords: list[str], top_k: int = 10,
                           max_context_tokens: int = 4000, mode: str = "hybrid") -> tuple[str, dict]:
    G = index.graph
    embed = lambda text: index.embedder.embed([text])[0]  # noqa: E731
    entities: list[str] = []
    edges: list[tuple[str, str]] = []

    if mode in ("local", "hybrid"):
        hits = index.entity_store.search(embed(", ".join(low_keywords) or query), k=top_k)
        entities += [name for name, _, _ in hits]
        one_hop = [(e, n) for e in entities for n in G.neighbors(e)]
        one_hop.sort(key=lambda e: (-G.edges[e].get("combined_degree", 0), -G.edges[e].get("weight", 0)))
        edges += one_hop
    if mode in ("global", "hybrid"):
        hits = index.relationship_store.search(embed(", ".join(high_keywords) or query), k=top_k)
        global_edges = [(m["source"], m["target"]) for _, _, m in hits]
        edges = global_edges + edges if mode == "global" else edges[: top_k] + global_edges + edges[top_k:]
        entities += [n for e in global_edges for n in e]

    entities = list(dict.fromkeys(entities))
    seen, unique_edges = set(), []
    for u, v in edges:
        key = tuple(sorted((u, v)))
        if key not in seen:
            seen.add(key)
            unique_edges.append((u, v))

    third = max_context_tokens // 3
    entity_rows = _fill([[G.nodes[e]["human_id"], e, G.nodes[e].get("type", ""), G.nodes[e].get("description", "")]
                         for e in entities], third)
    rel_rows = _fill([[G.edges[e]["human_id"], e[0], e[1], G.edges[e].get("description", ""), G.edges[e].get("weight", 0)]
                      for e in unique_edges], third)
    # Text units ranked by how many of the retrieved entities and relationships cite them.
    unit_counts = Counter(u for e in entities for u in G.nodes[e].get("source_ids", []))
    unit_counts.update(u for e in unique_edges for u in G.edges[e].get("source_ids", []))
    unit_rows = _fill([[u, index.text_units[u].text] for u, _ in unit_counts.most_common() if u in index.text_units], third)

    context = "\n\n".join([
        format_table("Entities", ["id", "entity", "type", "description"], entity_rows),
        format_table("Relationships", ["id", "source", "target", "description", "weight"], rel_rows),
        format_table("Sources", ["id", "text"], unit_rows),
    ])
    data = {"entities": [r[1] for r in entity_rows], "relationships": [(r[1], r[2]) for r in rel_rows],
            "sources": [{"id": r[0], "text": r[1]} for r in unit_rows],
            "high_level_keywords": high_keywords, "low_level_keywords": low_keywords}
    return context, data


def lightrag_search(index, query: str, llm: LLM, mode: str = "hybrid", top_k: int = 10,
                    max_context_tokens: int = 4000, response_type: str = DEFAULT_RESPONSE_TYPE) -> SearchResult:
    high, low = extract_keywords(llm, query)
    context, data = build_lightrag_context(index, query, high, low, top_k, max_context_tokens, mode)
    answer = generate_answer(llm, query, context, response_type)
    return SearchResult(answer, f"lightrag-{mode}", context, data,
                        doc_ids_for_units(index, [s["id"] for s in data["sources"]]), llm_calls=2)
