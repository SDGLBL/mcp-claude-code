"""Shell tools package for MCP Claude Code.

This package provides tools for executing shell commands and scripts.
"""

from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.shell.command_executor import CommandExecutor
from mcp_claude_code.tools.shell.run_command import register_run_command_tool

# Export all tool classes
__all__ = [
    "CommandExecutor",
    "get_shell_tools",
    "register_shell_tools",
]


def get_shell_tools(
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Create instances of all shell tools.

    Note: All shell tools have been converted to function-based tools,
    so this returns an empty list. Function-based tools are registered
    separately and not included in this list.

    Args:
        permission_manager: Permission manager for access control

    Returns:
        Empty list (all tools are now function-based)
    """
    return []


def register_shell_tools(
    mcp_server: FastMCP,
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Register all shell tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
        permission_manager: Permission manager for access control

    Returns:
        Empty list (all tools are now function-based)
    """
    # Initialize the command executor
    command_executor = CommandExecutor(permission_manager)

    # Register function-based tools (FastMCP v2 style)
    register_run_command_tool(mcp_server, command_executor)

    # Return empty list since all tools are now function-based
    return []
