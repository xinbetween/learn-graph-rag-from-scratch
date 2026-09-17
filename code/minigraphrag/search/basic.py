"""Baseline vector RAG: embed the question, take the nearest chunks, answer.

This is the method GraphRAG is compared against. It is great at single-hop
lookups ("How far is Halden Reef from Port Avalon?") and weak when the answer
is spread across documents that don't look like the question.
"""

from __future__ import annotations

from ..context import format_table
from ..llm import LLM
from ..tokens import count_tokens
from .common import DEFAULT_RESPONSE_TYPE, SearchResult, doc_ids_for_units, generate_answer


def basic_search(index, query: str, llm: LLM, top_k: int = 5, max_context_tokens: int = 4000,
                 response_type: str = DEFAULT_RESPONSE_TYPE) -> SearchResult:
    hits = index.text_unit_store.search(index.embedder.embed([query])[0], k=top_k)
    rows, used = [], 0
    for unit_id, score, _ in hits:
        text = index.text_units[unit_id].text
        if used + count_tokens(text) > max_context_tokens:
            break
        rows.append([unit_id, text])
        used += count_tokens(text)
    context = format_table("Sources", ["id", "text"], rows)
    answer = generate_answer(llm, query, context, response_type)
    return SearchResult(answer, "basic", context, {"sources": [{"id": r[0], "text": r[1]} for r in rows]},
                        doc_ids_for_units(index, [r[0] for r in rows]), llm_calls=1)
