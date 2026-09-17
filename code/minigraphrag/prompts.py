"""All prompt templates in one place.

Prompts are the real "model" of a GraphRAG system: the code around them only
chunks, parses, merges and budgets. Keeping every template here makes it easy
to read them side by side and to tune them for a new domain.

Templates use `str.format` placeholders. Literal braces in JSON examples are
doubled (`{{ }}`). Each template contains a distinctive sentence listed in
`MARKERS`; `MockLLM` uses those to recognise which task it is being asked to do.
"""

TUPLE_DELIMITER = "<|>"
RECORD_DELIMITER = "##"
COMPLETION_DELIMITER = "<|COMPLETE|>"
DEFAULT_ENTITY_TYPES = ["ORGANIZATION", "PERSON", "PROJECT", "LOCATION", "EVENT", "LAW"]

# --------------------------------------------------------------------------- indexing

ENTITY_EXTRACTION_PROMPT = """-Goal-
Given a text document and a list of entity types, identify all entities of those types from the text and all relationships among the identified entities.

-Steps-
1. Identify all entities. For each identified entity, extract:
- entity_name: Name of the entity, capitalized
- entity_type: One of the following types: [{entity_types}]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other. For each pair, extract:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation of why the source and target are related, including dates when stated
- relationship_strength: a numeric score from 1 to 10 indicating the strength of the relationship
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>)

3. Return output in English as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

4. When finished, output {completion_delimiter}

######################
-Example-
######################
Entity_types: ORGANIZATION,PERSON
Text:
Harbor Robotics hired Dana Lee as head of research in 2019.
######################
Output:
("entity"{tuple_delimiter}HARBOR ROBOTICS{tuple_delimiter}ORGANIZATION{tuple_delimiter}Harbor Robotics is a company that hired Dana Lee in 2019)
{record_delimiter}
("entity"{tuple_delimiter}DANA LEE{tuple_delimiter}PERSON{tuple_delimiter}Dana Lee is head of research at Harbor Robotics)
{record_delimiter}
("relationship"{tuple_delimiter}DANA LEE{tuple_delimiter}HARBOR ROBOTICS{tuple_delimiter}Dana Lee became head of research at Harbor Robotics in 2019{tuple_delimiter}9)
{completion_delimiter}

######################
-Real Data-
######################
Entity_types: {entity_types}
Text:
{input_text}
######################
Output:
"""

GLEANING_CONTINUE_PROMPT = """
MANY entities and relationships were missed in the last extraction. Remember to ONLY emit entities that match any of the previously extracted types. Add them below using the same format:
"""

GLEANING_LOOP_CHECK_PROMPT = """
It appears some entities and relationships may have still been missed. Answer Y if there are still entities or relationships that need to be added, or N if there are none. Please answer with a single letter Y or N.
"""

SUMMARIZE_DESCRIPTIONS_PROMPT = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given one entity or relationship, and a list of descriptions, all related to the same entity or relationship, concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions.
If the provided descriptions are contradictory, resolve the contradictions (prefer the most recent dated information) and provide a single, coherent summary.
Write in third person, include the entity names, and keep the summary under {max_tokens} tokens.

#######
-Data-
Entities: {entity_name}
Description List: {description_list}
#######
Output:
"""

CLAIM_EXTRACTION_PROMPT = """-Target activity-
You are an intelligent assistant that helps a human analyst to analyze claims against certain entities presented in a text document.

-Goal-
Given a text document, an entity specification, and a claim description, extract all entities that match the entity specification and all claims against those entities.

-Steps-
1. Extract all named entities that match the entity specification: {entity_specs}
2. For each entity, extract all claims matching the claim description: {claim_description}
For each claim extract: subject, object (or NONE), claim type, claim status (TRUE, FALSE or SUSPECTED), claim start and end dates in ISO-8601 (or NONE), a description with evidence, and the source text quote.
Format each claim as (<subject>{tuple_delimiter}<object>{tuple_delimiter}<claim_type>{tuple_delimiter}<claim_status>{tuple_delimiter}<start_date>{tuple_delimiter}<end_date>{tuple_delimiter}<description>{tuple_delimiter}<source_text>)
Use **{record_delimiter}** as the list delimiter. When finished, output {completion_delimiter}

-Real Data-
Text:
{input_text}
######################
Output:
"""

COMMUNITY_REPORT_PROMPT = """You are an AI assistant that helps a human analyst to perform general information discovery.

# Goal
Write a comprehensive report of a community, given a list of entities that belong to the community as well as their relationships and optional associated claims. The report will be used to inform decision-makers about the community and its potential impact.

# Report Structure
- TITLE: community's name that represents its key entities; short but specific.
- SUMMARY: an executive summary of the community's overall structure and how its entities relate.
- IMPACT SEVERITY RATING: a float score between 0-10 representing the importance of the community.
- RATING EXPLANATION: a single sentence explaining the rating.
- DETAILED FINDINGS: a list of 5-10 key insights. Each has a short summary and a multi-paragraph explanation grounded in the data.

Return output as a well-formed JSON-formatted string with the following format:
{{
    "title": <report_title>,
    "summary": <executive_summary>,
    "rating": <impact_severity_rating>,
    "rating_explanation": <rating_explanation>,
    "findings": [
        {{"summary": <insight_1_summary>, "explanation": <insight_1_explanation>}}
    ]
}}

# Grounding Rules
Points supported by data should list their data references as [Data: <dataset name> (record ids)], e.g. [Data: Entities (5, 7); Relationships (23)]. Do not list more than 5 record ids in a single reference. Do not include information for which no evidence is given.

# Real Data
Use the following text for your answer. Do not make anything up.

Text:
{input_text}

Output:
"""

# --------------------------------------------------------------------------- querying

LOCAL_SEARCH_SYSTEM_PROMPT = """---Role---
You are a helpful assistant responding to questions about data in the tables provided.

---Goal---
Generate a response of the target length and format that answers the user's question, summarizing all information in the input data tables appropriate for the response length and format.
If you don't know the answer, just say so. Do not make anything up.
Points supported by data should list their data references as [Data: <dataset name> (record ids)], e.g. [Data: Sources (12); Relationships (3, 8)].

---Target response length and format---
{response_type}

---Data tables---
{context_data}
"""

GLOBAL_MAP_PROMPT = """---Role---
You are a helpful assistant responding to questions about data in the tables provided.

---Goal---
Generate a list of key points that responds to the user's question, summarizing all relevant information in the community reports below.
Each key point must have a description and an importance score from 0 to 100 reflecting how helpful it is for answering the question. If the reports are not relevant, return an empty list or points with score 0.
Reference supporting reports as [Data: Reports (report ids)].

The response should be JSON formatted as follows:
{{"points": [{{"description": "Description of point 1 [Data: Reports (report ids)]", "score": score_value}}]}}

---Data tables---
{context_data}

---Question---
{question}
"""

GLOBAL_REDUCE_PROMPT = """---Role---
You are a helpful assistant responding to questions about a dataset by synthesizing perspectives from multiple analysts.

---Goal---
Generate a response of the target length and format that responds to the user's question, summarizing all the reports from multiple analysts who focused on different parts of the dataset.
Analyst reports are ranked in descending order of importance. Remove irrelevant information and merge the rest into a comprehensive answer. Preserve the [Data: ...] references.

---Target response length and format---
{response_type}

---Analyst Reports---
{report_data}

---Question---
{question}
"""

COMMUNITY_RATING_PROMPT = """---Role---
You rate how relevant a community report is to a user question for dynamic community selection.

---Goal---
Give a relevance rating from 0 (irrelevant) to 5 (essential).
Return JSON: {{"rating": <int>, "reason": <short reason>}}

---Report---
{report}

---Question---
{question}
"""

DRIFT_PRIMER_PROMPT = """---Role---
You are a research assistant performing the primer step of DRIFT search.

---Goal---
Using the community reports below, write an intermediate answer to the question and propose follow-up questions that would require looking up specific entities in detail.
Return JSON: {{"intermediate_answer": <text>, "follow_up_queries": [<question>, ...], "score": <0-100>}}

---Community reports---
{context_data}

---Question---
{question}
"""

KEYWORD_EXTRACTION_PROMPT = """---Role---
You are a helpful assistant tasked with identifying both high-level and low-level keywords in the user's query.

---Goal---
Given the query, list both high-level and low-level keywords. High-level keywords focus on overarching concepts or themes, while low-level keywords focus on specific entities, details, or concrete terms.

---Output format---
Return JSON: {{"high_level_keywords": [...], "low_level_keywords": [...]}}

---Query---
{query}
"""

TEXT2CYPHER_PROMPT = """Task: Generate a Cypher statement to query a graph database.
Instructions:
Use only the provided node labels, relationship types and properties in the schema.
The query must be read-only (MATCH / OPTIONAL MATCH / WHERE / RETURN / ORDER BY / LIMIT).
Entity names are stored UPPERCASE in the `name` property.
Do not include explanations; return only the Cypher statement.

Schema:
{schema}

Question: {question}
Cypher:
"""

PAIRWISE_JUDGE_PROMPT = """---Role---
You are an impartial judge comparing two answers to the same question.

---Criterion---
{criterion}: {criterion_description}

---Question---
{question}

---Answer A---
{answer_a}

---Answer B---
{answer_b}

---Goal---
Decide which answer is better on the criterion only. Return JSON: {{"winner": "A" | "B" | "TIE", "reasoning": <one sentence>}}
"""

CRITERIA_DESCRIPTIONS = {
    "comprehensiveness": "How much detail does the answer provide to cover all aspects of the question?",
    "diversity": "How varied and rich is the answer in providing different perspectives and insights?",
    "empowerment": "How well does the answer help the reader understand and make informed judgements (e.g. by citing sources)?",
    "directness": "How specifically and clearly does the answer address the question?",
}

# Distinctive phrases used by MockLLM to route prompts. Order matters: gleaning
# prompts *contain* the extraction prompt, so they must be checked first.
MARKERS = {
    "loop_check": "Answer Y if there are still entities or relationships",
    "continue": "MANY entities and relationships were missed",
    "claims": "all claims against those entities",
    "extraction": "identify all entities of those types from the text",
    "summarize": "generating a comprehensive summary of the data provided below",
    "report": "Write a comprehensive report of a community",
    "rating": "for dynamic community selection",
    "drift_primer": "primer step of DRIFT search",
    "map": "importance score from 0 to 100",
    "reduce": "perspectives from multiple analysts",
    "keywords": "high-level and low-level keywords",
    "text2cypher": "Generate a Cypher statement",
    "judge": "impartial judge comparing two answers",
    "answer": "responding to questions about data in the tables provided",
}
