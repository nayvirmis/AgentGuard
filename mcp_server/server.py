from mcp.server.fastmcp import FastMCP

from .retrieval import search_documents

mcp = FastMCP("AgentGuard Document Search")


@mcp.tool()
def document_search(
    query: str, corpus: str = "all", top_k: int = 3, include_snippets: bool = True
) -> dict:
    """Search seeded academic documents and return untrusted evidence snippets."""
    results = search_documents(query, corpus, top_k)
    if not include_snippets:
        results = [{**result, "snippet": ""} for result in results]
    return {"results": results, "untrusted_content": True}


if __name__ == "__main__":
    mcp.run(transport="stdio")
