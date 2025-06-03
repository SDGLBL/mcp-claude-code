"""Filesystem tools package for MCP Claude Code.

This package provides tools for interacting with the filesystem, including reading, writing,
and editing files, directory navigation, and content searching.
"""

from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import BaseTool, ToolRegistry

from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.filesystem.content_replace import ContentReplaceTool
from mcp_claude_code.tools.filesystem.directory_tree import DirectoryTreeTool
from mcp_claude_code.tools.filesystem.edit import Edit
from mcp_claude_code.tools.filesystem.grep import Grep
from mcp_claude_code.tools.filesystem.grep_ast_tool import GrepAstTool
from mcp_claude_code.tools.filesystem.multi_edit import MultiEdit
from mcp_claude_code.tools.filesystem.read import ReadTool
from mcp_claude_code.tools.filesystem.write import Write

# Export all tool classes
__all__ = [
    "ReadTool",
    "Write",
    "Edit",
    "MultiEdit",
    "DirectoryTreeTool",
    "Grep",
    "ContentReplaceTool",
    "GrepAstTool",
    "get_filesystem_tools",
    "register_filesystem_tools",
]


def get_read_only_filesystem_tools(
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Create instances of read-only filesystem tools.

    Args:
        permission_manager: Permission manager for access control

    Returns:
        List of read-only filesystem tool instances
    """
    return [
        ReadTool(permission_manager),
        DirectoryTreeTool(permission_manager),
        Grep(permission_manager),
        GrepAstTool(permission_manager),
    ]


def get_filesystem_tools(permission_manager: PermissionManager) -> list[BaseTool]:
    """Create instances of all filesystem tools.

    Args:
        permission_manager: Permission manager for access control

    Returns:
        List of filesystem tool instances
    """
    return [
        ReadTool(permission_manager),
        Write(permission_manager),
        Edit(permission_manager),
        MultiEdit(permission_manager),
        DirectoryTreeTool(permission_manager),
        Grep(permission_manager),
        ContentReplaceTool(permission_manager),
        GrepAstTool(permission_manager),
    ]


def register_filesystem_tools(
    mcp_server: FastMCP,
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Register all filesystem tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
        permission_manager: Permission manager for access control

    Returns:
        List of registered tools
    """
    tools = get_filesystem_tools(permission_manager)
    ToolRegistry.register_tools(mcp_server, tools)
    return tools
