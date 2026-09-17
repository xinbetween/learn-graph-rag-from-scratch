<div align="center">

# Build Graph RAG From Scratch

**Thirty-four chapters and four capstones. A pile of documents that becomes a knowledge graph you can search.**

Read the diagram → step through the figure → run the code → take the quiz.

[![CI](https://github.com/xinbetween/learn-graph-rag-from-scratch/actions/workflows/ci.yml/badge.svg)](https://github.com/xinbetween/learn-graph-rag-from-scratch/actions/workflows/ci.yml)
[![Deploy](https://github.com/xinbetween/learn-graph-rag-from-scratch/actions/workflows/deploy.yml/badge.svg)](https://github.com/xinbetween/learn-graph-rag-from-scratch/actions/workflows/deploy.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776ab.svg?style=flat-square)](https://www.python.org/)
[![Dependencies: networkx, numpy](https://img.shields.io/badge/dependencies-networkx%20·%20numpy-16a34a.svg?style=flat-square)](code/)
[![API key required: none](https://img.shields.io/badge/API_key_required-none-16a34a.svg?style=flat-square)](code/)
[![Site build: none](https://img.shields.io/badge/site_build_step-none-16a34a.svg?style=flat-square)](site/)
[![Languages: EN · 中文](https://img.shields.io/badge/languages-EN%20·%20中文-f59e0b.svg?style=flat-square)](#-translating)

[**Read it →**](https://graphrag.xinbetween.com/) &nbsp;·&nbsp;
[**Star on GitHub**](https://github.com/xinbetween/learn-graph-rag-from-scratch) &nbsp;·&nbsp;
[**Follow on X**](https://x.com/xinbetween)

</div>

---

Vector search finds passages that look like the question. It loses the thread when
the answer is spread across three documents, when the question is about the whole
corpus, or when a fact changed last March. Most teams discover this after launch,
then reach for a GraphRAG framework without being able to say why it should work
or where it will fail. This course closes that gap.

It starts with a hundred-line vector RAG and the questions it cannot answer. It ends
with an extractor, entity resolution, community detection, community reports, eight
retrieval methods, a bi-temporal graph, an evaluation harness and four complete
systems. Each technique arrives **as the repair for a failure you have already seen.**

```python
# Chapter 17. Personalized PageRank: spread probability from the question's
# entities across the graph, restarting at the seeds with probability 1 - alpha.
p = s.copy()
for _ in range(iters):
    new = (1 - alpha) * s + alpha * (M @ p + p[dangling].sum() * s)
    if np.abs(new - p).sum() < tol:
        p = new
        break
    p = new
```

Chapter 17 builds HippoRAG-style retrieval on those lines: seed the question's
entities, let probability flow along relationships, and rank passages by where it
settles. It also shows where one step of spreading activation still misses evidence.
By the end you will be able to open Microsoft GraphRAG, LightRAG, HippoRAG or Graphiti
and say what each part is for.

**No framework. No API key. No graph database required.** 3,462 lines of Python
with two dependencies, runnable offline on a laptop against a deterministic mock model.

---

## Who this is for

| | |
| --- | --- |
| **Your RAG system misses multi-hop questions.** | Chapter 03 shows exactly which document top-k retrieval drops. Chapters 17–18 fix it with Personalized PageRank and path retrieval. |
| **You are choosing a GraphRAG framework.** | Chapters 26 and 28 compare Microsoft GraphRAG, LightRAG, neo4j-graphrag, LlamaIndex and Graphiti by what they extract, how they search and what indexing costs. |
| **You read the GraphRAG paper and want the details.** | Chapters 12, 14 and 15 implement community reports, local search budgets, map-reduce global search and DRIFT, and measure each on one corpus. |
| **You learn by experimenting.** | Ninety interactive figures. Step through Louvain one move at a time, toggle PageRank seeds, and watch global search discard low-scoring reports. |

Prerequisites: Python, and having called an LLM API once. No graph theory or machine
learning background: Chapter 04 teaches the graph algorithms the course uses.

---

## What makes it different

|  | |
| --- | --- |
| 📊 **Diagrams of the mechanism** | Where a fact enters the graph, which edge a query follows, and what reaches the model's context window. |
| 🎛 **Figures you can step through** | 90 interactive figures running in the page: extraction, BFS, Louvain, Personalized PageRank, map-reduce search, rank fusion, token budgets. |
| ✅ **220 graded questions** | In every chapter and capstone, each with an explanation, plus 190 answers to questions learners actually ask. |
| 🧪 **168 exercises with worked answers** | Warm-up, core and stretch. Answers with code run against the reference implementation. |
| 🟦 **Code that runs** | `minigraphrag` implements every stage the chapters teach. Its test suite runs in CI on every push, offline. |
| 🔎 **Claims checked against sources** | Numbers attributed to papers were checked against their arXiv abstracts or project docs; numbers attributed to the code were reproduced by running it. |
| 🌏 **English and 中文** | Navigation, search, quizzes, figure controls, the home page and glossary in Chinese, with chapters translated progressively; untranslated chapters fall back to English with an honest banner. |
| 🗺 **One running example** | Every chapter uses the same fictional corpus about Kestrel Labs, so you watch one graph grow from raw text to answers. |

---

## The curriculum

<table>
<tr><th align="left">Part</th><th align="left">Chapters</th><th align="left">You learn</th></tr>
<tr>
<td><b>Start here</b></td>
<td>00</td>
<td>What GraphRAG is · the Kestrel Labs corpus · setting up <code>minigraphrag</code></td>
</tr>
<tr>
<td><b>Foundations</b></td>
<td>01–05</td>
<td>Why LLMs need retrieval · <b>vector RAG from scratch</b> · where it breaks · graph algorithms · knowledge graphs, Cypher and SPARQL</td>
</tr>
<tr>
<td><b>Building the graph</b></td>
<td>06–13</td>
<td>Graph shapes · text units · LLM extraction and gleaning · entity resolution · claims and time · Louvain and Leiden · community reports · storage</td>
</tr>
<tr>
<td><b>Retrieval</b></td>
<td>14–21</td>
<td>Local search · global search and DRIFT · LightRAG · <b>Personalized PageRank (HippoRAG)</b> · PathRAG and Think-on-Graph · G-Retriever and GNNs · Text2Cypher · hybrid retrieval and seven Graph RAG designs</td>
</tr>
<tr>
<td><b>Generation</b></td>
<td>22–24</td>
<td>Turning graphs into prompts · graph-guided reasoning · training models with graphs</td>
</tr>
<tr>
<td><b>Evaluation and production</b></td>
<td>25–29</td>
<td>Evaluation and LLM judges · cost and scale · incremental and bi-temporal graphs · frameworks in practice · access control, prompt injection and observability</td>
</tr>
<tr>
<td><b>Frontiers</b></td>
<td>30–33</td>
<td>Agentic GraphRAG and graph memory · multimodal and hypergraph RAG · code, medicine, finance and law · the research map to 2026</td>
</tr>
<tr>
<td><b>Capstones</b></td>
<td>C1–C4</td>
<td>MiniGraphRAG end to end · a codebase assistant on a code graph · temporal memory for an agent · enterprise knowledge graph QA</td>
</tr>
</table>

Each part answers a question the previous one created:

0. Start here. **…which gives you a corpus, a codebase and a map. Now see why plain retrieval is not enough. So:**
1. Foundations. **…which shows exactly where vector search loses the thread. Build the structure it is missing. So:**
2. Building the graph. **…which leaves you with a graph, its communities and their summaries. Now search them. So:**
3. Retrieval. **…which finds the right evidence. Getting it into the model's reasoning is a separate problem. So:**
4. Generation. **…which produces grounded answers. Prove they are better, and make them affordable. So:**
5. Evaluation and production. **…which is a system you can run. The field keeps moving past it. So:**
6. Frontiers. **…which is everything. Put it together.**

Read them in order the first time. After that, go straight to the retrieval method you need.

---

## Quickstart

```bash
git clone https://github.com/xinbetween/learn-graph-rag-from-scratch
cd learn-graph-rag-from-scratch

# --- the code (mock LLM, no key, no network) ---
cd code
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                                    # 65 tests, under a second

python -m minigraphrag index --input data/corpus --output .index
python -m minigraphrag query --method local  "Why did Kestrel Labs start Project Tern?"
python -m minigraphrag query --method global "What are the main themes in this corpus?"
python -m minigraphrag query --method ppr    "What connects Priya Nair to Deepcast?"
python -m minigraphrag eval  --methods basic,local,global,ppr,hybrid

# --- the site (no build step) ---
cd ..
python3 tools/serve.py        # http://localhost:8765
```

Query methods: `local`, `global` (with `--level N` or `--dynamic`), `drift`, `basic`,
`lightrag`, `ppr`, `hybrid`, `subgraph`.

`MockLLM` recognizes each prompt and answers with deterministic heuristics, and
`HashingEmbedder` embeds text without downloading a model, so the whole pipeline runs
offline with no spend. Its answers stitch together retrieved sentences: they show what
each method retrieved, not how well a real model reasons. To use one, pass
`--llm openai`, `--llm anthropic` or `--llm ollama` and set the matching environment
variables; see [`code/README.md`](code/README.md).

---

## The numbers on the site are real

When a chapter says the offline index has 17 entities, 54 relationships and 4
communities, that building it takes 122 LLM calls, or that retrieval ranks a document
21st of 24, those numbers came from running `minigraphrag` on the Kestrel corpus with
the mock model. Worked examples (modularity, PageRank iterations, BM25, rank fusion, token
budgets) were recomputed by hand and in code.

Numbers attributed to papers or products were checked against the arXiv abstract, the
paper body, the project README or its source. Where a claim could not be confirmed, the
chapter says so or states it qualitatively.

Two bugs in the reference code are deliberate: the ordering assumption in
`temporal.add_fact` and the path-scoring shortcut in `find_relational_paths`. Chapters
10, 18 and 27 teach them as exercises.

CI enforces the parts a machine can check: the test suite passes, every chapter has its
required components with valid figure configs and exactly one correct answer per quiz,
internal links resolve, asset version stamps are current, and every page renders in
Chromium at desktop and phone width, light and dark, with no errors. Changing the
corpus or the package can still make a quoted number stale, so rerun the relevant
chapter's code after changes there.

---

## Repo layout

```
site/                        the published website; no build step
  index.html                 the home page
  chapters/00..33-*.html     chapters: prose, figures, exercises, quizzes, Q&A, project
  chapters/c1..c4-*.html     capstones
  chapters/glossary.html     167 terms
  chapters/library.html      every paper, repository and article cited
  assets/js/curriculum.js    parts, chapters, prerequisites: the single source of structure
  assets/js/site.js          top bar, search, chapter rail, quizzes, progress, code blocks
  assets/js/viz.js           the interactive figure library
  assets/css/site.css        design tokens and components
  assets/js/curriculum.zh.js Chinese part and chapter text
  zh/index.html              the home page in Chinese
  zh/chapters/*.html         Chinese chapters: translated, or generated English fallbacks
  CNAME                      graphrag.xinbetween.com
code/                        minigraphrag, the reference implementation
  minigraphrag/              chunking, extraction, resolution, communities, reports, indexer
  minigraphrag/search/       basic, local, global/DRIFT, LightRAG, PPR, paths, subgraph, BM25, hybrid, Text2Cypher
  data/corpus/               the 12 Kestrel Labs documents
  data/questions.jsonl       23 evaluation questions with answers and supporting documents
  tests/                     pytest suite
docs/
  running-example.md         the Kestrel Labs world: entities, relationships, canonical questions
  AUTHORING.md               chapter markup, figure configs, style and accuracy rules
  REVIEW.md                  the editorial and technical review brief
  TRANSLATING.md             Chinese translation workflow, terminology and style
tools/
  serve.py                   no-cache local preview server
  check_site.py              structure, figure JSON, quiz and link checks
  build_zh.py                regenerates the Chinese mirror and hreflang alternates
  stamp_assets.py            adds ?v=<content hash> to CSS/JS links
  render_check.py            renders every page in Chromium and clicks through every figure
```

The site is plain HTML with two shared scripts and one stylesheet. Chapter pages author
only their `<main>` content; `site.js` adds navigation, search, the contents rail,
quiz behaviour and progress tracking in `localStorage`.

Every push to `main` publishes `site/` to GitHub Pages through
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml), after the site check
passes; no build output is committed. Every internal link is relative, so there is no
base path or site URL to configure. The domain lives in `site/CNAME` so it survives
every deploy. [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs the tests,
site checks, stamp check and render check on pushes and pull requests.

After editing an English chapter or anything in `site/assets/`, run `python3 tools/build_zh.py` and
`python3 tools/stamp_assets.py`, or CI will fail on a stale Chinese mirror or stale version stamps.

---

## 🌏 Translating

Translation is **partial by design**. Every English page has a Chinese counterpart under
[`/zh/`](https://graphrag.xinbetween.com/zh/). A chapter that has not been translated shows its English
body with a banner saying so, while the navigation, search, quizzes and figure controls around it are
already Chinese. `/zh/` stays complete and navigable at every point instead of shipping a half-built second
site.

| Where | What it holds |
| --- | --- |
| `site/assets/js/site.js` → `STRINGS` | Top bar, search, chapter rail, pager, quiz UI, footer, the fallback banner |
| `site/assets/js/viz.js` → `L` | Figure controls and the built-in captions of every figure type |
| `site/assets/js/curriculum.zh.js` | Part titles, blurbs and bridges; chapter titles and summaries |
| `site/zh/index.html` | The home page, written by hand |
| `site/zh/chapters/<slug>.html` | Chapters: generated English fallbacks until translated |

**To translate a chapter:** open its generated page under `site/zh/chapters/`, change `data-fallback="en"`
to `data-translated="true"` on `<body>`, and translate everything inside `<main>`, including figure captions
and diagram text. Then run:

```bash
python3 tools/build_zh.py && python3 tools/stamp_assets.py && python3 tools/check_site.py
```

`build_zh.py` regenerates every untranslated page from its English source and leaves translated pages alone.
`check_site.py` compares each translated page with the chapter it mirrors: the same figures in the same
order, the same number of diagrams, exercises, answers, Q&A items and references, and the same correct
option in every quiz, so a translation cannot silently drift. CI runs both and fails on any difference.

**Conventions.** Code, identifiers, model and framework names, paper titles and the Kestrel Labs names stay
in English; everything else is translated. The terminology table and style rules are in
[`docs/TRANSLATING.md`](docs/TRANSLATING.md).

---

## Contributing

Issues and PRs welcome. Particularly useful:

- **Corrections.** If a claim is wrong, open an issue with the evidence. This is the
  most valuable contribution there is.
- **Stale numbers.** If a chapter's quoted output no longer matches what `minigraphrag`
  prints, report the chapter and the command.
- **Translations.** See above: the build tells you exactly what is missing.
- **Quiz questions and exercises.** More good ones are always welcome.
- **A chapter this course is missing.** GraphRAG over streaming data, cross-lingual
  entity resolution, and graph retrieval evaluated with real users are all absent
  and all interesting.

Chapter conventions are in [`docs/AUTHORING.md`](docs/AUTHORING.md). Before opening a
PR, run `python3 tools/check_site.py`, the test suite, and with the preview server
running, `python3 tools/render_check.py`.

---

## Credits

Built on the work of the people who actually solved these problems. Particular debts
to Microsoft Research's GraphRAG and its *From Local to Global* paper, LightRAG,
HippoRAG, RAPTOR, Think-on-Graph, G-Retriever, Zep and Graphiti, and the curated
lists at [DEEP-PolyU/Awesome-GraphRAG](https://github.com/DEEP-PolyU/Awesome-GraphRAG),
[graphrag/awesome-graphrag](https://github.com/graphrag/awesome-graphrag) and the
Hugging Face [GraphRAG papers collection](https://huggingface.co/collections/graphrag/graphrag-papers).
Every source is listed in the [paper and tool library](https://graphrag.xinbetween.com/chapters/library.html).

This is an educational reimplementation and is not affiliated with any of them.
Production frameworks are the real thing; this teaches you how to read them. The
Kestrel Labs corpus is fictional.

---

<div align="center">

**[Start with Chapter 00 →](https://graphrag.xinbetween.com/chapters/00-welcome.html)**

If this helped, a ⭐ makes it findable for the next person.

[GitHub](https://github.com/xinbetween/learn-graph-rag-from-scratch) · [X](https://x.com/xinbetween)

</div>
