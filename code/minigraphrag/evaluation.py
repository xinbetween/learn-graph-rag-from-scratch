"""Evaluating RAG systems.

Three complementary signals:
- answer overlap with a gold answer (exact match, token F1): cheap but harsh
  on long, correct answers;
- context recall: did retrieval surface the documents that contain the answer?
  This isolates retrieval quality from generation quality;
- LLM-as-judge pairwise comparison on the GraphRAG paper's criteria
  (comprehensiveness, diversity, empowerment, directness), the standard way to
  compare answers to open-ended "global" questions that have no single gold string.
"""

from __future__ import annotations

import json
import re
import string
from collections import Counter
from pathlib import Path
from typing import Callable

from . import prompts as P
from .llm import LLM, parse_json_response


def normalize_answer(text: str) -> str:
    """SQuAD-style normalisation: lowercase, strip punctuation, articles and extra whitespace."""
    text = text.lower()
    text = "".join(ch for ch in text if ch not in set(string.punctuation))
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def exact_match(prediction: str, gold: str) -> float:
    return float(normalize_answer(prediction) == normalize_answer(gold))


def token_f1(prediction: str, gold: str) -> float:
    pred, ref = normalize_answer(prediction).split(), normalize_answer(gold).split()
    common = Counter(pred) & Counter(ref)
    overlap = sum(common.values())
    if not pred or not ref or overlap == 0:
        return 0.0
    precision, recall = overlap / len(pred), overlap / len(ref)
    return 2 * precision * recall / (precision + recall)


def context_recall(retrieved_doc_ids: list[str], supporting_docs: list[str]) -> float:
    """Fraction of the supporting documents that made it into the context."""
    if not supporting_docs:
        return 1.0
    return len(set(retrieved_doc_ids) & set(supporting_docs)) / len(set(supporting_docs))


def load_questions(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def llm_judge_pairwise(
    llm: LLM,
    question: str,
    answer_a: str,
    answer_b: str,
    criteria: tuple[str, ...] = ("comprehensiveness", "diversity", "empowerment", "directness"),
    swap: bool = True,
) -> dict[str, dict]:
    """Per criterion, which answer wins: {"comprehensiveness": {"winner": "A"|"B"|"TIE", "reasoning": ...}}.

    LLM judges prefer whichever answer they read first. With `swap=True` we ask
    twice with the order reversed and only declare a winner if both agree.
    """
    results = {}
    for criterion in criteria:
        def ask(a: str, b: str) -> dict:
            prompt = P.PAIRWISE_JUDGE_PROMPT.format(criterion=criterion, question=question, answer_a=a, answer_b=b,
                                                    criterion_description=P.CRITERIA_DESCRIPTIONS.get(criterion, ""))
            return parse_json_response(llm.complete(prompt, json=True))

        first = ask(answer_a, answer_b)
        winner = str(first.get("winner", "TIE")).upper()
        if swap:
            second = str(ask(answer_b, answer_a).get("winner", "TIE")).upper()
            flipped = {"A": "B", "B": "A"}.get(second, "TIE")
            winner = winner if winner == flipped else "TIE"
        results[criterion] = {"winner": winner, "reasoning": first.get("reasoning", "")}
    return results


def run_eval(questions: list[dict], systems: dict[str, Callable[[str], object]]) -> dict:
    """Run every system on every question.

    `systems` maps a name to a function `question -> SearchResult` (anything with
    `.answer` and `.sources`). Returns per-question rows and per-system means,
    overall and by question type.
    """
    rows = []
    for q in questions:
        for name, fn in systems.items():
            result = fn(q["question"])
            rows.append({
                "id": q["id"], "type": q.get("type", ""), "system": name, "answer": result.answer,
                "exact_match": exact_match(result.answer, q["answer"]),
                "token_f1": token_f1(result.answer, q["answer"]),
                "context_recall": context_recall(getattr(result, "sources", []), q.get("supporting_docs", [])),
            })
    summary: dict[str, dict] = {}
    for name in systems:
        mine = [r for r in rows if r["system"] == name]
        groups = {"all": mine, **{t: [r for r in mine if r["type"] == t] for t in sorted({r["type"] for r in mine})}}
        summary[name] = {
            g: {m: round(sum(r[m] for r in rs) / len(rs), 3) for m in ("exact_match", "token_f1", "context_recall")}
            | {"n": len(rs)}
            for g, rs in groups.items() if rs
        }
    return {"rows": rows, "summary": summary}


def format_summary(result: dict) -> str:
    """Plain-text table of the per-system means."""
    lines = [f"{'system':<10} {'group':<11} {'n':>3} {'EM':>6} {'F1':>6} {'ctx_recall':>10}"]
    for name, groups in result["summary"].items():
        for g, s in groups.items():
            lines.append(f"{name:<10} {g:<11} {s['n']:>3} {s['exact_match']:>6.2f} {s['token_f1']:>6.2f} {s['context_recall']:>10.2f}")
    return "\n".join(lines)
