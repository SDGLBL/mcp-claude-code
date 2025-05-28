"""Todo tools package for MCP Claude Code.

This package provides tools for managing todo lists across different Claude Desktop sessions,
using in-memory storage to maintain separate task lists for each conversation.
"""

from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import BaseTool, ToolRegistry
from mcp_claude_code.tools.todo.todo_read import TodoReadTool
from mcp_claude_code.tools.todo.todo_write import TodoWriteTool

# Export all tool classes
__all__ = [
    "TodoReadTool",
    "TodoWriteTool",
    "get_todo_tools",
    "register_todo_tools",
]


def get_todo_tools() -> list[BaseTool]:
    """Create instances of all todo tools.

    Returns:
        List of todo tool instances
    """
    return [
        TodoReadTool(),
        TodoWriteTool(),
    ]


def register_todo_tools(mcp_server: FastMCP) -> list[BaseTool]:
    """Register all todo tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance

    Returns:
        List of registered tools
    """
    tools = get_todo_tools()
    ToolRegistry.register_tools(mcp_server, tools)
    return tools
