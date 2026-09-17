import math

from minigraphrag.chunking import chunk_by_sentences, chunk_documents, chunk_fixed, split_sentences
from minigraphrag.tokens import count_tokens, truncate_to_tokens


def test_count_tokens_basics():
    assert count_tokens("") == 0
    assert count_tokens("one two three") > 0
    assert count_tokens(truncate_to_tokens("word " * 500, 50)) <= 50


def test_fixed_chunk_overlap_math():
    words = [f"w{i}" for i in range(1000)]
    text = " ".join(words)
    units = chunk_fixed(text, size=300, overlap=50, doc_id="d")
    assert len(units) == math.ceil((1000 - 50) / 250)
    for a, b in zip(units, units[1:]):
        assert a.text.split()[-50:] == b.text.split()[:50]
    for u in units:
        assert text[u.start:u.end] == u.text
    assert units[-1].text.split()[-1] == "w999"
    assert units[0].id == "d-000"


def test_short_text_is_one_chunk():
    assert len(chunk_fixed("just a few words", 300, 50)) == 1
    assert chunk_fixed("", 300, 50) == []


def test_sentence_splitting_keeps_titles():
    text = "Dr. Mira Okafor founded Kestrel Labs. Jonas Vehl joined her! Did it work?"
    sents = [text[s:e].strip() for s, e in split_sentences(text)]
    assert sents == ["Dr. Mira Okafor founded Kestrel Labs.", "Jonas Vehl joined her!", "Did it work?"]


def test_chunk_by_sentences_respects_budget():
    text = " ".join(f"Sentence number {i} is here." for i in range(100))
    units = chunk_by_sentences(text, max_tokens=40, overlap_sentences=1)
    assert len(units) > 1
    assert all(u.n_tokens <= 40 for u in units)
    assert all(u.text.endswith(".") for u in units)


def test_chunk_documents_multiple_docs():
    units = chunk_documents({"a": "x " * 400, "b": "y " * 10}, size=300, overlap=50)
    assert {u.doc_id for u in units} == {"a", "b"}
