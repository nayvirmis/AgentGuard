from backend.app.mcp_client import MCPDocumentClient


async def test_mcp_client_discovers_and_calls_document_search():
    client = MCPDocumentClient()
    await client.start()
    try:
        result = await client.search(
            {
                "query": "assignment extension instructor",
                "corpus": "all",
                "top_k": 2,
                "include_snippets": True,
            }
        )
        assert client.health == "healthy"
        assert result["untrusted_content"] is True
        assert result["results"]
    finally:
        await client.stop()
