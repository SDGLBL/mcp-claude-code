"""Jupyter notebook tools package for MCP Claude Code.

This package provides tools for working with Jupyter notebooks (.ipynb files),
including reading and editing notebook cells.
"""

from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.context import DocumentContext
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.jupyter.notebook_edit import notebook_edit
from mcp_claude_code.tools.jupyter.notebook_read import notebook_read

# Export all tool functions
__all__ = [
    "notebook_read",
    "notebook_edit",
    "get_read_only_jupyter_tools",
    "register_jupyter_tools",
]


def get_read_only_jupyter_tools(
    document_context: DocumentContext, permission_manager: PermissionManager
) -> list[BaseTool]:
    """Create instances of read-only Jupyter notebook tools.

    Note: All Jupyter tools have been converted to function-based tools,
    so this returns an empty list. Function-based tools are registered
    separately and not included in this list.

    Args:
        document_context: Document context for tracking file contents
        permission_manager: Permission manager for access control

    Returns:
        Empty list (all tools are now function-based)
    """
    return []


def register_jupyter_tools(mcp_server: FastMCP) -> list[str]:
    """Register all Jupyter notebook tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance

    Returns:
        List of registered tool names
    """
    # Register notebook read tool
    mcp_server.tool(name="notebook_read")(notebook_read)

    # Register notebook edit tool
    mcp_server.tool(name="notebook_edit")(notebook_edit)

    return ["notebook_read", "notebook_edit"]
