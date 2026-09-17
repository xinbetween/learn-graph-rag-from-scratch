from minigraphrag.context import parse_tables
from minigraphrag.reports import build_community_context, generate_all_reports, generate_report
from minigraphrag.tokens import count_tokens


def test_community_context_tables(index):
    community = max(index.communities, key=lambda c: len(c.nodes))
    context = build_community_context(index.graph, community, max_tokens=4000)
    tables = parse_tables(context)
    assert set(tables) == {"Entities", "Relationships"}
    degrees = [int(r["degree"]) for r in tables["Entities"]]
    assert degrees == sorted(degrees, reverse=True)
    small = build_community_context(index.graph, community, max_tokens=300)
    assert count_tokens(small) < count_tokens(context)


def test_generate_report_structure(index, llm):
    community = index.communities[0]
    report = generate_report(llm, build_community_context(index.graph, community), community.id, community.level)
    assert report.title and report.summary and 0 <= report.rating <= 10
    assert report.findings and report.full_content.startswith("# ")


def test_saved_reports(index):
    assert len(index.reports) >= 3
    assert all(r.findings for r in index.reports)


def test_sub_community_substitution(index, llm):
    from minigraphrag.communities import hierarchical_communities

    comms = hierarchical_communities(index.graph, max_cluster_size=4, seed=42, use_leiden=False)
    assert any(c.children for c in comms)
    calls = []

    class Spy:
        def complete(self, prompt, system=None, json=False):
            calls.append(prompt)
            return llm.complete(prompt, system, json)

    reports = generate_all_reports(Spy(), index.graph, comms, max_tokens=400)
    assert any("-----Reports-----" in p for p in calls)  # a parent was summarised from its children's reports
    assert len(reports) == len([c for c in comms if len(c.nodes) >= 2])
