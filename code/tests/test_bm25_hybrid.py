from minigraphrag.search.bm25 import BM25
from minigraphrag.search.hybrid import reciprocal_rank_fusion


def test_bm25_ordering():
    docs = ["Deepcast supplied sonar to Kestrel Labs", "Brightwater Capital led the Series B",
            "sonar sonar sonar sonar array design", "the reef"]
    bm = BM25(docs)
    results = bm.search("Deepcast sonar", top_k=4)
    assert results[0][0] == 0  # rare term "deepcast" outweighs repeated "sonar"
    assert {i for i, _ in results} == {0, 2}  # zero-score docs omitted
    assert bm.get_scores("Series B")[1] > 0


def test_bm25_length_normalisation():
    bm = BM25(["tern", "tern " + "filler " * 50])
    scores = bm.get_scores("tern")
    assert scores[0] > scores[1]


def test_rrf():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"], ["b", "e"]], k=60)
    assert fused[0][0] == "b"
    assert dict(fused)["a"] > dict(fused)["d"]
    assert abs(dict(fused)["e"] - 1 / 62) < 1e-12
    weighted = reciprocal_rank_fusion([["a"], ["b"]], weights=[1.0, 2.0])
    assert weighted[0][0] == "b"
