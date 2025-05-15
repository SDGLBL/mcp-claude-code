"""Shell tools package for MCP Claude Code.

This package provides tools for executing shell commands and scripts.
"""

from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.common.base import BaseTool, ToolRegistry
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.shell.command_executor import CommandExecutor
from mcp_claude_code.tools.shell.run_command import RunCommandTool
from mcp_claude_code.tools.shell.run_script import RunScriptTool
from mcp_claude_code.tools.shell.script_tool import ScriptTool

# Export all tool classes
__all__ = [
    "RunCommandTool",
    "RunScriptTool",
    "ScriptTool",
    "CommandExecutor",
    "get_shell_tools",
    "register_shell_tools",
]


def get_shell_tools(
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Create instances of all shell tools.

    Args:
        permission_manager: Permission manager for access control

    Returns:
        List of shell tool instances
    """
    # Initialize the command executor
    command_executor = CommandExecutor(permission_manager)

    return [
        RunCommandTool(permission_manager, command_executor),
        RunScriptTool(permission_manager, command_executor),
        ScriptTool(permission_manager, command_executor),
    ]


def register_shell_tools(
    mcp_server: FastMCP,
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Register all shell tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
        permission_manager: Permission manager for access control

    Returns:
        List of registered tools
    """
    tools = get_shell_tools(permission_manager)
    ToolRegistry.register_tools(mcp_server, tools)
    return tools
