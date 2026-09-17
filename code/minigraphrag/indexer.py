"""The indexing pipeline, end to end.

    documents -> chunk -> extract (+gleaning) -> resolve aliases -> build graph
      -> summarise descriptions -> communities -> community reports -> embeddings

Every step writes a plain artifact (JSON, GraphML, .npz) so you can open the
output folder and inspect what each stage produced. Indexing is the expensive
part of GraphRAG (one or more LLM calls per chunk, per merged description, per
community); querying reuses these artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable

import networkx as nx

from . import prompts as P
from .chunking import TextUnit, chunk_documents, load_documents
from .communities import Community, hierarchical_communities
from .embeddings import Embedder, HashingEmbedder, get_embedder
from .extraction import Claim, ExtractionResult, extract_claims, extract_from_unit
from .graph_build import build_graph
from .llm import LLM
from .reports import CommunityReport, generate_all_reports
from .resolution import resolve_entities
from .vector_store import VectorStore


@dataclass
class IndexConfig:
    chunk_size: int = 300
    chunk_overlap: int = 50
    entity_types: list[str] = field(default_factory=lambda: list(P.DEFAULT_ENTITY_TYPES))
    max_gleanings: int = 1
    alias_threshold: float = 0.9
    summarize_max_tokens: int = 150
    max_cluster_size: int = 10
    report_max_tokens: int = 4000
    extract_claims: bool = True
    seed: int = 42


@dataclass
class Index:
    """Everything query-time methods need, loaded in memory."""

    graph: nx.Graph
    text_units: dict[str, TextUnit]
    communities: list[Community]
    reports: list[CommunityReport]
    claims: list[Claim]
    entity_store: VectorStore
    relationship_store: VectorStore
    text_unit_store: VectorStore
    report_store: VectorStore
    embedder: Embedder
    config: IndexConfig = field(default_factory=IndexConfig)

    def community(self, community_id: int) -> Community:
        return next(c for c in self.communities if c.id == community_id)

    def report(self, community_id: int) -> CommunityReport | None:
        return next((r for r in self.reports if r.community_id == community_id), None)

    def communities_of(self, entity: str) -> list[Community]:
        return [c for c in self.communities if entity in c.nodes]


def _embed_store(embedder: Embedder, ids: list[str], texts: list[str], metadata: list[dict]) -> VectorStore:
    store = VectorStore()
    if ids:
        store.add(ids, embedder.embed(texts), metadata)
    return store


def entity_embedding_text(name: str, data: dict) -> str:
    return f"{name}: {data.get('description', '')}"


def relationship_embedding_text(u: str, v: str, data: dict) -> str:
    return f"{u} {v}: {data.get('description', '')}"


def build_index(
    docs_dir: str | Path,
    out_dir: str | Path,
    llm: LLM,
    embedder: Embedder | None = None,
    config: IndexConfig | None = None,
    log: Callable[[str], None] | None = None,
) -> Index:
    """Run the full pipeline over `docs_dir` and write artifacts to `out_dir`."""
    config = config or IndexConfig()
    embedder = embedder or HashingEmbedder()
    log = log or (lambda msg: None)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    docs = load_documents(docs_dir)
    units = chunk_documents(docs, config.chunk_size, config.chunk_overlap)
    log(f"chunked {len(docs)} documents into {len(units)} text units")

    extractions: list[ExtractionResult] = [
        extract_from_unit(llm, u, config.entity_types, config.max_gleanings) for u in units
    ]
    raw_entities = [e for ex in extractions for e in ex.entities]
    log(f"extracted {len(raw_entities)} entity mentions, "
        f"{sum(len(ex.relationships) for ex in extractions)} relationship mentions")

    claims = [c for u in units for c in extract_claims(llm, u, config.entity_types)] if config.extract_claims else []

    name_map = resolve_entities(raw_entities, alias_threshold=config.alias_threshold)
    G = build_graph(extractions, llm=llm, name_map=name_map, summarize_max_tokens=config.summarize_max_tokens)
    for c in claims:
        c.subject, c.object = name_map.get(c.subject, c.subject), name_map.get(c.object, c.object)
    log(f"graph: {G.number_of_nodes()} entities, {G.number_of_edges()} relationships")

    communities = hierarchical_communities(G, config.max_cluster_size, config.seed)
    reports = generate_all_reports(llm, G, communities, config.report_max_tokens)
    log(f"{len(communities)} communities, {len(reports)} reports")

    entity_store = _embed_store(
        embedder, list(G.nodes()), [entity_embedding_text(n, d) for n, d in G.nodes(data=True)],
        [{"human_id": d["human_id"]} for _, d in G.nodes(data=True)])
    relationship_store = _embed_store(
        embedder, [str(d["human_id"]) for _, _, d in G.edges(data=True)],
        [relationship_embedding_text(u, v, d) for u, v, d in G.edges(data=True)],
        [{"source": u, "target": v} for u, v in G.edges()])
    text_unit_store = _embed_store(embedder, [u.id for u in units], [u.text for u in units],
                                   [{"doc_id": u.doc_id} for u in units])
    report_store = _embed_store(embedder, [str(r.community_id) for r in reports],
                                [r.full_content for r in reports], [{"level": r.level} for r in reports])

    index = Index(G, {u.id: u for u in units}, communities, reports, claims, entity_store,
                  relationship_store, text_unit_store, report_store, embedder, config)
    save_index(index, out)
    log(f"saved index to {out}")
    return index


# --------------------------------------------------------------------------- persistence


def save_index(index: Index, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    G = index.graph

    def dump(name: str, obj) -> None:
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False))

    dump("config.json", {**asdict(index.config), "embedder": getattr(index.embedder, "name", "hashing")})
    dump("text_units.json", [u.to_dict() for u in index.text_units.values()])
    dump("entities.json", [{"name": n, **d} for n, d in G.nodes(data=True)])
    dump("relationships.json", [{"source": u, "target": v, **d} for u, v, d in G.edges(data=True)])
    dump("communities.json", [c.to_dict() for c in index.communities])
    dump("community_reports.json", [{**r.to_dict(), "full_content": r.full_content} for r in index.reports])
    dump("claims.json", [c.to_dict() for c in index.claims])

    # GraphML only supports scalar attributes, so lists are JSON-encoded (open it in Gephi/yEd).
    export = nx.Graph()
    for n, d in G.nodes(data=True):
        export.add_node(n, **{k: json.dumps(v) if isinstance(v, list) else v for k, v in d.items()})
    for u, v, d in G.edges(data=True):
        export.add_edge(u, v, **{k: json.dumps(x) if isinstance(x, list) else x for k, x in d.items()})
    nx.write_graphml(export, out / "graph.graphml")

    for name in ("entity", "relationship", "text_unit", "report"):
        getattr(index, f"{name}_store").save(out / f"{name}_embeddings")


def load_index(out_dir: str | Path, embedder: Embedder | None = None) -> Index:
    """Load artifacts written by `build_index`. The embedder is rebuilt from config unless given."""
    out = Path(out_dir)
    load = lambda name: json.loads((out / name).read_text())  # noqa: E731
    cfg = load("config.json")
    embedder_name = cfg.pop("embedder", "hashing")
    config = IndexConfig(**{k: v for k, v in cfg.items() if k in IndexConfig.__dataclass_fields__})
    embedder = embedder or get_embedder(embedder_name)

    G = nx.Graph()
    for e in load("entities.json"):
        G.add_node(e.pop("name"), **e)
    for r in load("relationships.json"):
        G.add_edge(r.pop("source"), r.pop("target"), **r)

    communities = [Community(**{**c, "edges": [tuple(e) for e in c["edges"]]}) for c in load("communities.json")]
    reports = [CommunityReport(**{k: v for k, v in r.items() if k != "full_content"}) for r in load("community_reports.json")]
    claims = [Claim(**c) for c in load("claims.json")]
    units = {u["id"]: TextUnit(**u) for u in load("text_units.json")}
    stores = {name: VectorStore.load(out / f"{name}_embeddings") for name in ("entity", "relationship", "text_unit", "report")}
    return Index(G, units, communities, reports, claims, stores["entity"], stores["relationship"],
                 stores["text_unit"], stores["report"], embedder, config)
