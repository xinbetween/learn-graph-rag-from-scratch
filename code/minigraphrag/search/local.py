"""GraphRAG local search: entity-centric retrieval.

Steps:
1. Embed the query and find the most similar *entity descriptions*.
2. Fan out from those entities: their relationships, the text units they were
   extracted from, and the reports of the communities they belong to.
3. Split the token budget proportionally (default: 15% community reports,
   50% source text, 35% entities + relationships) and fill each slice with the
   highest-ranked items.
4. Render tables with ids so the answer can cite [Data: Entities (3)].

Because relationships connect entities from different documents, one query
entity pulls in facts from many documents: that is the multi-hop advantage.
"""

from __future__ import annotations

import re
from collections import Counter

from ..context import format_table
from ..llm import LLM
from ..tokens import count_tokens
from .common import DEFAULT_RESPONSE_TYPE, SearchResult, doc_ids_for_units, generate_answer


def map_query_to_entities(index, query: str, top_k: int = 10, include_name_matches: bool = True) -> list[str]:
    """Entities most relevant to the query, by description embedding.

    GraphRAG uses embeddings only; `include_name_matches` additionally puts
    entities whose name or alias literally occurs in the query first, a cheap
    and very effective boost.
    """
    G = index.graph
    hits = [name for name, _, _ in index.entity_store.search(index.embedder.embed([query])[0], k=top_k * 2)]
    mentioned = []
    if include_name_matches:
        q = query.upper()
        for n, d in G.nodes(data=True):
            if any(re.search(rf"(?<!\w){re.escape(s)}(?!\w)", q) for s in [n, *d.get("aliases", [])]):
                mentioned.append(n)
    # Rarer entities first: "PROJECT TERN" says more about the question than the hub "KESTREL LABS".
    mentioned.sort(key=lambda n: len(G.nodes[n].get("source_ids", [])))
    return list(dict.fromkeys(mentioned + hits))[:top_k]


def _fill(rows: list[list], budget: int) -> list[list]:
    kept, used = [], 0
    for row in rows:
        t = count_tokens("|".join(map(str, row)))
        if used + t > budget:
            break
        kept.append(row)
        used += t
    return kept


def build_local_context(
    index,
    query: str,
    top_k_entities: int = 10,
    max_context_tokens: int = 8000,
    community_prop: float = 0.15,
    text_unit_prop: float = 0.5,
) -> tuple[str, dict]:
    """Return (context text, {table name: rows}) for local search."""
    G = index.graph
    entities = map_query_to_entities(index, query, top_k_entities)
    selected = set(entities)

    # --- community reports: communities containing the most selected entities first
    counts = Counter(c.id for e in entities for c in index.communities_of(e))
    community_rows = []
    for cid, _ in sorted(counts.items(), key=lambda x: (-x[1], -(index.report(x[0]).rating if index.report(x[0]) else 0))):
        report = index.report(cid)
        if report:
            community_rows.append([cid, report.title, report.full_content])
    community_rows = _fill(community_rows, int(max_context_tokens * community_prop))

    # --- entities and relationships share the "local" slice
    local_budget = int(max_context_tokens * (1 - community_prop - text_unit_prop))
    entity_rows = _fill([[G.nodes[e]["human_id"], e, G.nodes[e].get("description", ""), G.degree(e)]
                         for e in entities], local_budget // 2)
    in_network = [(u, v) for u, v in G.subgraph(entities).edges()]
    out_network = [(e, n) for e in entities for n in G.neighbors(e) if n not in selected]
    # External neighbours linked to several selected entities are the best bridges.
    links = Counter(n for _, n in out_network)
    out_network.sort(key=lambda e: (-links[e[1]], -G.edges[e].get("weight", 0)))
    edges = list(dict.fromkeys(tuple(e) for e in in_network + out_network))
    rel_rows = _fill([[G.edges[e]["human_id"], e[0], e[1], G.edges[e].get("description", ""),
                       G.edges[e].get("weight", 0)] for e in edges],
                     local_budget - sum(count_tokens("|".join(map(str, r))) for r in entity_rows))

    # --- text units: from the best entities first, then by how many selected relationships cite them
    rel_sources = Counter(s for e in edges for s in G.edges[e].get("source_ids", []))
    unit_order: dict[str, tuple] = {}
    for rank, e in enumerate(entities):
        for uid in G.nodes[e].get("source_ids", []):
            unit_order.setdefault(uid, (rank, -rel_sources[uid]))
    unit_ids = sorted(unit_order, key=lambda u: unit_order[u])
    unit_rows = _fill([[u, index.text_units[u].text] for u in unit_ids if u in index.text_units],
                      int(max_context_tokens * text_unit_prop))

    parts = []
    if community_rows:
        parts.append(format_table("Reports", ["id", "title", "content"], community_rows))
    parts.append(format_table("Entities", ["id", "entity", "description", "number of relationships"], entity_rows))
    parts.append(format_table("Relationships", ["id", "source", "target", "description", "weight"], rel_rows))
    parts.append(format_table("Sources", ["id", "text"], unit_rows))
    data = {
        "reports": [dict(zip(["id", "title", "content"], r)) for r in community_rows],
        "entities": [dict(zip(["id", "entity", "description", "degree"], r)) for r in entity_rows],
        "relationships": [dict(zip(["id", "source", "target", "description", "weight"], r)) for r in rel_rows],
        "sources": [dict(zip(["id", "text"], r)) for r in unit_rows],
    }
    return "\n\n".join(parts), data


def local_search(
    index,
    query: str,
    llm: LLM,
    top_k_entities: int = 10,
    max_context_tokens: int = 8000,
    community_prop: float = 0.15,
    text_unit_prop: float = 0.5,
    response_type: str = DEFAULT_RESPONSE_TYPE,
) -> SearchResult:
    context, data = build_local_context(index, query, top_k_entities, max_context_tokens, community_prop, text_unit_prop)
    answer = generate_answer(llm, query, context, response_type)
    sources = doc_ids_for_units(index, [s["id"] for s in data["sources"]])
    return SearchResult(answer, "local", context, data, sources, llm_calls=1)
