"""Command-line interface: index, query, eval.

    python -m minigraphrag index --input data/corpus --output .index [--llm mock]
    python -m minigraphrag query --method local "Why did Kestrel Labs start Project Tern?"
    python -m minigraphrag eval --methods local,global,basic
"""

from __future__ import annotations

import argparse
import sys

from .embeddings import get_embedder
from .evaluation import format_summary, llm_judge_pairwise, load_questions, run_eval
from .indexer import IndexConfig, build_index, load_index
from .llm import get_llm
from .search.basic import basic_search
from .search.global_ import drift_search, global_search
from .search.hybrid import hybrid_search
from .search.lightrag import lightrag_search
from .search.local import local_search
from .search.ppr import hipporag_search
from .search.subgraph import subgraph_search

METHODS = ["local", "global", "drift", "basic", "lightrag", "ppr", "hybrid", "subgraph"]


def make_search(method: str, index, llm, level: int | None = None, dynamic: bool = False):
    """Return a function question -> SearchResult for the named method."""
    return {
        "local": lambda q: local_search(index, q, llm),
        "global": lambda q: global_search(index, q, llm, level=level, dynamic=dynamic),
        "drift": lambda q: drift_search(index, q, llm),
        "basic": lambda q: basic_search(index, q, llm),
        "lightrag": lambda q: lightrag_search(index, q, llm),
        "ppr": lambda q: hipporag_search(index, q, llm),
        "hybrid": lambda q: hybrid_search(index, q, llm),
        "subgraph": lambda q: subgraph_search(index, q, llm),
    }[method]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="minigraphrag", description="GraphRAG from scratch")
    sub = parser.add_subparsers(dest="command", required=True)
    llm_choices = ["mock", "openai", "anthropic", "ollama"]

    p = sub.add_parser("index", help="build an index from a folder of .md documents")
    p.add_argument("--input", default="data/corpus")
    p.add_argument("--output", default=".index")
    p.add_argument("--llm", default="mock", choices=llm_choices)
    p.add_argument("--embedder", default="hashing", help="hashing | hashing:<dim> | openai | st:<model>")
    p.add_argument("--chunk-size", type=int, default=300)
    p.add_argument("--chunk-overlap", type=int, default=50)
    p.add_argument("--max-gleanings", type=int, default=1)
    p.add_argument("--max-cluster-size", type=int, default=10)
    p.add_argument("--no-claims", action="store_true")
    p.add_argument("--cache-dir", default=None, help="cache LLM responses on disk (recommended for real LLMs)")

    q = sub.add_parser("query", help="ask a question against an index")
    q.add_argument("question")
    q.add_argument("--index", default=".index")
    q.add_argument("--method", default="local", choices=METHODS)
    q.add_argument("--llm", default="mock", choices=llm_choices)
    q.add_argument("--level", type=int, default=None, help="community level for global search")
    q.add_argument("--dynamic", action="store_true", help="dynamic community selection for global search")
    q.add_argument("--show-context", action="store_true")
    q.add_argument("--cache-dir", default=None)

    e = sub.add_parser("eval", help="run the question set against several methods")
    e.add_argument("--index", default=".index")
    e.add_argument("--questions", default="data/questions.jsonl")
    e.add_argument("--methods", default="basic,local,global,ppr,hybrid")
    e.add_argument("--llm", default="mock", choices=llm_choices)
    e.add_argument("--judge", action="store_true", help="LLM pairwise judge of the first two methods")
    e.add_argument("--limit", type=int, default=None)
    e.add_argument("--cache-dir", default=None)

    args = parser.parse_args(argv)
    llm = get_llm(args.llm, cache_dir=args.cache_dir)

    if args.command == "index":
        config = IndexConfig(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap,
                             max_gleanings=args.max_gleanings, max_cluster_size=args.max_cluster_size,
                             extract_claims=not args.no_claims)
        build_index(args.input, args.output, llm, get_embedder(args.embedder), config, log=print)
        return 0

    index = load_index(args.index)
    if args.command == "query":
        result = make_search(args.method, index, llm, args.level, args.dynamic)(args.question)
        if args.show_context:
            print("=" * 30 + " CONTEXT " + "=" * 30 + f"\n{result.context_text}\n" + "=" * 69)
        print(result.answer)
        print(f"\n[method={result.method} llm_calls={result.llm_calls} sources={', '.join(result.sources) or '-'}]")
        return 0

    questions = load_questions(args.questions)[: args.limit]
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    systems = {m: make_search(m, index, llm) for m in methods}
    result = run_eval(questions, systems)
    print(format_summary(result))
    if args.judge and len(methods) >= 2:
        a, b = methods[:2]
        wins: dict[str, dict[str, int]] = {}
        for qd in questions:
            ans = {r["system"]: r["answer"] for r in result["rows"] if r["id"] == qd["id"]}
            for crit, verdict in llm_judge_pairwise(llm, qd["question"], ans[a], ans[b]).items():
                wins.setdefault(crit, {"A": 0, "B": 0, "TIE": 0})[verdict["winner"]] += 1
        print(f"\nPairwise judge ({a} = A vs {b} = B):")
        for crit, counts in wins.items():
            print(f"  {crit:<18} A={counts['A']} B={counts['B']} tie={counts['TIE']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
