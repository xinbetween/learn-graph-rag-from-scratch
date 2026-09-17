import json

from minigraphrag import prompts as P
from minigraphrag.llm import CachedLLM, MockLLM, find_mentions, parse_json_response


def test_every_template_contains_its_marker():
    templates = {
        "loop_check": P.GLEANING_LOOP_CHECK_PROMPT, "continue": P.GLEANING_CONTINUE_PROMPT,
        "claims": P.CLAIM_EXTRACTION_PROMPT, "extraction": P.ENTITY_EXTRACTION_PROMPT,
        "summarize": P.SUMMARIZE_DESCRIPTIONS_PROMPT, "report": P.COMMUNITY_REPORT_PROMPT,
        "rating": P.COMMUNITY_RATING_PROMPT, "drift_primer": P.DRIFT_PRIMER_PROMPT, "map": P.GLOBAL_MAP_PROMPT,
        "reduce": P.GLOBAL_REDUCE_PROMPT, "keywords": P.KEYWORD_EXTRACTION_PROMPT,
        "text2cypher": P.TEXT2CYPHER_PROMPT, "judge": P.PAIRWISE_JUDGE_PROMPT, "answer": P.LOCAL_SEARCH_SYSTEM_PROMPT,
    }
    for task, template in templates.items():
        assert P.MARKERS[task] in template, task


def test_mock_extraction_output_format(llm):
    prompt = P.ENTITY_EXTRACTION_PROMPT.format(
        entity_types="ORGANIZATION,PERSON", input_text="Marlow Dynamics acquired Deepcast in April 2025.",
        tuple_delimiter=P.TUPLE_DELIMITER, record_delimiter=P.RECORD_DELIMITER, completion_delimiter=P.COMPLETION_DELIMITER)
    out = llm.complete(prompt)
    assert '("entity"<|>MARLOW DYNAMICS<|>ORGANIZATION' in out
    assert '("relationship"<|>MARLOW DYNAMICS<|>DEEPCAST' in out
    assert out.strip().endswith(P.COMPLETION_DELIMITER)


def test_mock_keywords_and_json(llm):
    data = json.loads(llm.complete(P.KEYWORD_EXTRACTION_PROMPT.format(query="What connects Priya Nair to Deepcast?")))
    assert "Priya Nair" in data["low_level_keywords"] and "Deepcast" in data["low_level_keywords"]
    assert "connect" in data["high_level_keywords"]


def test_find_mentions_prefers_longest():
    surfaces = [m[2] for m in find_mentions("The Port Avalon City Council met Dr. Mira Okafor and TWI.")]
    assert surfaces == ["Port Avalon City Council", "Dr. Mira Okafor", "TWI"]


def test_parse_json_response_handles_fences():
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_response('Sure! {"a": 2} hope that helps') == {"a": 2}
    assert parse_json_response("not json") == {}


def test_cached_llm(tmp_path):
    mock = MockLLM()
    cached = CachedLLM(mock, tmp_path)
    first = cached.complete("hello", system="s")
    second = cached.complete("hello", system="s")
    assert first == second and mock.calls == 1 and cached.hits == 1
