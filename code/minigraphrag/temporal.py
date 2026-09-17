"""A bi-temporal knowledge graph (in the style of Graphiti/Zep).

Facts change: Jonas Vehl was CTO until March 2026, then Priya Nair. A plain
graph either keeps both edges (and answers "who is the CTO?" with two people)
or overwrites history. A *bi-temporal* edge tracks two timelines:

- valid time  (`valid_from`, `valid_to`):   when the fact was true in the world;
- record time (`recorded_at`, `invalidated_at`): when *we* learned it / learned it stopped.

New facts never delete old ones. Instead, a contradicting fact closes the old
edge's validity interval and stamps `invalidated_at`. That lets us answer both
"who was CTO in 2024?" (valid time) and "what did we believe in January 2026?"
(record time).
"""

from __future__ import annotations

from datetime import date

import networkx as nx

# Relations where a target can have only one source at a time (one CTO per company).
EXCLUSIVE_RELATIONS: set[str] = {"CTO_OF", "CEO_OF"}


def parse_date(value: str | date | None) -> date | None:
    """Accept date objects or ISO-ish strings: '2026', '2026-03', '2026-03-26'."""
    if value is None or isinstance(value, date):
        return value
    parts = [int(p) for p in str(value).split("-")]
    return date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)


def new_temporal_graph() -> nx.MultiDiGraph:
    """Directed multigraph: the same pair can hold many facts over time."""
    return nx.MultiDiGraph()


def add_fact(
    G: nx.MultiDiGraph,
    source: str,
    relation: str,
    target: str,
    valid_from: str | date,
    valid_to: str | date | None = None,
    recorded_at: str | date | None = None,
    description: str = "",
    exclusive: bool | None = None,
) -> int:
    """Add a fact edge, invalidating contradicting facts. Returns the new edge key."""
    vf, vt = parse_date(valid_from), parse_date(valid_to)
    rec = parse_date(recorded_at) or vf
    exclusive = relation in EXCLUSIVE_RELATIONS if exclusive is None else exclusive

    if exclusive and target in G:
        for old_source, _, key, d in list(G.in_edges(target, keys=True, data=True)):
            if d["relation"] != relation or old_source == source or d["invalidated_at"] is not None:
                continue
            if d["valid_to"] is None or d["valid_to"] > vf:
                # Close the old interval where the new one begins; remember what we believed before.
                d["prior_valid_to"] = d["valid_to"]
                d["valid_to"] = vf
                d["invalidated_at"] = rec

    return G.add_edge(source, target, relation=relation, description=description, valid_from=vf, valid_to=vt,
                      recorded_at=rec, invalidated_at=None, prior_valid_to=None)


def is_valid(d: dict, at: date, known_at: date | None = None) -> bool:
    """Was this fact true at `at`, according to what was recorded by `known_at` (default: now)?"""
    valid_to = d["valid_to"]
    if known_at is not None:
        if d["recorded_at"] > known_at:
            return False  # we hadn't learned this fact yet
        if d["invalidated_at"] is not None and d["invalidated_at"] > known_at:
            valid_to = d["prior_valid_to"]  # the invalidation hadn't happened yet
    return d["valid_from"] <= at and (valid_to is None or at < valid_to)


def as_of(G: nx.MultiDiGraph, at: str | date, known_at: str | date | None = None) -> nx.MultiDiGraph:
    """Snapshot of the facts valid at `at` (optionally as believed at `known_at`)."""
    at_d, known_d = parse_date(at), parse_date(known_at)
    snap = nx.MultiDiGraph()
    snap.add_nodes_from(G.nodes(data=True))
    for u, v, k, d in G.edges(keys=True, data=True):
        if is_valid(d, at_d, known_d):
            snap.add_edge(u, v, key=k, **d)
    return snap


def holders(G: nx.MultiDiGraph, relation: str, target: str, at: str | date, known_at: str | date | None = None) -> list[str]:
    """Sources holding `relation` to `target` at a date, e.g. holders(G, 'CTO_OF', 'Kestrel Labs', '2024-08')."""
    snap = as_of(G, at, known_at)
    if target not in snap:
        return []
    return sorted({u for u, _, d in snap.in_edges(target, data=True) if d["relation"] == relation})


def kestrel_timeline() -> nx.MultiDiGraph:
    """The dated facts of the running example, recorded in publication order."""
    G = new_temporal_graph()
    facts = [
        ("Dr. Mira Okafor", "FORMERLY_WORKED_AT", "Tidewater Institute", "2015", "2021", "2021-10-04"),
        ("Dr. Mira Okafor", "CO_FOUNDED", "Kestrel Labs", "2021", None, "2021-10-04"),
        ("Jonas Vehl", "CO_FOUNDED", "Kestrel Labs", "2021", None, "2021-10-04"),
        ("Dr. Mira Okafor", "CEO_OF", "Kestrel Labs", "2021", None, "2021-10-04"),
        ("Jonas Vehl", "CTO_OF", "Kestrel Labs", "2021", None, "2021-10-04"),
        ("Brightwater Capital", "INVESTED_IN", "Kestrel Labs", "2022-03-15", None, "2022-03-15"),
        ("Lena Park", "BOARD_MEMBER_OF", "Kestrel Labs", "2022-03-15", None, "2022-03-15"),
        ("Deepcast", "SUPPLIED", "Kestrel Labs", "2022-08", None, "2022-08-09"),
        ("Kestrel Labs", "RUNS", "Project Sentinel", "2023-02", None, "2023-02-21"),
        ("Priya Nair", "LEADS", "Project Sentinel", "2023-06", None, "2023-09-12"),
        ("Project Sentinel", "DETECTED", "2024 Halden Reef bleaching event", "2024-08-11", None, "2024-09-03"),
        ("Marlow Dynamics", "ACQUIRED", "Deepcast", "2025-04", None, "2025-04-17"),
        ("Kestrel Labs", "RUNS", "Project Tern", "2025-06-30", None, "2025-06-30"),
        ("Port Avalon City Council", "CONTRACTED", "Kestrel Labs", "2025-11-18", None, "2025-11-18"),
        ("Priya Nair", "CTO_OF", "Kestrel Labs", "2026-03", None, "2026-03-26"),
        ("Jonas Vehl", "CHIEF_SCIENTIST_OF", "Kestrel Labs", "2026-03", None, "2026-03-26"),
    ]
    for s, r, t, vf, vt, rec in facts:
        add_fact(G, s, r, t, vf, vt, rec)
    # The supply ended when the board memo recorded it: close that edge explicitly.
    for u, v, d in G.edges(data=True):
        if d["relation"] == "SUPPLIED":
            d["prior_valid_to"], d["valid_to"], d["invalidated_at"] = None, date(2025, 6, 30), date(2025, 5, 14)
    return G
