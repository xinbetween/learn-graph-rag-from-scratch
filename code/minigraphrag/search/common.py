"""Pieces shared by every search method."""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import prompts as P
from ..llm import LLM

DEFAULT_RESPONSE_TYPE = "multiple paragraphs"


@dataclass
class SearchResult:
    answer: str
    method: str
    context_text: str = ""
    context_data: dict = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)  # document ids that reached the context
    llm_calls: int = 0


def generate_answer(llm: LLM, query: str, context_text: str, response_type: str = DEFAULT_RESPONSE_TYPE) -> str:
    """Final generation step: the context goes into the system prompt, the question is the user turn."""
    system = P.LOCAL_SEARCH_SYSTEM_PROMPT.format(context_data=context_text, response_type=response_type)
    return llm.complete(query, system=system)


def doc_ids_for_units(index, unit_ids) -> list[str]:
    """Distinct document ids, in first-seen order, for a sequence of text unit ids."""
    return list(dict.fromkeys(index.text_units[u].doc_id for u in unit_ids if u in index.text_units))
