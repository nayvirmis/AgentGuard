from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import get_settings


class MCPDocumentClient:
    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self.health = "disconnected"

    async def start(self) -> None:
        if self._session:
            return
        settings = get_settings()
        self._stack = AsyncExitStack()
        params = StdioServerParameters(
            command=settings.mcp_server_command,
            args=settings.mcp_args,
        )
        read_stream, write_stream = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()
        tools = await self._session.list_tools()
        if not any(tool.name == "document_search" for tool in tools.tools):
            raise RuntimeError("MCP server did not expose document_search")
        self.health = "healthy"

    async def stop(self) -> None:
        if self._stack:
            await self._stack.aclose()
        self._stack = None
        self._session = None
        self.health = "disconnected"

    async def search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self._session:
            await self.start()
        assert self._session
        result = await self._session.call_tool("document_search", arguments=arguments)
        if getattr(result, "isError", False):
            raise RuntimeError("MCP document_search returned an error")
        for block in result.content:
            if hasattr(block, "text"):
                import json

                return json.loads(block.text)
        structured = getattr(result, "structuredContent", None)
        if structured:
            return structured
        return {"results": [], "untrusted_content": True}


mcp_client = MCPDocumentClient()
