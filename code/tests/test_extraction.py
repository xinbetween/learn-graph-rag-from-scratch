from minigraphrag.chunking import TextUnit
from minigraphrag.extraction import extract_claims, extract_from_unit, parse_claims_output, parse_extraction_output


def test_parser_happy_path():
    text = ('("entity"<|>KESTREL LABS<|>ORGANIZATION<|>Ocean drone startup)##'
            '("relationship"<|>DEEPCAST<|>KESTREL LABS<|>Deepcast supplied sonar<|>8)<|COMPLETE|>')
    ents, rels = parse_extraction_output(text, source_id="u1")
    assert ents[0].name == "KESTREL LABS" and ents[0].source_id == "u1"
    assert rels[0].strength == 8.0 and rels[0].description == "Deepcast supplied sonar"


def test_parser_is_robust_to_messy_output():
    text = """Here are the results:
    ( "Entity" <|> "tidewater institute" <|> organization <|> Research institute )
    ##
    ("RELATIONSHIP"<|>ana ruiz<|>Tidewater Institute<|>Directs it<|>high)
    ("relationship"<|>ONLY SOURCE)
    ("entity"<|>MIRA OKAFOR<|>PERSON<|>CEO)("entity"<|>JONAS VEHL<|>PERSON<|>CTO)
    garbage line without structure
    <|COMPLETE|>"""
    ents, rels = parse_extraction_output(text)
    assert [e.name for e in ents] == ["TIDEWATER INSTITUTE", "MIRA OKAFOR", "JONAS VEHL"]
    assert ents[0].type == "ORGANIZATION"
    assert len(rels) == 1 and rels[0].source == "ANA RUIZ" and rels[0].strength == 1.0


def test_gleaning_recovers_missed_relationships(llm):
    text = ("Dr. Mira Okafor and Jonas Vehl founded Kestrel Labs in Port Avalon. "
            "Tidewater Institute and Halden Reef appear in the same sentence as Deepcast.")
    unit = TextUnit("u", "d", text, 30, 0, len(text))
    no_glean = extract_from_unit(llm, unit, max_gleanings=0)
    glean = extract_from_unit(llm, unit, max_gleanings=1)
    assert no_glean.llm_calls == 1 and glean.llm_calls == 2
    assert len(glean.relationships) > len(no_glean.relationships)
    assert {e.name for e in glean.entities} >= {"DR. MIRA OKAFOR", "KESTREL LABS"}


def test_gleaning_loop_check_stops(llm):
    text = "Marlow Dynamics acquired Deepcast."
    unit = TextUnit("u", "d", text, 5, 0, len(text))
    result = extract_from_unit(llm, unit, max_gleanings=3)
    # continue (nothing missing) -> loop check says N -> stop
    assert result.llm_calls == 3


def test_claims(llm):
    text = "Marlow Dynamics acquired Deepcast in April 2025."
    claims = extract_claims(llm, TextUnit("u", "d", text, 8, 0, len(text)))
    assert claims[0].subject == "MARLOW DYNAMICS" and claims[0].type == "ACQUISITION"
    assert claims[0].start_date == "2025-04-01" and claims[0].end_date is None
    assert parse_claims_output("(A<|>B<|>too few)") == []
