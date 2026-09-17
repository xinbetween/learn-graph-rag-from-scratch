"""GraphRAG global search (map-reduce over community reports) and DRIFT.

Global questions ("what are the main themes?") have no single matching chunk.
Instead we ask the question of *every* community report:

  map:    split reports into batches that fit the context window; for each batch
          the LLM lists key points with a 0-100 helpfulness score;
  filter: drop points scoring below `min_score` (most batches are irrelevant);
  reduce: merge the surviving points, best first, into one answer.

Cost grows with the number of reports, so we also provide
`dynamic_community_selection`: rate reports top-down through the hierarchy and
only descend into children of relevant communities (GraphRAG's "dynamic
global search"). `drift_search` combines a global primer with local follow-ups.
"""

from __future__ import annotations

import random

from .. import prompts as P
from ..context import format_table
from ..llm import LLM, parse_json_response
from ..reports import CommunityReport
from ..tokens import count_tokens
from .common import DEFAULT_RESPONSE_TYPE, SearchResult, doc_ids_for_units
from .local import local_search

NO_DATA_ANSWER = "I am sorry but I am unable to answer this question given the provided data."


def reports_at_level(index, level: int | None = None) -> list[CommunityReport]:
    """Reports at `level`, plus leaf communities at shallower levels so every entity stays covered."""
    level = 0 if level is None else level
    by_id = {c.id: c for c in index.communities}
    chosen = []
    for r in index.reports:
        c = by_id[r.community_id]
        if c.level == level or (c.level < level and not c.children):
            chosen.append(r)
    return chosen


def _report_sources(index, reports: list[CommunityReport]) -> list[str]:
    G = index.graph
    units = [u for r in reports for n in index.community(r.community_id).nodes for u in G.nodes[n].get("source_ids", [])]
    return doc_ids_for_units(index, units)


def _batches(reports: list[CommunityReport], max_tokens: int, seed: int) -> list[list[CommunityReport]]:
    """Shuffle (so no batch is systematically all-irrelevant) and pack reports into token-bounded batches."""
    shuffled = list(reports)
    random.Random(seed).shuffle(shuffled)
    batches, current, used = [], [], 0
    for r in shuffled:
        t = count_tokens(r.full_content)
        if current and used + t > max_tokens:
            batches.append(current)
            current, used = [], 0
        current.append(r)
        used += t
    return batches + ([current] if current else [])


def _map_reduce(index, query: str, llm: LLM, reports: list[CommunityReport], max_context_tokens: int,
                min_score: int, response_type: str, seed: int, method: str, extra_calls: int = 0) -> SearchResult:
    points, calls, useful = [], extra_calls, []
    for batch in _batches(reports, max_context_tokens, seed):
        context = format_table("Reports", ["id", "title", "content", "rating"],
                               [[r.community_id, r.title, r.full_content, r.rating] for r in batch])
        data = parse_json_response(llm.complete(P.GLOBAL_MAP_PROMPT.format(context_data=context, question=query), json=True))
        calls += 1
        kept = []
        for p in data.get("points", []):
            try:
                score = int(float(p.get("score", 0)))
            except (TypeError, ValueError):
                continue
            if score >= min_score and p.get("description"):
                kept.append({"description": " ".join(str(p["description"]).split()), "score": score})
        if kept:
            useful.extend(batch)
        points.extend(kept)

    points.sort(key=lambda p: -p["score"])
    if not points:
        return SearchResult(NO_DATA_ANSWER, method, "", {"points": []}, [], calls)
    report_data = "\n\n".join(f"----Analyst {i + 1}----\nImportance Score: {p['score']}\n{p['description']}"
                              for i, p in enumerate(points))
    answer = llm.complete(P.GLOBAL_REDUCE_PROMPT.format(report_data=report_data, question=query, response_type=response_type))
    return SearchResult(answer, method, report_data, {"points": points, "reports": [r.community_id for r in useful]},
                        _report_sources(index, useful), calls + 1)


def dynamic_community_selection(index, query: str, llm: LLM, threshold: int = 2, keep_parent: bool = False,
                                max_level: int | None = None) -> tuple[list[CommunityReport], int]:
    """Top-down relevance rating. Returns (relevant reports, number of LLM calls)."""
    by_id = {c.id: c for c in index.communities}
    queue = [r for r in index.reports if by_id[r.community_id].level == 0]
    relevant: dict[int, CommunityReport] = {}
    calls = 0
    while queue:
        report = queue.pop(0)
        data = parse_json_response(llm.complete(
            P.COMMUNITY_RATING_PROMPT.format(report=report.full_content, question=query), json=True))
        calls += 1
        try:
            rating = int(data.get("rating", 0))
        except (TypeError, ValueError):
            rating = 0
        if rating < threshold:
            continue  # prune the whole subtree: children of an irrelevant community are skipped
        relevant[report.community_id] = report
        community = by_id[report.community_id]
        if max_level is not None and community.level >= max_level:
            continue
        children = [index.report(ch) for ch in community.children if index.report(ch)]
        queue.extend(children)
    # Prefer specific communities: drop a parent if at least one of its children is relevant.
    for cid in list(relevant):
        parent = by_id[cid].parent
        if not keep_parent and parent in relevant:
            relevant.pop(parent, None)
    return list(relevant.values()), calls


def global_search(index, query: str, llm: LLM, level: int | None = None, dynamic: bool = False,
                  max_context_tokens: int = 3000, min_score: int = 20,
                  response_type: str = DEFAULT_RESPONSE_TYPE, seed: int = 42) -> SearchResult:
    """Map-reduce global search over the reports at `level` (or dynamically selected reports)."""
    if dynamic:
        reports, calls = dynamic_community_selection(index, query, llm)
    else:
        reports, calls = reports_at_level(index, level), 0
    return _map_reduce(index, query, llm, reports, max_context_tokens, min_score, response_type, seed,
                       "global-dynamic" if dynamic else "global", calls)


def drift_search(index, query: str, llm: LLM, top_k_reports: int = 5, max_followups: int = 3,
                 response_type: str = DEFAULT_RESPONSE_TYPE) -> SearchResult:
    """DRIFT-style search: global primer from the nearest reports, then local follow-ups, then reduce.

    1. primer: the most similar community reports give a broad intermediate answer
       and a few follow-up questions about specific entities;
    2. follow-up: each follow-up question runs a local search;
    3. reduce: all intermediate answers are merged.
    """
    hits = index.report_store.search(index.embedder.embed([query])[0], k=top_k_reports)
    reports = [index.report(int(rid)) for rid, _, _ in hits]
    context = format_table("Reports", ["id", "title", "content"], [[r.community_id, r.title, r.full_content] for r in reports])
    primer = parse_json_response(llm.complete(P.DRIFT_PRIMER_PROMPT.format(context_data=context, question=query), json=True))
    calls = 1
    answers = [(100, str(primer.get("intermediate_answer", "")))]
    sources = _report_sources(index, reports)
    followups = [str(q) for q in primer.get("follow_up_queries", [])][:max_followups]
    for q in followups:
        result = local_search(index, q, llm)
        calls += result.llm_calls
        answers.append((80, result.answer))
        sources += [s for s in result.sources if s not in sources]
    report_data = "\n\n".join(f"----Analyst {i + 1}----\nImportance Score: {score}\n{' '.join(text.split())}"
                              for i, (score, text) in enumerate(answers) if text.strip())
    answer = llm.complete(P.GLOBAL_REDUCE_PROMPT.format(report_data=report_data, question=query, response_type=response_type))
    return SearchResult(answer, "drift", report_data, {"followups": followups, "reports": [r.community_id for r in reports]},
                        sources, calls + 1)
