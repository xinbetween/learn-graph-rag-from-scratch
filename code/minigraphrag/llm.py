"""LLM clients behind one tiny interface.

GraphRAG calls an LLM for many different jobs (extract, summarise, write
reports, rate, answer). The pipeline only needs one method:

    complete(prompt, system=None, json=False) -> str

so swapping OpenAI for Claude for a local Ollama model is a one-line change.
`MockLLM` implements the same interface with deterministic heuristics, which is
what lets the whole course run offline, in CI, and for free.
"""

from __future__ import annotations

import hashlib
import json as jsonlib
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Protocol

from . import prompts as P
from .chunking import split_sentences
from .context import parse_tables
from .embeddings import simple_tokenize


class LLM(Protocol):
    def complete(self, prompt: str, system: str | None = None, json: bool = False) -> str: ...


def parse_json_response(text: str) -> dict:
    """Pull the first JSON object out of an LLM reply (models love code fences)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return jsonlib.loads(text)
    except jsonlib.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return jsonlib.loads(text[start : end + 1])
            except jsonlib.JSONDecodeError:
                pass
    return {}


# --------------------------------------------------------------------------- real providers


class OpenAICompatibleLLM:
    """Any OpenAI-compatible chat endpoint: OpenAI, Ollama, vLLM, LM Studio...

    Ollama:  OpenAICompatibleLLM("llama3.1", base_url="http://localhost:11434/v1", api_key="ollama")
    """

    def __init__(self, model: str = "gpt-4o-mini", base_url: str | None = None,
                 api_key: str | None = None, temperature: float = 0.0):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model, self.temperature = model, temperature
        self.name = f"openai:{model}"

    def complete(self, prompt: str, system: str | None = None, json: bool = False) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        kwargs = {"response_format": {"type": "json_object"}} if json else {}
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=self.temperature, **kwargs
        )
        return resp.choices[0].message.content or ""


class AnthropicLLM:
    """Claude via the official Anthropic SDK.

    Note: current Claude models reject sampling parameters such as `temperature`,
    so we don't send any. JSON mode is requested through the system prompt.
    """

    def __init__(self, model: str = "claude-sonnet-5", api_key: str | None = None, max_tokens: int = 16000):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model, self.max_tokens = model, max_tokens
        self.name = f"anthropic:{model}"

    def complete(self, prompt: str, system: str | None = None, json: bool = False) -> str:
        if json:
            system = (system or "") + "\nRespond with a single valid JSON object and nothing else."
        kwargs = {"system": system} if system else {}
        resp = self.client.messages.create(
            model=self.model, max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}], **kwargs,
        )
        if resp.stop_reason == "refusal":
            return ""
        return "".join(block.text for block in resp.content if block.type == "text")


class CachedLLM:
    """Wrap any LLM with a disk cache keyed by a hash of (model, system, prompt, json).

    Indexing a corpus makes hundreds of calls; re-running after a code change
    should not pay for them again. Deterministic prompts make this safe.
    """

    def __init__(self, llm: LLM, cache_dir: str | Path = ".cache/llm"):
        self.llm = llm
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.name = getattr(llm, "name", type(llm).__name__)
        self.hits = self.misses = 0

    def complete(self, prompt: str, system: str | None = None, json: bool = False) -> str:
        key = hashlib.sha256(jsonlib.dumps([self.name, system, prompt, json]).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            self.hits += 1
            return jsonlib.loads(path.read_text())["response"]
        self.misses += 1
        response = self.llm.complete(prompt, system=system, json=json)
        path.write_text(jsonlib.dumps({"response": response}))
        return response


# --------------------------------------------------------------------------- mock

# A gazetteer stands in for the world knowledge a real LLM brings to extraction.
# It contains *surface forms*, including aliases, so entity resolution still has
# real work to do ("Okafor" vs "Dr. Mira Okafor", "TWI" vs "Tidewater Institute").
MOCK_GAZETTEER = {
    "Kestrel Labs": "ORGANIZATION", "Kestrel": "ORGANIZATION",
    "Tidewater Institute": "ORGANIZATION", "Tidewater": "ORGANIZATION", "TWI": "ORGANIZATION",
    "Brightwater Capital": "ORGANIZATION", "Brightwater": "ORGANIZATION",
    "Marlow Dynamics": "ORGANIZATION", "Marlow": "ORGANIZATION", "Deepcast": "ORGANIZATION",
    "Port Avalon City Council": "ORGANIZATION",
    "Dr. Mira Okafor": "PERSON", "Mira Okafor": "PERSON", "Okafor": "PERSON",
    "Jonas Vehl": "PERSON", "Vehl": "PERSON", "Priya Nair": "PERSON", "Nair": "PERSON",
    "Dr. Ana Ruiz": "PERSON", "Ana Ruiz": "PERSON", "Lena Park": "PERSON",
    "Project Sentinel": "PROJECT", "Sentinel": "PROJECT", "Project Tern": "PROJECT", "Tern": "PROJECT",
    "Halden Reef": "LOCATION", "Port Avalon": "LOCATION",
    "2024 Halden Reef bleaching event": "EVENT", "Halden Reef bleaching event": "EVENT",
    "bleaching event": "EVENT", "Ocean Health Act": "LAW",
}
# Heuristic typing for capitalised phrases the gazetteer does not know.
_SUFFIX_TYPES = {"Labs": "ORGANIZATION", "Institute": "ORGANIZATION", "Capital": "ORGANIZATION",
                 "Dynamics": "ORGANIZATION", "Council": "ORGANIZATION", "Act": "LAW", "Reef": "LOCATION"}
_CAP_PHRASE = re.compile(r"\b(?:Dr\.\s+)?[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+")
_RELATION_CUES = re.compile(
    r"found|acquir|invest|led |leads|lead |partner|suppl|replac|detect|contract|director|board|joined|"
    r"CTO|CEO|chief|monitor|runs|designed|compet|require|research", re.I)
_BROAD = {"theme", "main", "overall", "risk", "summarize", "summary", "trend", "evolved", "role", "relationship"}


def find_mentions(text: str) -> list[tuple[int, int, str, str]]:
    """(start, end, surface, type) for every entity mention, longest match first."""
    found: list[tuple[int, int, str, str]] = []
    taken = [False] * len(text)
    surfaces = sorted(MOCK_GAZETTEER, key=len, reverse=True)
    for surface in surfaces:
        variants = [surface] + ([surface.upper()] if " " not in surface and surface.upper() != surface else [])
        for variant in variants:
            for m in re.finditer(r"(?<![\w.])" + re.escape(variant) + r"(?!\w)", text):
                if not any(taken[m.start() : m.end()]):
                    found.append((m.start(), m.end(), surface, MOCK_GAZETTEER[surface]))
                    taken[m.start() : m.end()] = [True] * (m.end() - m.start())
    masked = "".join("#" if t else c for c, t in zip(text, taken))
    for m in _CAP_PHRASE.finditer(masked):
        words = m.group().split()
        etype = ("PERSON" if words[0] == "Dr." else "PROJECT" if words[0] == "Project"
                 else _SUFFIX_TYPES.get(words[-1]))
        if etype:
            found.append((m.start(), m.end(), m.group(), etype))
    return sorted(found)


def _clean_sentence(raw: str) -> str:
    """Collapse whitespace and strip markdown decoration (#, *, >)."""
    return " ".join(raw.replace("**", "").split()).strip("#*>- ")


def _between(text: str, start: str, end: str) -> str:
    i = text.rfind(start)
    if i == -1:
        return ""
    i += len(start)
    j = text.find(end, i)
    return text[i : j if j != -1 else len(text)].strip()


def _overlap(query: str, text: str) -> int:
    return len(set(simple_tokenize(query)) & set(simple_tokenize(text)))


class MockLLM:
    """Deterministic offline LLM that recognises each prompt by its marker.

    It is intentionally a little "lazy": the first extraction pass omits weak
    co-occurrence relationships, and only the gleaning pass adds them, so the
    effect of gleaning is observable in tests.
    """

    name = "mock"

    def __init__(self):
        self.calls = 0

    def complete(self, prompt: str, system: str | None = None, json: bool = False) -> str:
        self.calls += 1
        full = f"{system or ''}\n{prompt}"
        for task, marker in P.MARKERS.items():
            if marker in full:
                return getattr(self, f"_{task}")(full, prompt)
        return "OK"

    # ---- indexing tasks
    def _records(self, text: str) -> list[str]:
        """All extraction records for a text: entities first, then relationships."""
        d = P.TUPLE_DELIMITER
        entities: dict[str, dict] = {}
        rels: dict[tuple[str, str], dict] = {}
        for s, e in split_sentences(text):
            sentence = _clean_sentence(text[s:e])
            ms = find_mentions(sentence)
            names = []
            for ms_start, ms_end, surface, etype in ms:
                name = surface.upper()
                ent = entities.setdefault(name, {"type": etype, "desc": []})
                if len(ent["desc"]) < 2 and sentence not in ent["desc"]:
                    ent["desc"].append(sentence)
                if name not in [n for n, _, _ in names]:
                    names.append((name, ms_start, ms_end))
            for i, (a, a_start, a_end) in enumerate(names[:5]):
                for b, b_start, _ in names[i + 1 : 5]:
                    if set(a.split()) <= set(b.split()) or set(b.split()) <= set(a.split()):
                        continue  # "KESTREL" and "KESTREL LABS" are the same thing, not a relation
                    cue = bool(_RELATION_CUES.search(sentence[a_start:b_start + 1] or sentence))
                    strength = min(10, 2 + (6 if cue else 0) + (1 if b_start - a_end < 40 else 0))
                    r = rels.setdefault((a, b), {"desc": [], "strength": 0})
                    if sentence not in r["desc"]:
                        r["desc"].append(sentence)
                    r["strength"] = max(r["strength"], strength)
        out = [f'("entity"{d}{n}{d}{v["type"]}{d}{" ".join(v["desc"])})' for n, v in entities.items()]
        out += [f'("relationship"{d}{a}{d}{b}{d}{" ".join(v["desc"][:2])}{d}{v["strength"]})'
                for (a, b), v in rels.items()]
        return out

    def _extraction_text(self, full: str) -> str:
        return _between(full, "-Real Data-", "\n######################\nOutput:").split("Text:", 1)[-1].strip()

    def _extraction(self, full: str, prompt: str) -> str:
        first_pass = [r for r in self._records(self._extraction_text(full))
                      if r.startswith('("entity"') or int(r.rstrip(")").split(P.TUPLE_DELIMITER)[-1]) >= 5]
        return f"\n{P.RECORD_DELIMITER}\n".join(first_pass) + f"\n{P.COMPLETION_DELIMITER}"

    def _missing(self, full: str) -> list[str]:
        return [r for r in self._records(self._extraction_text(full)) if r not in full.split("-Real Data-")[-1]]

    def _continue(self, full: str, prompt: str) -> str:
        return f"\n{P.RECORD_DELIMITER}\n".join(self._missing(full)) + f"\n{P.COMPLETION_DELIMITER}"

    def _loop_check(self, full: str, prompt: str) -> str:
        return "Y" if self._missing(full) else "N"

    def _claims(self, full: str, prompt: str) -> str:
        d, text = P.TUPLE_DELIMITER, self._extraction_text(full)
        out = []
        for s, e in split_sentences(text):
            sentence = _clean_sentence(text[s:e])
            year = re.search(r"\b(?:(January|February|March|April|May|June|July|August|September|October|"
                             r"November|December)\s+)?(20\d\d)\b", sentence)
            ents = [m[2].upper() for m in find_mentions(sentence)]
            if not year or not ents:
                continue
            month = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                     "October", "November", "December"].index(year.group(1)) + 1 if year.group(1) else 1
            ctype = next((t for pat, t in [("acquir", "ACQUISITION"), ("invest|raise|Series", "FUNDING"),
                                           ("CTO|CEO|chief|Chief|director|Director", "LEADERSHIP"),
                                           ("suppl", "SUPPLY")] if re.search(pat, sentence)), "EVENT")
            obj = ents[1] if len(ents) > 1 else "NONE"
            out.append(f"({ents[0]}{d}{obj}{d}{ctype}{d}TRUE{d}{year.group(2)}-{month:02d}-01{d}NONE{d}{sentence}{d}{sentence})")
        return f"\n{P.RECORD_DELIMITER}\n".join(out) + f"\n{P.COMPLETION_DELIMITER}"

    def _summarize(self, full: str, prompt: str) -> str:
        try:
            descriptions = jsonlib.loads(_between(full, "Description List:", "\n#######"))
        except jsonlib.JSONDecodeError:
            descriptions = [_between(full, "Description List:", "\n#######")]
        limit = int((re.search(r"under (\d+) tokens", full) or [0, 150])[1])
        seen, kept, words = set(), [], 0
        for desc in descriptions:
            for s, e in split_sentences(desc):
                sent = desc[s:e].strip()
                if sent.lower() not in seen and words + len(sent.split()) <= limit * 3 / 4:
                    seen.add(sent.lower())
                    kept.append(sent)
                    words += len(sent.split())
        return " ".join(kept) or " ".join(descriptions)[:500]

    def _report(self, full: str, prompt: str) -> str:
        tables = parse_tables(_between(full, "Text:", "\nOutput:"))
        ents = tables.get("Entities", [])
        rels = sorted(tables.get("Relationships", []), key=lambda r: -float(r.get("combined_degree") or 0))
        subs = tables.get("Reports", [])
        names = [e["entity"].title() for e in ents[:3]] or [s["title"] for s in subs[:2]]
        title = " and ".join(names[:2]) if names else "Unnamed community"
        summary = f"This community centres on {', '.join(names)}."
        if ents:
            summary += " " + ents[0].get("description", "")[:300]
        elif subs:
            summary += " " + " ".join(s.get("summary", "")[:200] for s in subs[:2])
        findings = [{"summary": f"{r['source'].title()} and {r['target'].title()}",
                     "explanation": f"{r['description'][:400]} [Data: Relationships ({r['id']})]"} for r in rels[:5]]
        findings += [{"summary": s["title"], "explanation": s.get("summary", "")} for s in subs[:3]]
        if not findings and ents:
            findings = [{"summary": e["entity"].title(), "explanation": f"{e['description'][:300]} [Data: Entities ({e['id']})]"}
                        for e in ents[:3]]
        rating = round(min(10.0, 2 + 0.5 * (len(rels) + len(subs))), 1)
        return jsonlib.dumps({"title": title, "summary": summary, "rating": rating,
                              "rating_explanation": f"Rated {rating} based on {len(rels)} relationships among {len(ents)} entities.",
                              "findings": findings})

    # ---- query tasks
    def _map(self, full: str, prompt: str) -> str:
        question = _between(full, "---Question---", "\n---")
        broad = bool(_BROAD & set(simple_tokenize(question)))
        points = []
        for row in parse_tables(_between(full, "---Data tables---", "---Question---")).get("Reports", []):
            text = f"{row.get('title', '')} {row.get('content', '')}"
            ov = _overlap(question, text)
            score = min(100, 40 + 10 * ov) if broad else min(100, 25 * ov)
            if score > 0:
                body = row.get("content", "").split(row.get("title", ""), 1)[-1]
                spans = split_sentences(body)
                first = " ".join(_clean_sentence(body[a:b]) for a, b in spans[:2])[:400]
                points.append({"description": f"{row.get('title', '')}: {first} [Data: Reports ({row.get('id')})]",
                               "score": score})
        return jsonlib.dumps({"points": points})

    def _reduce(self, full: str, prompt: str) -> str:
        body = _between(full, "---Analyst Reports---", "\n---Question---")
        points = re.findall(r"Importance Score: (\d+)\n(.+)", body)
        points.sort(key=lambda p: -int(p[0]))
        if not points:
            return "I don't know: none of the community reports were relevant to the question."
        return "Key points from the dataset:\n" + "\n".join(f"- {text.strip()}" for _, text in points[:8])

    def _answer(self, full: str, prompt: str) -> str:
        """Extractive answer: the context sentences sharing the rarest words with the question."""
        question = prompt
        candidates = []
        for table, rows in parse_tables(_between(full, "---Data tables---", "\n---Question---")).items():
            for row in rows:
                text = row.get("text") or row.get("content") or row.get("description") or row.get("summary") or ""
                for paragraph in re.split(r"\s{2,}", text):  # table cells turned newlines into spaces
                    for s, e in split_sentences(paragraph):
                        sent = _clean_sentence(paragraph[s:e])
                        if len(sent) > 30 and sent[-1] in ".!?\"":  # skip headings and metadata lines
                            candidates.append((sent, table, row.get("id", "")))
        q = set(simple_tokenize(question))
        df = Counter(t for sent, _, _ in candidates for t in set(simple_tokenize(sent)) & q)
        n = max(1, len(candidates))
        scored = []
        for sent, table, rid in candidates:
            score = sum(math.log(1 + n / df[t]) for t in set(simple_tokenize(sent)) & q)
            if score > 0:
                scored.append((score, sent, table, rid))
        scored.sort(key=lambda x: -x[0])
        seen, parts = set(), []
        for _, sent, table, rid in scored:
            if sent.lower() not in seen:
                seen.add(sent.lower())
                parts.append(f"{sent} [Data: {table} ({rid})]")
            if len(parts) == 5:
                break
        return " ".join(parts) if parts else "I don't know based on the provided data."

    def _keywords(self, full: str, prompt: str) -> str:
        query = _between(full, "---Query---", "\n---") or prompt
        low = list(dict.fromkeys(m[2] for m in find_mentions(query)))
        low_tokens = set(simple_tokenize(" ".join(low)))
        high = [t for t in dict.fromkeys(simple_tokenize(query)) if t not in low_tokens]
        return jsonlib.dumps({"high_level_keywords": high, "low_level_keywords": low})

    def _rating(self, full: str, prompt: str) -> str:
        question = _between(full, "---Question---", "\n---")
        report = _between(full, "---Report---", "---Question---")
        ov = _overlap(question, report)
        rating = 3 if _BROAD & set(simple_tokenize(question)) else min(5, ov)
        return jsonlib.dumps({"rating": rating, "reason": f"{ov} overlapping terms"})

    def _drift_primer(self, full: str, prompt: str) -> str:
        question = _between(full, "---Question---", "\n---")
        reports = _between(full, "---Community reports---", "---Question---")
        entities = list(dict.fromkeys(m[2] for m in find_mentions(question))) or \
            list(dict.fromkeys(m[2] for m in find_mentions(reports)))[:3]
        answer = self._answer(f"---Data tables---\n{reports}\n---Question---", question)
        return jsonlib.dumps({"intermediate_answer": answer,
                              "follow_up_queries": [f"What is the role of {e} in: {question}" for e in entities[:3]],
                              "score": 50})

    def _text2cypher(self, full: str, prompt: str) -> str:
        question = _between(full, "Question:", "\nCypher:")
        names = [m[2].upper() for m in find_mentions(question)]
        if names:
            return (f'MATCH (e:Entity {{name: "{names[0]}"}})-[r]-(n:Entity) '
                    "RETURN e.name, type(r), r.description, n.name LIMIT 25")
        return "MATCH (n:Entity) RETURN n.name, n.description LIMIT 10"

    def _judge(self, full: str, prompt: str) -> str:
        criterion = _between(full, "---Criterion---", ":")
        a = _between(full, "---Answer A---", "---Answer B---")
        b = _between(full, "---Answer B---", "---Goal---")
        measure = {"comprehensiveness": lambda x: len(set(simple_tokenize(x))),
                   "diversity": lambda x: len(split_sentences(x)),
                   "empowerment": lambda x: x.count("[Data:"),
                   "directness": lambda x: -len(x.split())}.get(criterion, lambda x: len(x))
        sa, sb = measure(a), measure(b)
        winner = "A" if sa > sb else "B" if sb > sa else "TIE"
        return jsonlib.dumps({"winner": winner, "reasoning": f"{criterion}: A={sa}, B={sb}"})


# --------------------------------------------------------------------------- factory


def get_llm(name: str = "mock", cache_dir: str | None = None) -> LLM:
    """Build an LLM from a short name, configured by environment variables.

    mock       - offline MockLLM
    openai     - OPENAI_API_KEY, optional OPENAI_MODEL (gpt-4o-mini), OPENAI_BASE_URL
    anthropic  - ANTHROPIC_API_KEY, optional ANTHROPIC_MODEL (claude-sonnet-5)
    ollama     - OLLAMA_BASE_URL (http://localhost:11434/v1), OLLAMA_MODEL (llama3.1)
    """
    if name == "mock":
        llm: LLM = MockLLM()
    elif name == "openai":
        llm = OpenAICompatibleLLM(os.getenv("OPENAI_MODEL", "gpt-4o-mini"), base_url=os.getenv("OPENAI_BASE_URL"))
    elif name == "anthropic":
        llm = AnthropicLLM(os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"))
    elif name == "ollama":
        llm = OpenAICompatibleLLM(os.getenv("OLLAMA_MODEL", "llama3.1"),
                                  base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), api_key="ollama")
    else:
        raise ValueError(f"unknown llm {name!r}")
    return CachedLLM(llm, cache_dir) if cache_dir else llm
