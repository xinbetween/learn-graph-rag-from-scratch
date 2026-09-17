# Authoring guide: Graph RAG from Scratch

Visual design follows agentsecurity.xinbetween.com (Flexoki-derived tokens, system sans and mono fonts, no web fonts). Tokens live in `site/assets/css/site.css`; prefer `--bg`, `--fg`, `--accent`, `--boundary`, `--trust`, `--attack`, `--defense`, `--warn`, but legacy names (`--paper`, `--ink`, `--node`, `--edge`, `--comm`, `--c1`…`--c8`) still work as aliases.

Read this whole file before writing a chapter. Then read the exemplar chapter
`site/chapters/08-entity-relation-extraction.html` end to end. Every chapter must match its structure,
tone, markup conventions and depth.

## Files and structure

- Site root: `site/`. Chapters: `site/chapters/<slug>.html`. Slugs, titles, minutes, summaries and prerequisites are in
  `site/assets/js/curriculum.js`. Use the **exact** slug as filename and in `<body data-slug>`. The `<h1>` should match the
  curriculum title (tiny wording tweaks are OK, but then do not change curriculum.js; the orchestrator owns it).
- Running example: `docs/running-example.md` (the fictional Kestrel Labs corpus). Use its entities, relationships, dates and
  canonical questions for every example, diagram, exercise and project. Never contradict it.
- Reference code: `code/minigraphrag/` is a Python package being built in parallel. Before writing code snippets, list
  and read the actual files in `code/minigraphrag/` (and `code/README.md` if present). If a module/function exists, your
  snippets and exercises must match its real names and signatures. If it doesn't exist yet, use the planned names below.
  Check again before you finish. Snippets may be simplified teaching versions, but label the file with `data-file` and
  don't invent a different API for the same thing.

Planned `minigraphrag` modules: `llm.py` (LLM.complete(prompt, system=None, json=False), OpenAICompatibleLLM, AnthropicLLM,
MockLLM, CachedLLM), `tokens.py` (count_tokens), `chunking.py` (TextUnit, chunk_fixed, chunk_by_sentences,
chunk_documents), `embeddings.py` (HashingEmbedder, OpenAIEmbedder, SentenceTransformerEmbedder, cosine_top_k),
`vector_store.py` (VectorStore), `prompts.py`, `extraction.py` (Entity, Relationship, Claim, parse_extraction_output,
extract_from_unit, extract_claims), `resolution.py` (normalize_name, resolve_entities), `graph_build.py` (build_graph,
summarize_descriptions), `communities.py` (louvain_communities, modularity, hierarchical_communities, Community),
`reports.py` (build_community_context, generate_report, generate_all_reports, CommunityReport), `indexer.py`
(IndexConfig, build_index, load_index, Index), `search/basic.py` (basic_search), `search/local.py` (local_search,
build_local_context), `search/global_.py` (global_search, dynamic_community_selection), `search/lightrag.py`,
`search/ppr.py` (personalized_pagerank, hipporag_search), `search/paths.py` (find_relational_paths, paths_to_text),
`search/subgraph.py` (pcst_subgraph), `search/bm25.py`, `search/hybrid.py` (reciprocal_rank_fusion, hybrid_search),
`search/text2cypher.py` (validate_cypher, graph_to_cypher_statements), `temporal.py` (add_fact, as_of), `context.py`
(triples_to_text, to_markdown_tables, to_adjacency_text, to_json, fit_to_budget), `evaluation.py` (exact_match, token_f1,
context_recall, llm_judge_pairwise, run_eval), CLI `python -m minigraphrag index|query|eval`.

## Page skeleton (copy exactly; change only slug, title, description and the main content)

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TITLE | Graph RAG from Scratch</title>
<meta name="description" content="ONE SENTENCE">
<meta name="theme-color" content="#fbfaf8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#100f0d" media="(prefers-color-scheme: dark)">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="...copy from exemplar...">
<link rel="stylesheet" href="../assets/css/site.css">  <!-- tools/stamp_assets.py adds ?v=hash -->
<script>try{var t=localStorage.getItem("grfs-theme");if(t)document.documentElement.dataset.theme=t}catch(e){}</script>
</head>
<body data-slug="SLUG" data-root="..">
<main class="chapter" id="main">
  <header class="chapter-head">
    <h1>TITLE</h1>
    <p class="lede">...</p>
    <div class="objectives"><h2>You will be able to</h2><ul><li>...</li></ul></div>
  </header>
  ... sections ...
</main>
<script src="../assets/js/curriculum.js"></script>
<script src="../assets/js/site.js"></script>
<script src="../assets/js/viz.js"></script>
<!-- optional: <script> GRFSViz.register(...) custom visualizations </script> -->
</body>
</html>
```

`site.js` adds the top bar, sidebar, part/chapter kicker, reading time, prerequisites, on-this-page TOC, heading anchors,
quiz behavior, copy buttons, syntax highlighting (Prism, languages: python, bash, json, cypher, sql, yaml, typescript),
automatic completion tracking (a chapter is marked complete in localStorage when the reader scrolls to its pager) and the pager. Do not add any of these yourself.

## Required sections, in this order

1. **Header**: h1, lede (1–2 sentences on what you'll build/learn and why it matters), objectives (4–6 action verbs).
2. **Teaching sections** (4–7 `<h2>`s, with `<h3>` subsections): motivation → intuition → mechanism → code → trade-offs.
   Explain *why* before *how*. Go deep: real formulas where they exist (e.g. modularity, PPR, RRF, BM25), real prompts,
   real algorithm steps, real complexity/cost reasoning, concrete worked numbers on the Kestrel graph.
   - At least **one interactive visualization** (`.viz`) and usually two or three.
   - At least **one hand-drawn inline SVG diagram** in `<figure><div class="diagram"><svg>…</svg></div><figcaption>`.
   - Code in `<pre data-file="path"><code class="language-python">` (escape `<`, `>`, `&` as entities!).
   - Comparison tables where there are real trade-offs.
   - Callouts: `<div class="callout note|tip|warn|example|paper"><span class="callout-title">…</span><p>…</p></div>`.
     `paper` callouts automatically prefix "From the literature: " — the title should be "Authors, Short title (year)".
3. `<h2>Exercises</h2>`: **at least 4** `<section class="exercise" data-level="warmup|core|stretch">` with
   `<h4>Exercise N.M <span class="level">Warm-up|Core|Stretch</span></h4>`, the task, optional
   `<details class="hint"><summary>Hint</summary>…</details>`, and **always** a full worked
   `<details class="answer"><summary>Show answer</summary>…</details>`. Answers must be complete: code that works,
   numbers computed correctly, reasoning shown. Mix: hand-computation, coding, analysis/design. N = chapter number
   (capstones use C1.1 etc.).
4. `<h2>Check your understanding</h2>` + `<p class="quiz-score"></p>` + **at least 5** quizzes:
   `<div class="quiz"><p class="q">…</p><ol><li>…</li><li data-correct>…</li>…</ol><div class="explain">…</div></div>`.
   Exactly one `data-correct` per quiz; vary its position; distractors must be plausible.
5. `<h2>Questions learners often ask</h2>` with **at least 4** `<details class="qa"><summary>Q</summary><div><p>A</p></div></details>`.
6. `<section class="project"><h3>Project: …</h3>` with intro, `<ul class="checklist deliverables">` items
   `<li><input type="checkbox" aria-label="Done"> <span>…</span></li>`, and a "Done when" line.
7. `<div class="keypoints"><h2>Key takeaways</h2><ul>…</ul></div>`
8. `<h2>References</h2><ul class="refs"><li>Authors. <a href="…">Title</a>. <span class="venue">venue, year</span></li></ul>`

Capstones replace sections 2–6 with: overview and architecture diagram, requirements, milestones (each milestone with
steps, starter code, checkpoints and a worked reference solution in `details.answer`), evaluation rubric (table),
stretch goals, a short quiz (≥3) and Q&A (≥4). Glossary/library pages have their own structure (see their brief).

Length target: comparable to the exemplar (roughly 5,000–9,000 words of content including code). Depth over breadth.

## Visualizations (`site/assets/js/viz.js`)

Markup: `<div class="viz" data-viz="TYPE"><script type="application/json">{…valid JSON…}</script></div>`.
Valid JSON only: double quotes, no trailing commas, no comments. HTML inside `caption`/`detail` strings is allowed
(e.g. `<strong>`, `<span class=\"viz-chip node\">`). Common keys: `title`, `subtitle`, `height` (px of a 720-wide viewBox),
`interval` (ms between autoplay steps).

### graph-steps — the workhorse (BFS, neighborhood expansion, paths, seeds, scores, subgraphs)
```json
{ "title": "...", "height": 380, "directed": false, "dim": true, "scaleByScore": false, "scoreDigits": 2,
  "nodes": [{"id": "kestrel", "label": "Kestrel Labs", "group": 1, "x": 50, "y": 40}],
  "edges": [{"source": "kestrel", "target": "tern", "label": "runs"}],
  "legend": {"1": "Organization", "2": "Person"},
  "steps": [
    {"caption": "HTML caption", "active": ["kestrel"], "visited": ["tern"],
     "edges": ["kestrel>tern"], "visitedEdges": [], "scores": {"kestrel": 0.42}, "showAllLabels": false}
  ] }
```
- `x`,`y` are percentages (0–100); give them for **all** nodes for a clean deliberate layout (recommended), or omit for all
  to get a force layout. Keep labels short; ~6–16 nodes. Node ids: no `>` or `|` characters.
- Edge refs in steps: `"a>b"` (either direction matches). `group` 1–8 picks a palette color.
- With `dim: true` (default when a step has active/visited), everything else fades.

### flow — pipelines and loops
`{ "title": "...", "perRow": 3, "stages": [{"label": "Chunk", "detail": "HTML caption"}] }` (snake layout).

### chunker
`{ "title": "...", "text": "long passage", "size": 40, "overlap": 8, "note": "caption suffix" }` (units are words).

### embedding-space
`{ "title": "...", "points": [{"label": "chunk 3: Deepcast acquired", "x": 20, "y": 30, "group": 2}], "query": {"label": "Why Tern?", "x": 40, "y": 50}, "k": 3, "note": "..." }`

### pagerank (live power iteration; click nodes to toggle seeds; α slider; iteration slider)
`{ "title": "...", "nodes": [...as graph-steps...], "edges": [{"source": "a", "target": "b", "weight": 1}], "seeds": ["a"], "alpha": 0.85, "directed": false }`

### louvain (step-through of phase 1 local moves, live modularity)
`{ "title": "...", "nodes": [...], "edges": [...weights optional...], "seed": 3 }`

### text-to-graph (extraction)
`{ "title": "...", "text": "...", "height": 280, "entities": [{"name": "Deepcast", "type": "ORGANIZATION", "group": 2, "mentions": ["Deepcast"], "description": "...", "x": 45, "y": 25}], "relations": [{"source": "Marlow Dynamics", "target": "Deepcast", "label": "acquired", "description": "..."}] }`

### map-reduce (global search)
`{ "title": "...", "question": "...", "threshold": 20, "communities": [{"title": "Supply chain", "score": 85, "answer": "partial answer"}], "final": "final answer" }`

### rrf
`{ "title": "...", "lists": {"BM25": ["doc a", "doc b"], "Vector": [...], "Graph": [...]}, "k": 60 }`

### token-budget
`{ "title": "...", "total": 12000, "parts": [{"label": "Entities", "share": 0.2}], "note": "..." }`

### Custom visualizations
If a concept needs something else (e.g. a PCST prize/cost explorer, a bi-temporal timeline, a BM25 calculator, a
beam-search tree), register one inline after viz.js:
```html
<div class="viz" data-viz="ch19-pcst"><script type="application/json">{...}</script></div>
...
<script>
GRFSViz.register("ch19-pcst", function (el, cfg, api) {
  const { stage } = api.frame(el, cfg);               // header + stage
  const svg = api.svgEl("svg", { viewBox: "0 0 720 360" }, stage);
  const G = api.drawGraph(svg, cfg, 720, 360);         // nodes/edges with drag; G.nodes[i]._c circle, G.edges[i]._el line
  const cap = api.h("div", { class: "viz-caption", "aria-live": "polite" }, el);
  api.player(el, nSteps, (i) => { /* render step i */ cap.innerHTML = "..."; });
  // or api.controls(el) + api.button(bar, "Run") + sliders via api.h("input", {type:"range"})
});
</script>
```
Other helpers: `api.pagerank(nodes, edges, seedsSet, alpha, iters, directed)`, `api.groupColor(n)`, `api.legend(el, map)`,
`api.fmt(x, digits)`, `api.escapeHtml`. Prefix custom names with the chapter number. Use only CSS variables for colors
(`var(--node)`, `var(--edge)`, `var(--comm)`, `var(--ink)`, `var(--muted)`, `var(--rule)`, `var(--panel)`, `var(--c1)`…`var(--c8)`,
soft variants `--node-soft`, `--edge-soft`, `--comm-soft`, `--bad`, `--good`). No external libraries.

## Hand-drawn SVG diagrams

Use `viewBox` and classes only (never hard-coded colors), so both light and dark themes work:
`d-box` (+ `node|edge|comm|bad|good|ghost`), `d-node` (+ `hot|alt|warm`), `d-line` (+ `hot|dash|faint`), `d-text`
(+ `small|bold|mono|on-hot`), `d-area` (community hull), `d-fill-node|edge|comm|ink|muted`. Include `<title>` and
`role="img"`. Keep text ≥ 11px in viewBox units at ~680 wide. For arrowheads define a `<marker>` whose path uses
`class="d-fill-ink"`. Check that text does not overflow boxes (estimate ~7px per character at 13px).

## Writing style

- Audience: software engineers comfortable with Python, new to graphs and GraphRAG. Teach from first principles.
- Sentence case headings. Plain, direct, active voice. Short paragraphs. Define a term the first time you use it.
- Avoid: ALL CAPS labels, "WORD — fragment" labels, middle-dot meta strings, marketing adjectives, filler
  ("In this section we will…" once in the lede is enough), exclamation marks, emoji.
- Link other chapters by relative filename (`14-local-search.html`) where you build on or forward-reference them.
- Always tie back to the Kestrel Labs example and the canonical questions.

## Accuracy rules (important)

- Do not invent paper results, numbers, author names, venues, or arXiv IDs. If you state a specific number from a paper,
  you must be confident it is correct; otherwise describe the finding qualitatively.
- Cite only sources you are sure exist. You may use WebFetch/WebSearch to verify (arxiv.org/abs/ID pages). IDs below
  marked (verified) came from the course's source lists; others are believed correct but verify before citing.
- Tools/frameworks change: describe stable concepts; when mentioning CLI flags or config keys of third-party tools,
  keep to well-known ones or verify in their docs. Microsoft GraphRAG is in maintenance mode as of 2026.
- For "numbers you will observe" in exercises, prefer computing them in the answer (by hand for small graphs) over
  asserting what an LLM run would output.

### Source papers (arXiv IDs)
Verified from course source lists: From Local to Global (GraphRAG) 2404.16130; Graph RAG survey 2408.08921;
RAG with Graphs survey 2501.00309; Survey of GraphRAG for customized LLMs 2501.13958; RAPTOR 2401.18059; KAG 2409.13731;
GRAG 2405.16506; OG-RAG 2412.15235; LinearRAG 2510.10114; AutoGraph-R1 2510.15339; AGRAG 2511.05549;
Medical Graph RAG 2408.04187; GFM-RAG 2502.01113; StructRAG 2410.08815; Think-on-Graph 2307.07697; Think-on-Graph 2.0
2407.10805; HybGRAG 2412.16311; KG-Guided RAG 2502.06864; G-Retriever 2402.07630; GraphCoder 2406.07003; adaptive
reasoning structures 2508.06105; LightRAG 2410.05779; citation graph RAG 2501.15067; GNN-enhanced retrieval 2406.06572;
Graph Chain-of-Thought 2404.07103; Graph of Records 2410.11001; Graph-constrained Reasoning 2410.13080;
Chain-of-Knowledge 2306.06427; MuseGraph 2403.04780; Plan-on-Graph 2410.23875; GraphRAG-Bench 2506.05690; DIGIMON
2503.04338; PolyG 2504.02112; MultiHop-RAG 2401.15391; CRUD-RAG 2401.17043; HyperTree Planning 2505.02322; Knowledge
Graph of Thoughts 2504.02670; HiRAG (hierarchical knowledge) 2503.10150; PathRAG 2502.14902; Agentic Deep Graph Reasoning
2502.13025; A-MEM 2502.12110; KARMA 2502.06472; Agentic Reasoning 2502.04644; Zep 2501.13956; SimGRAG 2412.15272;
SynthCypher 2412.12612; Decoding on Graphs 2410.18415; Graphusion 2410.17600; AGENTiGraph 2410.11531; HybridRAG
2408.04948; Path-based algebraic foundations of graph query languages 2407.04823; GraphReader 2406.14550; Docs2KG
2406.02962; Don't Forget to Connect (graph reranking) 2405.18414; HippoRAG 2405.14831; Ontologies to the Rescue 2405.11706;
KG RAG for customer service 2404.17723; GraphER 2404.12491; Topologies of Reasoning 2401.14295; KG benchmark on enterprise
SQL 2311.07509; MemGPT 2310.08560; Talk like a Graph 2310.04560; Unifying LLMs and KGs roadmap 2306.08302; KAPING
2306.04136; FactKG 2305.06590; AutoKG 2008.08995; G-Designer 2410.11782; KG-LLM interface optimization 2505.24478;
workflow graphs for conversational agents 2505.23006; DRAG distillation 2506.01954; BYOKG-RAG 2507.04127; Youtu-GraphRAG
2508.19855; RepoGraph 2410.14684; CodexGraph 2408.03910; CodeGRAG 2405.02355; GraphSearch (agentic deep searching)
2509.22009. Recent (2026): MOSAIC 2609.11065; LiteRAG 2609.10239; NS-ST-GraphRAG 2609.05139; Beyond Vector Search hybrid
GraphRAG comparison 2608.28766; multi-agent governed KG construction 2608.28642; post-graph-rag bi-temporal Postgres
2608.24921; Evidence-admissible GraphRAG 2608.22062; The Commercial Tax (GraphRAG cost) 2608.16096; LineageRAG 2608.16004;
Noesis 2608.15919; CTI with GraphRAG 2608.13050; HC-RAG financial filings 2608.12335; VDGR-RAG 2608.07994; DocNavRAG
2608.01565; HVM-GraphRAG 2607.24861; HyCE-RAG hypergraph chain-of-evidence 2607.22597; schema-constrained causal graphs
HCG-RAG 2607.22592; hypergraph RAG fact extraction 2607.20506; PAGE-RAG 2607.19301; ColGraphRAG 2607.16208; EvoGraph-R1
2607.12764; RAGU 2607.11683; NGM-RAG 2607.11159; multi-granularity multimodal KG RAG 2608.25986.
Believed correct (verify): Reasoning on Graphs (RoG) 2310.01061; GNN-RAG 2405.20139; HippoRAG 2 2502.14802; GraphGPT
2310.13023; LLaGA 2402.08170; HyperGraphRAG 2503.21322; Graph-R1 2507.21892; Chain-of-Knowledge (ICLR 2024) is on
OpenReview cPgh4gWZlz; Think-on-Graph ICLR 2024 OpenReview nnVO1PvbTv.

Other sources: microsoft/graphrag (GitHub; docs at microsoft.github.io/graphrag), Microsoft Research blog posts on
GraphRAG, LazyGraphRAG and DRIFT search; gusye1234/nano-graphrag; HKUDS/LightRAG; circlemind-ai/fast-graphrag;
getzep/graphiti; neo4j/neo4j-graphrag-python; LlamaIndex PropertyGraphIndex; LangChain graph transformers; topoteretes/cognee;
apecloud/ApeRAG; JayLZhou/GraphRAG (DIGIMON); pyg-team/pytorch_geometric; graspologic; graphrag.com (GraphRAG pattern
catalog); curated lists DEEP-PolyU/Awesome-GraphRAG, graphrag/awesome-graphrag, H-Freax/Awesome-Graph-RAG, the
Hugging Face "graphrag/graphrag-papers" collection; Thinking Loop, "7 Graph RAG Designs That Outperform Keyword Search"
(Medium, Oct 2025): neighborhood expansion, metapaths, subgraph assembly, temporal windows, hybrid rerankers, panels,
provenance.

## Before you finish, verify

1. Every `<script type="application/json">` parses (e.g. extract and run through `python3 -c 'import json,sys;json.load(sys.stdin)'`).
2. Escape `<`, `>` and `&` inside `<code>`/`<pre>` as `&lt;` `&gt;` `&amp;`.
3. Render check: a static server runs at `http://localhost:8765/` serving `site/` (if not, start
   `python3 -m http.server 8765` from `site/` in the background). Use Python Playwright (installed) to load your page,
   collect console errors and page errors (must be zero), click through a few "Next" buttons on each viz, and screenshot
   each `.viz` and `figure .diagram` element to a temp folder in your scratchpad; look at the screenshots and fix layout
   problems (overlapping labels, clipped text, unreadable diagrams) in both light and dark color schemes.
4. Counts: ≥1 viz, ≥1 SVG diagram, ≥4 exercises each with answer, ≥5 quizzes each with exactly one data-correct,
   ≥4 Q&A, a project, key takeaways, references.
5. Do not edit shared files (`site.css`, `site.js`, `viz.js`, `curriculum.js`, `index.html`) or other agents' chapters.
   If you believe a shared component has a bug, describe it in your final reply instead.
