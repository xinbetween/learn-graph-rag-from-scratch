# Editorial and technical review brief

You are reviewing chapters of "Graph RAG from Scratch" as two people at once: a GraphRAG researcher checking
every claim, and a technical book editor rewriting prose so it reads as a careful human author wrote it.
Work in place on the assigned files under `site/chapters/`. Keep the page structure, markup and component
counts intact (see "What not to change").

Read first: `docs/running-example.md`, `docs/AUTHORING.md` (markup reference), and the real code under
`code/minigraphrag/` for anything a chapter quotes. Use `code/.venv/bin/python` to run code.

## Part 1: technical accuracy

Every factual statement must be true, or be removed or reworded as an uncertainty. Check, in order of risk:

1. **Numbers attributed to papers or products.** Percentages, win rates, dataset sizes, parameter defaults,
   token counts, years, venues, author names. Fetch `https://arxiv.org/abs/<id>` (WebFetch) and confirm the
   number appears in the abstract or is otherwise something you are certain of. If not confirmable, restate
   qualitatively ("substantially fewer LLM calls") or delete. Do not invent a replacement number.
2. **Descriptions of methods.** What GraphRAG local search does with its token budget; how Leiden differs
   from Louvain; the PPR equation and which symbol is the restart probability; HippoRAG's node specificity;
   PathRAG's flow pruning; G-Retriever's PCST objective; RRF formula; BM25 formula; DRIFT's stages; LightRAG's
   modes; Graphiti's bi-temporal fields. Compare against the paper abstract, the project README, or the
   course's own `minigraphrag` implementation. Fix anything that misdescribes the mechanism.
3. **Code and numbers computed from code.** Any snippet labelled with a `minigraphrag/...` `data-file` must
   match the real module's names, signatures and behaviour. Any number the text says "you will see" or "the
   run prints" should be reproduced by running the code (mock LLM, `code/data/corpus`). If a number is
   stale, update it; if it is not reproducible, say so or remove it. Exercise answers with code must run.
4. **Math.** Recompute every worked example by hand or with Python (modularity, ΔQ, PPR iterations, cosine,
   BM25, RRF, token budgets). Fix wrong arithmetic in text, tables, and viz captions.
5. **Cross-references.** "Chapter N" mentions and links must point to the chapter that actually covers the
   topic (see `site/assets/js/curriculum.js`). Field names must match the code (`source_id` not
   `source_ids`; `strength` not `weight` on `Relationship`; `alpha` is the follow-an-edge probability in
   `personalized_pagerank`).
6. **Framework specifics** (Microsoft GraphRAG CLI and settings keys, LightRAG API, neo4j-graphrag classes,
   LlamaIndex classes, Graphiti). Verify against the current docs/README via WebFetch where possible. Where
   you cannot verify, keep the statement hedged and generic rather than precise and possibly wrong.
7. **Quiz correctness.** The `data-correct` option must be unambiguously the only right answer; the
   explanation must be accurate. Fix or rewrite bad questions.

Known issues surfaced earlier (verify and fix where present): the GraphRAG paper's chunk-size finding is
on HotPotQA (600-token chunks yielded almost twice the entity references of 2400-token chunks); HippoRAG's
paper uses damping 0.5; Microsoft GraphRAG is in maintenance mode; arXiv 2412.12612 is now titled
"Auto-Cypher" (was SynthCypher); 2306.06427 is Wang et al.'s Chain-of-Knowledge *prompting* paper, the
ICLR 2024 Chain-of-Knowledge is Li et al. 2305.13269; 2506.05690 is "When to use Graphs in RAG"
(GraphRAG-Bench); 2503.04338 is the DIGIMON unified-framework analysis.

## Part 2: prose quality

Target register: a good technical book (think of the best O'Reilly or MIT Press titles), written by one
author with a point of view. Plain, direct, specific. The reader is a working engineer.

Remove these tells wherever they occur. Rewrite the sentence, do not just delete the phrase:

- Announcements and throat-clearing: "In this section we will", "Let's dive in", "Now that we have",
  "It's worth noting that", "Importantly,", "Note that" at sentence start, "As we saw earlier".
- Hollow intensifiers and praise words: crucial, critical, key, essential, robust, powerful, seamless,
  elegant, rich, comprehensive, leverage, harness, unlock, delve, landscape, journey, realm, tapestry,
  game-changer, paradigm shift, "a testament to". Replace with the specific thing meant, or cut.
- Reflexive triads ("fast, cheap and reliable") when two items or one would do; sentences that end with a
  moral or a restatement of the previous sentence; paragraphs that open by restating the heading.
- "Not X, but Y" and "It's not just X; it's Y" constructions. Say Y.
- Rhetorical questions used as transitions. Cut or answer them directly.
- Hedging stacks ("can potentially help to improve"). Commit: "improves" or "sometimes improves, see §".
- Excessive bold on phrases mid-sentence; colons introducing single clauses; em dashes used more than
  about once per paragraph; "e.g."/"i.e." in running prose (write "for example", "that is").
- Generic openers ("In the world of", "In today's", "When it comes to") and generic closers
  ("This is a powerful technique that…", "By understanding X, you can…").
- Summaries inside the body that repeat the Key takeaways; Key takeaways that repeat the objectives.
- Contractions are fine. Second person is fine. Sentence case headings.

Add what human authors add: a concrete example where a claim is abstract; a specific number where the text
says "many"; a short aside where a reader will wonder "but what about…"; an admission where the field
does not know. Vary sentence length. Prefer verbs to nominalizations ("we merge" not "the merging of").

Keep terminology consistent within and across chapters: "text unit" (not chunk, except when discussing
chunking generally), "entity resolution", "community report", "local search", "global search",
"Personalized PageRank", "restart probability", "Kestrel Labs", "Project Tern", "Deepcast".

Captions, quiz explanations, exercise answers, callouts and viz captions (the `caption`/`detail` strings in
viz JSON) are prose too; edit them with the same care. Keep JSON valid.

## What not to change

- The file's `<head>`, `data-slug`, the three `<script src>` tags, and any `GRFSViz.register` code
  (you may edit strings inside it).
- Section order and the required components: keep at least the existing number of `.viz`,
  `figure .diagram`, `.exercise` (each with `details.answer`), `.quiz` (exactly one `data-correct`),
  `details.qa`, `.project`, `.keypoints`, `.refs`. You may improve or replace items, not drop them.
- Node ids and edge references inside viz JSON (labels and captions may change).
- Shared files under `site/assets/`, `site/index.html`, `docs/`, `code/`. If you find a bug in
  `minigraphrag`, describe it in your report; if a chapter already teaches the bug as an exercise, leave it.
- Do not shorten chapters materially; tightening is good, cutting substance is not.

## Verify before you finish

1. `python3 tools/check_site.py` shows no problems for your files.
2. Start (if needed) `python3 tools/serve.py` in the background, then render-check your pages: load each in
   Playwright at 1300px and 390px, light and dark; zero console/page errors; click a few `Next` buttons in
   each viz. `tools/render_check.py` does this for the whole site and is fine to run.
3. Every `<script type="application/json">` still parses; `<`, `>`, `&` in code are escaped.
4. Grep your files for the tells above (`grep -inE "delve|crucial|robust|leverage|it's worth noting|in this section|let's dive|not just|game-chang|seamless|landscape|journey|tapestry|harness" file`) and confirm zero hits or justified ones.

## Report

Reply with, per chapter: factual errors found and fixed (with the source you checked), numbers updated from
code runs, prose passes made, anything you could not verify and how you reworded it, and any bug in the
reference code. Keep it to the substance.
