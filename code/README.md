# minigraphrag

The reference implementation for the *Graph RAG from Scratch* course. It is a small, readable GraphRAG: chunking, LLM extraction with gleaning, entity resolution, graph building, Louvain/Leiden communities, community reports, and eight retrieval methods (local, global, DRIFT, LightRAG, HippoRAG PPR, PathRAG paths, G-Retriever-style subgraphs, hybrid RRF), plus Text2Cypher, a bi-temporal graph and evaluation.

Everything runs **fully offline** by default. `MockLLM` recognises each prompt by a marker phrase and answers with deterministic heuristics, and `HashingEmbedder` embeds text without downloading a model. When you want real answers, swap in a real LLM with one flag.

The data in `data/` is the fictional Kestrel Labs world used in every chapter (see `docs/running-example.md`).

## Quickstart

```bash
cd code
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q

# build the index (mock LLM, hashing embedder: no network, about a second)
python -m minigraphrag index --input data/corpus --output .index

# ask questions
python -m minigraphrag query --method local  "Why did Kestrel Labs start Project Tern?"
python -m minigraphrag query --method global "What are the main themes in this corpus?"
python -m minigraphrag query --method ppr    "What connects Priya Nair to Deepcast?"
python -m minigraphrag query --method hybrid --show-context "Who supplied Kestrel's sonar in 2024?"

# compare methods on data/questions.jsonl
python -m minigraphrag eval --methods basic,local,global,ppr,hybrid --judge
```

Query methods: `local`, `global` (add `--level N` or `--dynamic`), `drift`, `basic`, `lightrag`, `ppr`, `hybrid`, `subgraph`.

The index folder has plain artifacts you can open: `text_units.json`, `entities.json`, `relationships.json`, `graph.graphml` (opens in Gephi or yEd), `communities.json`, `community_reports.json`, `claims.json`, `*_embeddings.npz/.json` and `config.json`.

## Using a real LLM

| `--llm` | Environment variables | Default model |
|---|---|---|
| `mock` | none | none |
| `openai` | `OPENAI_API_KEY`, optional `OPENAI_MODEL`, `OPENAI_BASE_URL` | `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY`, optional `ANTHROPIC_MODEL` | `claude-sonnet-5` |
| `ollama` | optional `OLLAMA_BASE_URL` (default `http://localhost:11434/v1`), `OLLAMA_MODEL` | `llama3.1` |

```bash
pip install -e ".[anthropic]"
export ANTHROPIC_API_KEY=...
python -m minigraphrag index --llm anthropic --cache-dir .cache/llm --output .index-claude
python -m minigraphrag query --llm anthropic --index .index-claude --method local "Who is the CTO of Kestrel Labs?"
```

`--cache-dir` wraps the LLM in `CachedLLM`, so re-running indexing after a code change doesn't pay for the same calls twice. vLLM, LM Studio and other OpenAI-compatible servers work through `OPENAI_BASE_URL`. For neural embeddings, pass `--embedder openai` or `--embedder st:all-MiniLM-L6-v2` (install the `st` extra). The embedder name is saved in `config.json` and reused at query time.

In Python:

```python
from minigraphrag import AnthropicLLM, HashingEmbedder, IndexConfig, build_index, load_index
from minigraphrag.search.local import local_search

llm = AnthropicLLM()                       # or OpenAICompatibleLLM(...), MockLLM()
build_index("data/corpus", ".index", llm, HashingEmbedder(), IndexConfig(max_gleanings=1))
index = load_index(".index")
print(local_search(index, "Why did Kestrel Labs start Project Tern?", llm).answer)
```

## Extras

`pip install -e ".[openai]"`, `".[anthropic]"`, `".[leiden]"` (graspologic hierarchical Leiden, used automatically when installed), `".[st]"` (sentence-transformers), `".[neo4j]"`, `".[tokens]"` (tiktoken; if its encoding files can't be loaded offline, a word-count estimate is used) and `".[dev]"` (pytest).

## Module map

| Module | What it teaches | Chapter |
|---|---|---|
| `llm.py` | One `complete()` interface; OpenAI-compatible, Anthropic, Mock, disk cache | 01, 26 |
| `tokens.py` | Token counting and budgets | 01, 07 |
| `embeddings.py`, `vector_store.py`, `search/basic.py` | Vector RAG baseline | 02, 03 |
| `context.py` | Graph linearization (triples, tables, adjacency, JSON), budgets | 06, 22 |
| `chunking.py` | Text units: fixed windows with overlap, sentence packing | 07 |
| `prompts.py`, `extraction.py` | Tuple-format extraction, robust parsing, gleaning, claims | 08, 10 |
| `resolution.py`, `graph_build.py` | Alias resolution, merging, description summarization, ranks | 09 |
| `temporal.py` | Bi-temporal edges, invalidation, as-of snapshots | 10, 27, C3 |
| `communities.py` | Modularity, Louvain from scratch, hierarchical Leiden/Louvain | 04, 11 |
| `reports.py` | Community context tables, JSON reports, sub-community substitution | 12 |
| `indexer.py` | Whole pipeline, artifacts, `load_index` | 13, C1 |
| `search/local.py` | Entity-anchored retrieval, proportional budgets, citations | 14 |
| `search/global_.py` | Map-reduce, helpfulness filtering, dynamic selection, DRIFT | 15 |
| `search/lightrag.py` | Low- and high-level keywords, dual-level matching | 16 |
| `search/ppr.py` | Personalized PageRank from scratch, HippoRAG passage ranking | 17 |
| `search/paths.py` | k-shortest paths, PathRAG flow pruning, path narration | 18 |
| `search/subgraph.py` | Greedy prize-collecting Steiner tree (G-Retriever approximation) | 19 |
| `search/text2cypher.py` | Schema prompt, Cypher validation, Neo4j export and execution | 05, 20 |
| `search/bm25.py`, `search/hybrid.py` | BM25 from scratch, reciprocal rank fusion | 21 |
| `evaluation.py` | EM, token F1, context recall, pairwise LLM judge | 25 |
| `cli.py` | `index`, `query`, `eval` | C1 |

## About the mock

`MockLLM` is a teaching device, not a model. For extraction it finds entity mentions with a small gazetteer of Kestrel surface forms (including aliases like "Okafor" and "TWI", so resolution still has work to do), plus a capitalised-phrase heuristic typed by suffixes ("... Institute", "... Act"). It links entities that co-occur in a sentence, and relation cue words ("acquired", "supplied", "led") mark a link as strong. On the first pass it skips weak co-occurrences and adds them only when gleaning, so gleaning has a visible effect. Its answers are extractive: it returns the context sentences that share the rarest words with the question, with `[Data: ...]` citations. Because of that, the mock shows *what each retriever put into the context*. To see how well a method actually answers, use a real LLM.
