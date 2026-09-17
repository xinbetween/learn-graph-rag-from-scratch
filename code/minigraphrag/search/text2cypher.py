"""Text2Cypher: let the LLM write a graph query instead of retrieving text.

For precise, structural questions ("list everyone connected to Deepcast")
a database query beats similarity search. The risks are real, though: models
hallucinate labels and may emit write statements. So we (1) show the model the
exact schema, (2) validate the generated Cypher before running it: read-only
clauses only, known labels and relationship types only, balanced brackets.
"""

from __future__ import annotations

import json
import re

import networkx as nx

from .. import prompts as P
from ..llm import LLM

WRITE_CLAUSES = re.compile(r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|LOAD\s+CSV|FOREACH|CALL\s+dbms|CALL\s+apoc)\b", re.I)


def _label(entity_type: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", entity_type or "") if part) or "Thing"


def _quote(value) -> str:
    return json.dumps(str(value), ensure_ascii=False)  # JSON string escaping is valid Cypher string escaping


def graph_to_cypher_statements(G: nx.Graph, relationship_type: str = "RELATED_TO") -> list[str]:
    """Export the graph as idempotent MERGE statements (run them in Neo4j Browser or via the driver)."""
    stmts = []
    for n, d in G.nodes(data=True):
        stmts.append(f"MERGE (n:Entity:{_label(d.get('type', ''))} {{name: {_quote(n)}}}) "
                     f"SET n.description = {_quote(d.get('description', ''))}, n.degree = {int(d.get('degree', 0))}")
    for u, v, d in G.edges(data=True):
        stmts.append(f"MATCH (a:Entity {{name: {_quote(u)}}}), (b:Entity {{name: {_quote(v)}}}) "
                     f"MERGE (a)-[r:{relationship_type}]->(b) "
                     f"SET r.description = {_quote(d.get('description', ''))}, r.weight = {float(d.get('weight', 1.0))}")
    return stmts


def graph_schema(G: nx.Graph, relationship_type: str = "RELATED_TO") -> dict:
    labels = sorted({"Entity"} | {_label(d.get("type", "")) for _, d in G.nodes(data=True)})
    return {"labels": labels, "relationship_types": [relationship_type],
            "node_properties": ["name", "description", "degree"], "relationship_properties": ["description", "weight"]}


def schema_to_text(schema: dict) -> str:
    return (f"Node labels: {', '.join(schema['labels'])}\n"
            f"Node properties: {', '.join(schema['node_properties'])}\n"
            f"Relationship types: {', '.join(schema['relationship_types'])}\n"
            f"Relationship properties: {', '.join(schema['relationship_properties'])}")


def validate_cypher(query: str, allowed_labels: list[str], allowed_relationship_types: list[str] | None = None) -> list[str]:
    """Return a list of problems; an empty list means the query passed the sanity checks."""
    errors = []
    stripped = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', '""', query)  # ignore string contents
    if WRITE_CLAUSES.search(stripped):
        errors.append("query contains a write clause; only read-only queries are allowed")
    if not re.search(r"\bMATCH\b", stripped, re.I) or not re.search(r"\bRETURN\b", stripped, re.I):
        errors.append("query must contain MATCH and RETURN")
    for open_, close in ("()", "[]", "{}"):
        if stripped.count(open_) != stripped.count(close):
            errors.append(f"unbalanced {open_}{close}")
    for label in re.findall(r"\(\s*\w*\s*((?::\w+)+)", stripped):
        for name in label.split(":")[1:]:
            if name not in allowed_labels:
                errors.append(f"unknown label {name!r}")
    if allowed_relationship_types is not None:
        for rel in re.findall(r"\[\s*\w*\s*:\s*([\w|]+)", stripped):
            for name in rel.split("|"):
                if name not in allowed_relationship_types:
                    errors.append(f"unknown relationship type {name!r}")
    return errors


def generate_cypher(llm: LLM, question: str, G: nx.Graph) -> str:
    """Ask the LLM for Cypher and validate it; raises ValueError if validation fails."""
    schema = graph_schema(G)
    raw = llm.complete(P.TEXT2CYPHER_PROMPT.format(schema=schema_to_text(schema), question=question))
    query = re.sub(r"^```(?:cypher)?|```$", "", raw.strip(), flags=re.M).strip()
    errors = validate_cypher(query, schema["labels"], schema["relationship_types"])
    if errors:
        raise ValueError(f"invalid Cypher: {'; '.join(errors)}\n{query}")
    return query


def run_cypher(query: str, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password") -> list[dict]:
    """Execute a (validated) query on Neo4j. Requires the `neo4j` extra and a running database."""
    from neo4j import GraphDatabase

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        records, _, _ = driver.execute_query(query)
        return [r.data() for r in records]
