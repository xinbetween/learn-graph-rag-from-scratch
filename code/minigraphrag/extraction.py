"""LLM-based entity, relationship and claim extraction.

This is where unstructured text becomes a graph. GraphRAG asks the model to
emit delimiter-separated tuples rather than JSON: tuples are cheaper, and a
single malformed record doesn't invalidate the whole response. The price is a
parser that must tolerate everything models actually produce (stray quotes,
odd casing, missing parentheses, trailing chatter).

*Gleaning* is GraphRAG's trick for recall: after the first pass, tell the
model "MANY entities were missed" and let it add more, optionally asking
"anything left? Y/N" between rounds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

from . import prompts as P
from .chunking import TextUnit
from .llm import LLM


@dataclass
class Entity:
    name: str
    type: str
    description: str
    source_id: str = ""  # TextUnit id the mention came from

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Relationship:
    source: str
    target: str
    description: str
    strength: float = 1.0
    source_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Claim:
    subject: str
    object: str
    type: str
    status: str
    start_date: str | None
    end_date: str | None
    description: str
    source_text: str
    source_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExtractionResult:
    """Everything extracted from one TextUnit."""

    unit_id: str
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    llm_calls: int = 0


def _clean_field(value: str) -> str:
    return value.strip().strip('"').strip("'").strip()


def _split_records(text: str, record_delimiter: str, completion_delimiter: str) -> list[str]:
    """Split raw output into candidate records.

    Models sometimes forget the record delimiter and use newlines, or glue
    records together as `(...)(...)`, so we split on all three.
    """
    text = text.replace(completion_delimiter, "")
    records = []
    for chunk in re.split(re.escape(record_delimiter) + r"|\n", text):
        for piece in re.split(r"(?<=\))\s*(?=\()", chunk):
            piece = piece.strip()
            if "(" in piece and ")" in piece:  # drop chatter around the parentheses
                piece = piece[piece.index("(") : piece.rindex(")") + 1]
            if piece:
                records.append(piece)
    return records


def parse_extraction_output(
    text: str,
    source_id: str = "",
    tuple_delimiter: str = P.TUPLE_DELIMITER,
    record_delimiter: str = P.RECORD_DELIMITER,
    completion_delimiter: str = P.COMPLETION_DELIMITER,
) -> tuple[list[Entity], list[Relationship]]:
    """Parse `("entity"<|>...)##("relationship"<|>...)` output. Bad records are skipped, not fatal."""
    entities, relationships = [], []
    for record in _split_records(text, record_delimiter, completion_delimiter):
        record = record.strip()
        if record.startswith("(") and record.endswith(")"):
            record = record[1:-1]
        fields = [_clean_field(f) for f in record.split(tuple_delimiter)]
        kind = fields[0].lower()
        if kind == "entity" and len(fields) >= 4 and fields[1]:
            entities.append(Entity(fields[1].upper(), fields[2].upper().replace(" ", "_"),
                                   tuple_delimiter.join(fields[3:]), source_id))
        elif kind == "relationship" and len(fields) >= 4 and fields[1] and fields[2]:
            strength = 1.0
            desc_fields = fields[3:]
            if len(fields) >= 5:
                try:
                    strength = float(re.sub(r"[^\d.]", "", fields[-1]) or "1")
                    desc_fields = fields[3:-1]
                except ValueError:
                    pass
            relationships.append(Relationship(fields[1].upper(), fields[2].upper(),
                                              tuple_delimiter.join(desc_fields), strength, source_id))
    return entities, relationships


def extract_from_unit(
    llm: LLM, unit: TextUnit, entity_types: list[str] | None = None, max_gleanings: int = 1
) -> ExtractionResult:
    """Extract entities/relationships from one chunk, with up to `max_gleanings` extra passes.

    Our LLM interface is single-turn, so the "conversation" is replayed by
    concatenating: original prompt + previous answers + follow-up instruction.
    """
    types = ",".join(entity_types or P.DEFAULT_ENTITY_TYPES)
    prompt = P.ENTITY_EXTRACTION_PROMPT.format(
        entity_types=types, input_text=unit.text, tuple_delimiter=P.TUPLE_DELIMITER,
        record_delimiter=P.RECORD_DELIMITER, completion_delimiter=P.COMPLETION_DELIMITER,
    )
    response = llm.complete(prompt)
    calls, transcript, outputs = 1, prompt + response, [response]
    for i in range(max_gleanings):
        more = llm.complete(transcript + P.GLEANING_CONTINUE_PROMPT)
        calls += 1
        outputs.append(more)
        transcript += P.GLEANING_CONTINUE_PROMPT + more
        if i >= max_gleanings - 1:
            break  # no point asking "anything left?" if we won't act on it
        answer = llm.complete(transcript + P.GLEANING_LOOP_CHECK_PROMPT)
        calls += 1
        if answer.strip().upper()[:1] != "Y":
            break

    result = ExtractionResult(unit.id, llm_calls=calls)
    for out in outputs:
        ents, rels = parse_extraction_output(out, source_id=unit.id)
        result.entities.extend(ents)
        result.relationships.extend(rels)
    return result


def parse_claims_output(text: str, source_id: str = "") -> list[Claim]:
    """Parse claim tuples: (subject<|>object<|>type<|>status<|>start<|>end<|>description<|>source)."""
    claims = []
    for record in _split_records(text, P.RECORD_DELIMITER, P.COMPLETION_DELIMITER):
        fields = [_clean_field(f) for f in record.strip().strip("()").split(P.TUPLE_DELIMITER)]
        if len(fields) < 8:
            continue
        none = lambda v: None if v.upper() in ("NONE", "") else v  # noqa: E731
        claims.append(Claim(fields[0].upper(), fields[1].upper(), fields[2].upper(), fields[3].upper(),
                            none(fields[4]), none(fields[5]), fields[6], fields[7], source_id))
    return claims


def extract_claims(
    llm: LLM,
    unit: TextUnit,
    entity_specs: list[str] | None = None,
    claim_description: str = "Any claims or facts about the entity, especially dated events, roles and transactions",
) -> list[Claim]:
    """Extract dated, attributable claims ("covariates" in GraphRAG) from one chunk."""
    prompt = P.CLAIM_EXTRACTION_PROMPT.format(
        entity_specs=", ".join(entity_specs or P.DEFAULT_ENTITY_TYPES), claim_description=claim_description,
        input_text=unit.text, tuple_delimiter=P.TUPLE_DELIMITER, record_delimiter=P.RECORD_DELIMITER,
        completion_delimiter=P.COMPLETION_DELIMITER,
    )
    return parse_claims_output(llm.complete(prompt), source_id=unit.id)
