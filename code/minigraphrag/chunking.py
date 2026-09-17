"""Splitting documents into TextUnits.

An LLM extracts entities far better from a few hundred tokens than from a whole
book: long inputs make models skip facts. So the first indexing step cuts each
document into overlapping windows ("text units" in GraphRAG's vocabulary).
Overlap matters because a fact that straddles a boundary ("...acquired" |
"Deepcast in April") would otherwise be lost to both chunks.

We chunk on whitespace-delimited words so that `start`/`end` are exact
character offsets into the original document (handy for citations). GraphRAG
chunks on tokenizer tokens; the idea is identical.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path

from .tokens import count_tokens


@dataclass
class TextUnit:
    """A chunk of a source document; the unit of extraction and of citation."""

    id: str
    doc_id: str
    text: str
    n_tokens: int
    start: int  # character offset (inclusive) in the document
    end: int  # character offset (exclusive)

    def to_dict(self) -> dict:
        return asdict(self)


def chunk_fixed(text: str, size: int = 300, overlap: int = 50, doc_id: str = "doc") -> list[TextUnit]:
    """Sliding window of `size` words that advances by `size - overlap` words.

    With stride = size - overlap, consecutive chunks share exactly `overlap`
    words, and a document of N words yields ceil((N - overlap) / stride) chunks.
    """
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    if not spans:
        return []
    stride = size - overlap
    units: list[TextUnit] = []
    for i, first in enumerate(range(0, len(spans), stride)):
        window = spans[first : first + size]
        start, end = window[0][0], window[-1][1]
        piece = text[start:end]
        units.append(TextUnit(f"{doc_id}-{i:03d}", doc_id, piece, count_tokens(piece), start, end))
        if first + size >= len(spans):  # this window reached the end of the document
            break
    return units


_ABBREVIATIONS = ("Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "St.", "vs.", "e.g.", "i.e.", "Inc.")


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Return (start, end) character spans of sentences, also breaking at newlines.

    Deliberately simple: split after . ! ? followed by whitespace, except after
    common abbreviations, so "Dr. Mira Okafor" stays in one sentence.
    """
    spans, start = [], 0
    for m in re.finditer(r"[.!?]+(?=\s)|\n", text):
        end = m.end()
        if m.group() != "\n" and text[:end].endswith(_ABBREVIATIONS):
            continue
        if text[start:end].strip():
            spans.append((start, end))
        start = end
    if text[start:].strip():
        spans.append((start, len(text)))
    return spans


def chunk_by_sentences(
    text: str, max_tokens: int = 300, overlap_sentences: int = 1, doc_id: str = "doc"
) -> list[TextUnit]:
    """Pack whole sentences into chunks of at most `max_tokens`.

    Never cutting a sentence in half keeps each chunk readable for the LLM; the
    trade-off is uneven chunk sizes. The last `overlap_sentences` sentences of a
    chunk are repeated at the start of the next one.
    """
    sents = split_sentences(text)
    units: list[TextUnit] = []
    i = 0
    while i < len(sents):
        j, tokens = i, 0
        while j < len(sents):
            t = count_tokens(text[sents[j][0] : sents[j][1]])
            if j > i and tokens + t > max_tokens:
                break
            tokens += t
            j += 1
        start, end = sents[i][0], sents[j - 1][1]
        piece = text[start:end].strip()
        units.append(TextUnit(f"{doc_id}-{len(units):03d}", doc_id, piece, count_tokens(piece), start, end))
        if j >= len(sents):
            break
        i = max(i + 1, j - overlap_sentences)
    return units


def load_documents(docs_dir: str | Path, pattern: str = "*.md") -> dict[str, str]:
    """Read every matching file into {doc_id: text}; doc_id is the file stem."""
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(Path(docs_dir).glob(pattern))}


def chunk_documents(
    docs: dict[str, str], size: int = 300, overlap: int = 50, method: str = "fixed"
) -> list[TextUnit]:
    """Chunk a {doc_id: text} mapping with either the fixed or sentence strategy."""
    units: list[TextUnit] = []
    for doc_id, text in docs.items():
        if method == "sentences":
            units.extend(chunk_by_sentences(text, size, 1, doc_id))
        else:
            units.extend(chunk_fixed(text, size, overlap, doc_id))
    return units
