"""Filesystem tools package for MCP Claude Code.

This package provides tools for interacting with the filesystem, including reading, writing,
and editing files, directory navigation, and content searching.

Updated for FastMCP v2 with function-based tools.
"""

from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.context import DocumentContext
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.filesystem.content_replace import (
    register_content_replace_tool,
)
from mcp_claude_code.tools.filesystem.directory_tree import register_directory_tree_tool
from mcp_claude_code.tools.filesystem.edit import register_edit_tool
from mcp_claude_code.tools.filesystem.grep import register_grep_tool
from mcp_claude_code.tools.filesystem.grep_ast_tool import register_grep_ast_tool
from mcp_claude_code.tools.filesystem.multi_edit import register_multi_edit_tool
from mcp_claude_code.tools.filesystem.read import register_read_tool
from mcp_claude_code.tools.filesystem.write import register_write_tool

# Export all registration functions
__all__ = [
    "get_read_only_filesystem_tools",
    "get_filesystem_tools",
    "register_filesystem_tools",
]


def get_read_only_filesystem_tools(
    document_context: DocumentContext, permission_manager: PermissionManager
) -> list[BaseTool]:
    """Create instances of read-only filesystem tools.

    Note: All filesystem tools have been converted to function-based tools,
    so this returns an empty list. Function-based tools are registered
    separately and not included in this list.

    Args:
        document_context: Document context for tracking file contents
        permission_manager: Permission manager for access control

    Returns:
        Empty list (all tools are now function-based)
    """
    return []


def get_filesystem_tools(
    document_context: DocumentContext, permission_manager: PermissionManager
) -> list[BaseTool]:
    """Create instances of all filesystem tools.

    Note: All filesystem tools have been converted to function-based tools,
    so this returns an empty list. Function-based tools are registered
    separately and not included in this list.

    Args:
        document_context: Document context for tracking file contents
        permission_manager: Permission manager for access control

    Returns:
        Empty list (all tools are now function-based)
    """
    return []


def register_filesystem_tools(
    mcp_server: FastMCP,
    document_context: DocumentContext,
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Register all filesystem tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
        document_context: Document context for tracking file contents
        permission_manager: Permission manager for access control

    Returns:
        Empty list (all tools are now function-based)
    """
    # Register all function-based tools (FastMCP v2 style)
    register_read_tool(mcp_server)
    register_write_tool(mcp_server)
    register_edit_tool(mcp_server)
    register_multi_edit_tool(mcp_server)
    register_directory_tree_tool(mcp_server)
    register_grep_tool(mcp_server)
    register_grep_ast_tool(mcp_server)
    register_content_replace_tool(mcp_server)

    # Return empty list since all tools are now function-based
    return []
