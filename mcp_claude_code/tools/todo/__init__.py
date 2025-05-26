"""Todo tools package for MCP Claude Code.

This package provides tools for managing todo lists across different Claude Desktop sessions,
using in-memory storage to maintain separate task lists for each conversation.

Converted to FastMCP v2 function-based pattern.
"""

from fastmcp import FastMCP

from mcp_claude_code.tools.todo.todo_read import register_todo_read_tool
from mcp_claude_code.tools.todo.todo_write import register_todo_write_tool

# Export registration functions
__all__ = [
    "register_todo_tools",
]


def register_todo_tools(mcp_server: FastMCP) -> None:
    """Register all todo tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
    """
    register_todo_read_tool(mcp_server)
    register_todo_write_tool(mcp_server)
