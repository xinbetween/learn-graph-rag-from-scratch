/* Single source of truth for course structure.
   Chapter pages live at chapters/<slug>.html. `prereqs` draws the edges of the course map. */
window.CURRICULUM = {
  title: "Graph RAG from Scratch",
  parts: [
    {
      id: "p0", bridge: "…which gives you a corpus, a codebase and a map. Now see why plain retrieval is not enough. So:", title: "Start here", blurb: "How the course works, the running example, and your toolkit.",
      chapters: [
        { slug: "00-welcome", title: "Welcome: the map and the toolkit", minutes: 25, prereqs: [],
          summary: "What GraphRAG is, how chapters are built, the Kestrel Labs corpus, and setting up the minigraphrag reference code." }
      ]
    },
    {
      id: "p1", bridge: "…which shows exactly where vector search loses the thread. Build the structure it is missing. So:", title: "Foundations", blurb: "LLMs, vector RAG, and the graph ideas everything else stands on.",
      chapters: [
        { slug: "01-llms-and-context", title: "Why LLMs need retrieval", minutes: 35, prereqs: ["00-welcome"],
          summary: "Parametric vs. non-parametric knowledge, context windows, hallucination and grounding." },
        { slug: "02-vector-rag", title: "Build vector RAG from scratch", minutes: 60, prereqs: ["01-llms-and-context"],
          summary: "Chunking, embeddings, cosine search, prompt assembly and citations in ~100 lines." },
        { slug: "03-where-rag-breaks", title: "Where vector RAG breaks", minutes: 40, prereqs: ["02-vector-rag"],
          summary: "Multi-hop questions, global sensemaking questions, and lost relationships between chunks." },
        { slug: "04-graph-fundamentals", title: "Graph fundamentals for RAG", minutes: 55, prereqs: ["01-llms-and-context"],
          summary: "Nodes, edges, adjacency, BFS/DFS, shortest paths, degree, PageRank and modularity." },
        { slug: "05-knowledge-graphs", title: "Knowledge graphs, schemas and query languages", minutes: 55, prereqs: ["04-graph-fundamentals"],
          summary: "Triples vs. property graphs, ontologies, Cypher and SPARQL basics." }
      ]
    },
    {
      id: "p2", bridge: "…which leaves you with a graph, its communities and their summaries. Now search them. So:", title: "Building the graph", blurb: "Knowledge organization: turning raw text into a graph worth searching.",
      chapters: [
        { slug: "06-graph-shapes", title: "Graph shapes for retrieval", minutes: 45, prereqs: ["03-where-rag-breaks", "05-knowledge-graphs"],
          summary: "Lexical graphs, domain graphs, tree indexes (RAPTOR), hybrid and hypergraph designs, and when to pick each." },
        { slug: "07-chunking-text-units", title: "Text units and document structure", minutes: 40, prereqs: ["06-graph-shapes"],
          summary: "Chunk size trade-offs for extraction, overlap, structure-aware splitting and provenance ids." },
        { slug: "08-entity-relation-extraction", title: "Extracting entities and relationships with LLMs", minutes: 70, prereqs: ["07-chunking-text-units"],
          summary: "Extraction prompts, delimiter vs. JSON output, gleaning, parsing and failure modes." },
        { slug: "09-entity-resolution", title: "Entity resolution, merging and summarization", minutes: 55, prereqs: ["08-entity-relation-extraction"],
          summary: "Normalization, fuzzy and embedding matching, merging descriptions and edge weights." },
        { slug: "10-claims-temporal", title: "Claims, covariates and time", minutes: 45, prereqs: ["09-entity-resolution"],
          summary: "Extracting claims with status and dates, and attaching time to facts." },
        { slug: "11-community-detection", title: "Community detection: Louvain and Leiden", minutes: 65, prereqs: ["09-entity-resolution", "04-graph-fundamentals"],
          summary: "Modularity, Louvain from scratch, Leiden's refinement step, hierarchical clustering." },
        { slug: "12-community-reports", title: "Community reports and hierarchical summaries", minutes: 55, prereqs: ["11-community-detection"],
          summary: "Building report context, ranking, bottom-up summarization and RAPTOR-style trees." },
        { slug: "13-storage-indexing", title: "Storing and indexing the graph", minutes: 50, prereqs: ["12-community-reports"],
          summary: "Parquet/JSON artifacts, NetworkX, Neo4j, Postgres, and embedding entities, edges and reports." }
      ]
    },
    {
      id: "p3", bridge: "…which finds the right evidence. Getting it into the model's reasoning is a separate problem. So:", title: "Retrieval", blurb: "Knowledge retrieval: finding the right nodes, paths, subgraphs and summaries.",
      chapters: [
        { slug: "14-local-search", title: "Local search: entity-anchored retrieval", minutes: 60, prereqs: ["13-storage-indexing"],
          summary: "Seed entities from embeddings, expand neighborhoods, budget tokens across tables, cite sources." },
        { slug: "15-global-search", title: "Global search and DRIFT", minutes: 55, prereqs: ["14-local-search"],
          summary: "Map-reduce over community reports, helpfulness scoring, dynamic community selection and DRIFT." },
        { slug: "16-lightrag", title: "Dual-level retrieval with LightRAG", minutes: 45, prereqs: ["14-local-search"],
          summary: "Low- and high-level keywords, entity and relation matching, incremental graph updates." },
        { slug: "17-ppr-hipporag", title: "Personalized PageRank retrieval (HippoRAG)", minutes: 55, prereqs: ["14-local-search"],
          summary: "Random walks with restart, seeding from query entities, and ranking passages by node mass." },
        { slug: "18-paths-and-agents", title: "Path retrieval and LLMs walking the graph", minutes: 60, prereqs: ["17-ppr-hipporag"],
          summary: "PathRAG pruning, Think-on-Graph beam search, Plan-on-Graph self-correction." },
        { slug: "19-subgraph-gnn", title: "Subgraph retrieval and GNN retrievers", minutes: 60, prereqs: ["18-paths-and-agents"],
          summary: "G-Retriever's prize-collecting Steiner tree, GNN-RAG and graph foundation models (GFM-RAG)." },
        { slug: "20-text2cypher", title: "Querying knowledge graphs with Text2Cypher", minutes: 50, prereqs: ["05-knowledge-graphs", "14-local-search"],
          summary: "Schema-grounded query generation, validation, self-repair and safety." },
        { slug: "21-hybrid-design-patterns", title: "Hybrid retrieval and seven Graph RAG designs", minutes: 60, prereqs: ["15-global-search", "17-ppr-hipporag"],
          summary: "BM25 + vectors + graph with RRF; neighborhood expansion, metapaths, subgraph assembly, temporal windows, hybrid rerankers, panels and provenance." }
      ]
    },
    {
      id: "p4", bridge: "…which produces grounded answers. Prove they are better, and make them affordable. So:", title: "Generation", blurb: "Knowledge integration: getting graph evidence into the model's reasoning.",
      chapters: [
        { slug: "22-context-construction", title: "Turning graphs into prompts", minutes: 45, prereqs: ["21-hybrid-design-patterns"],
          summary: "Triples, tables, adjacency text, JSON; ordering, token budgets and citations." },
        { slug: "23-graph-reasoning", title: "Graph-guided reasoning", minutes: 50, prereqs: ["22-context-construction", "18-paths-and-agents"],
          summary: "Graph chain-of-thought, reasoning on graphs, faithful paths and post-retrieval pruning." },
        { slug: "24-training-with-graphs", title: "Training models with graphs", minutes: 50, prereqs: ["23-graph-reasoning"],
          summary: "Graph tokens and soft prompts, instruction tuning (GraphGPT, LLaGA) and RL-trained graph retrievers." }
      ]
    },
    {
      id: "p5", bridge: "…which is a system you can run. The field keeps moving past it. So:", title: "Evaluation and production", blurb: "Measure it, make it cheaper, keep it fresh, run it safely.",
      chapters: [
        { slug: "25-evaluation", title: "Evaluating GraphRAG", minutes: 60, prereqs: ["22-context-construction"],
          summary: "Benchmarks, answer and retrieval metrics, LLM-as-judge pairwise evaluation and pitfalls." },
        { slug: "26-cost-scaling", title: "Cost, latency and scale", minutes: 50, prereqs: ["25-evaluation"],
          summary: "Where indexing cost goes, LazyGraphRAG, FastGraphRAG, caching, batching and small extractor models." },
        { slug: "27-incremental-temporal", title: "Incremental updates and temporal graphs", minutes: 55, prereqs: ["10-claims-temporal", "25-evaluation"],
          summary: "Upserts without full rebuilds, bi-temporal edges, invalidation, Graphiti and Zep." },
        { slug: "28-frameworks-in-practice", title: "Frameworks in practice", minutes: 55, prereqs: ["26-cost-scaling"],
          summary: "Microsoft GraphRAG, LightRAG, neo4j-graphrag and LlamaIndex PropertyGraphIndex: config, prompt tuning, trade-offs." },
        { slug: "29-production-ops", title: "Running GraphRAG in production", minutes: 45, prereqs: ["28-frameworks-in-practice", "27-incremental-temporal"],
          summary: "Access control on graphs, prompt injection through documents, observability and failure modes." }
      ]
    },
    {
      id: "p6", bridge: "…which is everything. Put it together. So:", title: "Frontiers", blurb: "Agents, memory, multimodal graphs, domains and where the research is heading.",
      chapters: [
        { slug: "30-agentic-graphrag", title: "Agentic GraphRAG and graph memory", minutes: 55, prereqs: ["23-graph-reasoning", "27-incremental-temporal"],
          summary: "Graph tools for agents, iterative deep graph search, A-MEM, Zep and Knowledge Graph of Thoughts." },
        { slug: "31-multimodal-hypergraph", title: "Multimodal and hypergraph RAG", minutes: 45, prereqs: ["21-hybrid-design-patterns"],
          summary: "N-ary facts as hyperedges, images and tables as nodes, multimodal knowledge graphs." },
        { slug: "32-domain-graphrag", title: "Domain GraphRAG: code, medicine, finance, law", minutes: 50, prereqs: ["21-hybrid-design-patterns"],
          summary: "Repository graphs, Medical Graph RAG, financial filings and legal citation graphs." },
        { slug: "33-research-map", title: "The research map", minutes: 40, prereqs: ["30-agentic-graphrag"],
          summary: "A taxonomy of the field, key papers by stage, benchmarks, and open problems in 2026." }
      ]
    },
    {
      id: "p7", title: "Capstone projects", blurb: "Four end-to-end builds that combine everything.",
      chapters: [
        { slug: "c1-minigraphrag", title: "Capstone 1: ship MiniGraphRAG end to end", minutes: 480, prereqs: ["25-evaluation"],
          summary: "Index a corpus, serve local, global and PPR search behind an API, and prove it beats vector RAG." },
        { slug: "c2-code-graph", title: "Capstone 2: a codebase assistant on a code graph", minutes: 480, prereqs: ["32-domain-graphrag", "20-text2cypher"],
          summary: "Parse a repository into a symbol graph and answer questions about call chains and impact." },
        { slug: "c3-temporal-memory", title: "Capstone 3: temporal memory for an agent", minutes: 480, prereqs: ["30-agentic-graphrag"],
          summary: "A bi-temporal graph memory that tracks changing facts across conversations." },
        { slug: "c4-enterprise-kgqa", title: "Capstone 4: enterprise knowledge graph QA", minutes: 600, prereqs: ["29-production-ops", "21-hybrid-design-patterns"],
          summary: "Hybrid retrieval with access control, Text2Cypher, evaluation harness and cost report." }
      ]
    },
    {
      id: "ap", title: "Appendices", blurb: "Reference material.",
      chapters: [
        { slug: "glossary", title: "Glossary", minutes: 0, prereqs: [], summary: "Every term used in the course, in one place." },
        { slug: "library", title: "Paper and tool library", minutes: 0, prereqs: [], summary: "All papers, repositories and articles referenced, organized by topic." }
      ]
    }
  ]
};
