import numpy as np

from minigraphrag.embeddings import HashingEmbedder, cosine_top_k
from minigraphrag.vector_store import VectorStore


def test_hashing_embedder_deterministic_and_normalised():
    e = HashingEmbedder(dim=128)
    a = e.embed(["Marlow Dynamics acquired Deepcast"])
    b = HashingEmbedder(dim=128).embed(["Marlow Dynamics acquired Deepcast"])
    assert np.allclose(a, b)
    assert np.isclose(np.linalg.norm(a[0]), 1.0)
    assert np.allclose(e.embed([""]), 0)


def test_similar_texts_rank_first():
    e = HashingEmbedder()
    docs = ["Deepcast supplies sonar hardware", "Brightwater Capital invested in Kestrel", "coral reef bleaching"]
    q = e.embed(["who supplies sonar"])[0]
    assert cosine_top_k(q, e.embed(docs), k=2)[0][0] == 0


def test_vector_store_roundtrip(tmp_path):
    e = HashingEmbedder(dim=64)
    store = VectorStore()
    store.add(["a", "b"], e.embed(["reef survey", "series b funding"]), [{"x": 1}, {"x": 2}])
    store.save(tmp_path / "vs")
    loaded = VectorStore.load(tmp_path / "vs")
    assert len(loaded) == 2
    hit = loaded.search(e.embed(["funding round"])[0], k=1)[0]
    assert hit[0] == "b" and hit[2] == {"x": 2}
