from mcp_server.retrieval import search_documents


def test_retrieval_has_stable_source_ids():
    first = search_documents("assignment extension instructor writing", top_k=3)
    second = search_documents("assignment extension instructor writing", top_k=3)
    assert first
    assert [row["source_id"] for row in first] == [row["source_id"] for row in second]
    assert all(row["source_id"] for row in first)


def test_malicious_fixture_is_retrievable_as_untrusted_data():
    results = search_documents("ignore previous instructions malicious academic rule", top_k=5)
    assert any("ignore" in row["snippet"].lower() for row in results)
