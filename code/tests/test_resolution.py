from minigraphrag.embeddings import HashingEmbedder
from minigraphrag.extraction import Entity
from minigraphrag.resolution import normalize_name, resolve_entities


def E(name, etype):
    return Entity(name, etype, f"{name} description")


def test_normalize_name():
    assert normalize_name("Dr. Mira Okafor") == "MIRA OKAFOR"
    assert normalize_name("the  Kestrel's") == "KESTREL"


def test_aliases_merge_into_canonical_names():
    ents = [E("DR. MIRA OKAFOR", "PERSON"), E("OKAFOR", "PERSON"), E("MIRA OKAFOR", "PERSON"),
            E("TIDEWATER INSTITUTE", "ORGANIZATION"), E("TWI", "ORGANIZATION"), E("TIDEWATER", "ORGANIZATION"),
            E("PROJECT SENTINEL", "PROJECT"), E("SENTINEL", "PROJECT"),
            E("PORT AVALON", "LOCATION"), E("PORT AVALON CITY COUNCIL", "ORGANIZATION"),
            E("TIDEWATER INSITUTE", "ORGANIZATION")]
    m = resolve_entities(ents)
    assert m["OKAFOR"] == m["MIRA OKAFOR"] == "DR. MIRA OKAFOR"
    assert m["TWI"] == m["TIDEWATER"] == m["TIDEWATER INSITUTE"] == "TIDEWATER INSTITUTE"
    assert m["SENTINEL"] == "PROJECT SENTINEL"
    assert m["PORT AVALON"] == "PORT AVALON"  # different type: not merged into the council


def test_ambiguous_alias_stays_separate():
    m = resolve_entities([E("JONAS VEHL", "PERSON"), E("ANNA VEHL", "PERSON"), E("VEHL", "PERSON")])
    assert m["VEHL"] == "VEHL"


def test_embedding_similarity_is_optional():
    m = resolve_entities([E("DEEPCAST", "ORGANIZATION"), E("DEEPCAST", "ORGANIZATION")], embedder=HashingEmbedder())
    assert m == {"DEEPCAST": "DEEPCAST"}
