"""Turning graph structures into text an LLM can read ("linearization").

An LLM cannot consume a networkx object; everything we retrieve must be
flattened into a prompt. How you flatten matters: triples are compact,
markdown tables are easy to cite by id, adjacency lists show neighbourhoods,
JSON is precise but token-hungry. `fit_to_budget` enforces the token limit
that every retrieval method has to respect.
"""

from __future__ import annotations

import json

import networkx as nx

from .tokens import count_tokens


def _clean(value) -> str:
    """Table cells must not contain the delimiter or newlines."""
    return str(value).replace("|", "/").replace("\n", " ").strip()


def format_table(title: str, header: list[str], rows: list[list]) -> str:
    """GraphRAG-style pipe-delimited table: `-----Title-----` then `a|b|c` lines."""
    lines = [f"-----{title}-----", "|".join(header)]
    lines += ["|".join(_clean(c) for c in row) for row in rows]
    return "\n".join(lines)


def parse_tables(text: str) -> dict[str, list[dict]]:
    """Inverse of `format_table`: {title: [row dicts]} (used by MockLLM and tests)."""
    tables: dict[str, list[dict]] = {}
    title, header = None, None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("-----") and s.endswith("-----") and len(s) > 10:
            title, header = s.strip("-"), None
            tables[title] = []
        elif title and s:
            cells = s.split("|")
            if header is None:
                header = cells
            else:
                tables[title].append(dict(zip(header, cells)))
    return tables


def fit_to_budget(items: list[str], max_tokens: int, header: str = "") -> list[str]:
    """Greedily keep items (already ranked best-first) until the budget is used up."""
    used = count_tokens(header)
    kept = []
    for item in items:
        t = count_tokens(item)
        if used + t > max_tokens:
            break
        kept.append(item)
        used += t
    return kept


def triples_to_text(G: nx.Graph, edges: list[tuple[str, str]] | None = None) -> str:
    """One `(SOURCE, description, TARGET)` line per edge: the most compact format."""
    edges = edges if edges is not None else list(G.edges())
    return "\n".join(f"({u}, {G.edges[u, v].get('description', 'related to')}, {v})" for u, v in edges)


def to_markdown_tables(G: nx.Graph, nodes: list[str] | None = None) -> str:
    """Markdown entity and relationship tables for the induced subgraph on `nodes`."""
    nodes = nodes if nodes is not None else list(G.nodes())
    sub = G.subgraph(nodes)
    out = ["| id | entity | type | description |", "|---|---|---|---|"]
    for n in nodes:
        d = G.nodes[n]
        out.append(f"| {d.get('human_id', '')} | {n} | {d.get('type', '')} | {_clean(d.get('description', ''))} |")
    out += ["", "| id | source | target | description | weight |", "|---|---|---|---|---|"]
    for u, v, d in sub.edges(data=True):
        out.append(f"| {d.get('human_id', '')} | {u} | {v} | {_clean(d.get('description', ''))} | {d.get('weight', 1)} |")
    return "\n".join(out)


def to_adjacency_text(G: nx.Graph, nodes: list[str] | None = None) -> str:
    """`NODE: neighbour1, neighbour2` lines: shows neighbourhood structure at a glance."""
    nodes = nodes if nodes is not None else list(G.nodes())
    return "\n".join(f"{n}: {', '.join(sorted(G.neighbors(n)))}" for n in nodes)


def to_json(G: nx.Graph, nodes: list[str] | None = None) -> str:
    """Node-link JSON of the induced subgraph (lists and scalars only)."""
    sub = G.subgraph(nodes if nodes is not None else list(G.nodes()))
    keep = ("type", "description")
    data = {
        "nodes": [{"id": n, **{k: d[k] for k in keep if k in d}} for n, d in sub.nodes(data=True)],
        "edges": [{"source": u, "target": v, "description": d.get("description", ""), "weight": d.get("weight", 1)}
                  for u, v, d in sub.edges(data=True)],
    }
    return json.dumps(data, indent=1)
