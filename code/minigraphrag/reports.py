"""Community reports: the summaries global search reasons over.

For each community we build a context of its entities and relationships
(highest-degree first, because hubs carry the most information), and ask the
LLM for a structured JSON report. We go *bottom-up* through the hierarchy: if a
large parent community doesn't fit the token budget, we substitute the already
written reports of its children for the raw tables. That is how GraphRAG
summarises big communities without ever exceeding the context window.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

import networkx as nx

from . import prompts as P
from .communities import Community
from .context import format_table, fit_to_budget
from .llm import LLM, parse_json_response
from .tokens import count_tokens


@dataclass
class CommunityReport:
    community_id: int
    level: int
    title: str
    summary: str
    rating: float
    rating_explanation: str
    findings: list[dict] = field(default_factory=list)

    @property
    def full_content(self) -> str:
        """Markdown rendering: what gets embedded and put into search contexts."""
        lines = [f"# {self.title}", "", self.summary, ""]
        for f in self.findings:
            lines += [f"## {f.get('summary', '')}", "", f.get("explanation", ""), ""]
        return "\n".join(lines).strip()

    def to_dict(self) -> dict:
        return asdict(self)


def _entity_rows(G: nx.Graph, nodes: list[str]) -> list[list]:
    ranked = sorted(nodes, key=lambda n: (-G.nodes[n].get("degree", 0), n))
    return [[G.nodes[n]["human_id"], n, G.nodes[n].get("type", ""), G.nodes[n].get("description", ""),
             G.nodes[n].get("degree", 0)] for n in ranked]


def _relationship_rows(G: nx.Graph, edges: list[tuple[str, str]]) -> list[list]:
    ranked = sorted(edges, key=lambda e: (-G.edges[e].get("combined_degree", 0), e))
    return [[G.edges[e]["human_id"], e[0], e[1], G.edges[e].get("description", ""),
             G.edges[e].get("combined_degree", 0)] for e in ranked]


ENTITY_HEADER = ["id", "entity", "type", "description", "degree"]
RELATIONSHIP_HEADER = ["id", "source", "target", "description", "combined_degree"]


def _fit_rows(rows: list[list], max_tokens: int) -> list[list]:
    """Keep the leading rows whose rendered lines fit in `max_tokens`."""
    lines = ["|".join(str(c) for c in row) for row in rows]
    return rows[: len(fit_to_budget(lines, max_tokens))]


def build_community_context(G: nx.Graph, community: Community, max_tokens: int = 4000) -> str:
    """Entity and relationship tables for one community, truncated to `max_tokens`.

    Half the budget goes to entities and half to relationships, each ranked by degree.
    """
    ent_rows = _fit_rows(_entity_rows(G, community.nodes), max_tokens // 2)
    rel_rows = _fit_rows(_relationship_rows(G, [tuple(e) for e in community.edges]), max_tokens // 2)
    return (format_table("Entities", ENTITY_HEADER, ent_rows) + "\n\n"
            + format_table("Relationships", RELATIONSHIP_HEADER, rel_rows))


def _full_context_tokens(G: nx.Graph, community: Community) -> int:
    return count_tokens(build_community_context(G, community, max_tokens=10**9))


def _substituted_context(G: nx.Graph, community: Community, child_reports: list[CommunityReport],
                         children: list[Community], max_tokens: int) -> str:
    """Replace raw tables with sub-community reports (largest children first)."""
    sizes = {c.id: len(c.nodes) for c in children}
    ranked = sorted(child_reports, key=lambda r: -sizes.get(r.community_id, 0))
    rows = _fit_rows([[r.community_id, r.title, r.summary] for r in ranked], max_tokens // 2)
    used = {row[0] for row in rows}
    covered = {n for c in children if c.id in used for n in c.nodes}
    remaining = Community(community.id, community.level, community.parent,
                          [n for n in community.nodes if n not in covered],
                          [e for e in community.edges if not (e[0] in covered and e[1] in covered)])
    return (format_table("Reports", ["id", "title", "summary"], rows) + "\n\n"
            + build_community_context(G, remaining, max_tokens // 2))


def generate_report(llm: LLM, context: str, community_id: int = -1, level: int = 0) -> CommunityReport:
    """Ask the LLM for a JSON report and parse it defensively."""
    data = parse_json_response(llm.complete(P.COMMUNITY_REPORT_PROMPT.format(input_text=context), json=True))
    try:
        rating = float(data.get("rating", 0))
    except (TypeError, ValueError):
        rating = 0.0
    findings = [f for f in data.get("findings", []) if isinstance(f, dict)]
    return CommunityReport(community_id, level, str(data.get("title", f"Community {community_id}")),
                           str(data.get("summary", "")), rating, str(data.get("rating_explanation", "")), findings)


def generate_all_reports(llm: LLM, G: nx.Graph, communities: list[Community], max_tokens: int = 4000,
                         min_size: int = 2) -> list[CommunityReport]:
    """Write a report for every community (with at least `min_size` nodes), deepest level first."""
    by_id = {c.id: c for c in communities}
    reports: dict[int, CommunityReport] = {}
    for c in sorted(communities, key=lambda c: (-c.level, c.id)):
        if len(c.nodes) < min_size:
            continue
        child_reports = [reports[ch] for ch in c.children if ch in reports]
        if child_reports and _full_context_tokens(G, c) > max_tokens:
            context = _substituted_context(G, c, child_reports, [by_id[ch] for ch in c.children], max_tokens)
        else:
            context = build_community_context(G, c, max_tokens)
        reports[c.id] = generate_report(llm, context, c.id, c.level)
    return [reports[k] for k in sorted(reports)]
