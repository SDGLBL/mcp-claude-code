"""Common utilities for MCP Claude Code tools."""

from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import BaseTool, ToolRegistry
from mcp_claude_code.tools.common.batch_tool import BatchTool


def register_batch_tool(mcp_server: FastMCP, tools: dict[str, BaseTool]) -> None:
    """Register batch tool with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
        tools: Dictionary mapping tool names to tool instances
    """
    batch_tool = BatchTool(tools)
    ToolRegistry.register_tool(mcp_server, batch_tool)
