"""Token counting.

Every stage of GraphRAG works against a *token budget*: chunks have a size,
community reports must fit a context window, search contexts are split into
proportional slices. We therefore need one function that answers "how many
tokens is this?" consistently everywhere.

If `tiktoken` is installed (and its encoding files are available) we use it,
because that is what OpenAI-style models actually count. Otherwise we fall back
to a cheap estimate: roughly 4 tokens for every 3 words. The estimate is wrong
for any single string but close on average, which is all budgeting needs.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache

_WORD_RE = re.compile(r"\S+")


@lru_cache(maxsize=1)
def _encoder():
    try:
        import tiktoken  # optional dependency

        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # not installed, or offline and encodings not cached
        return None


def count_tokens(text: str) -> int:
    """Return the number of tokens in `text` (tiktoken if available, else an estimate)."""
    if not text:
        return 0
    enc = _encoder()
    if enc is not None:
        return len(enc.encode(text))
    return math.ceil(len(_WORD_RE.findall(text)) * 4 / 3)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Cut `text` so that it fits in `max_tokens` (word-boundary cut in fallback mode)."""
    if count_tokens(text) <= max_tokens:
        return text
    enc = _encoder()
    if enc is not None:
        return enc.decode(enc.encode(text)[:max_tokens])
    words = text.split()
    return " ".join(words[: max(0, int(max_tokens * 3 / 4))])
