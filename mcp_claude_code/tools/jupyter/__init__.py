"""Jupyter notebook tools package for MCP Claude Code.

This package provides tools for working with Jupyter notebooks (.ipynb files),
including reading and editing notebook cells.
"""

from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import BaseTool, ToolRegistry
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.jupyter.notebook_edit import NoteBookEditTool
from mcp_claude_code.tools.jupyter.notebook_read import NotebookReadTool

# Export all tool classes
__all__ = [
    "NotebookReadTool",
    "NoteBookEditTool",
    "get_jupyter_tools",
    "register_jupyter_tools",
]


def get_read_only_jupyter_tools(
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Create instances of read only Jupyter notebook tools.

    Args:
        permission_manager: Permission manager for access control

    Returns:
        List of Jupyter notebook tool instances
    """
    return [
        NotebookReadTool(permission_manager),
    ]


def get_jupyter_tools(permission_manager: PermissionManager) -> list[BaseTool]:
    """Create instances of all Jupyter notebook tools.

    Args:
        permission_manager: Permission manager for access control

    Returns:
        List of Jupyter notebook tool instances
    """
    return [
        NotebookReadTool(permission_manager),
        NoteBookEditTool(permission_manager),
    ]


def register_jupyter_tools(
    mcp_server: FastMCP,
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Register all Jupyter notebook tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
        permission_manager: Permission manager for access control

    Returns:
        List of registered tools
    """
    tools = get_jupyter_tools(permission_manager)
    ToolRegistry.register_tools(mcp_server, tools)
    return tools
