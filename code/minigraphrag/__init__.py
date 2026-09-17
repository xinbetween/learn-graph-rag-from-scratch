"""minigraphrag: a small, readable GraphRAG built from scratch for teaching.

Typical offline use:

    from minigraphrag import MockLLM, HashingEmbedder, build_index, load_index
    from minigraphrag.search.local import local_search

    build_index("data/corpus", ".index", MockLLM(), HashingEmbedder())
    index = load_index(".index")
    print(local_search(index, "Why did Kestrel Labs start Project Tern?", MockLLM()).answer)
"""

from .chunking import TextUnit, chunk_documents
from .embeddings import HashingEmbedder
from .indexer import Index, IndexConfig, build_index, load_index
from .llm import AnthropicLLM, CachedLLM, MockLLM, OpenAICompatibleLLM, get_llm

__version__ = "0.1.0"
__all__ = ["TextUnit", "chunk_documents", "HashingEmbedder", "Index", "IndexConfig", "build_index", "load_index",
           "AnthropicLLM", "CachedLLM", "MockLLM", "OpenAICompatibleLLM", "get_llm"]
