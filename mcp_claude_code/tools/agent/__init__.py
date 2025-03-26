"""Agent tools for MCP Claude Code.

This module provides tools that allow Claude to delegate tasks to sub-agents,
enabling concurrent execution of multiple operations and specialized processing.
"""

from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.agent.agent_tool import AgentTool
from mcp_claude_code.tools.common.base import BaseTool, ToolRegistry
from mcp_claude_code.tools.common.context import DocumentContext
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.shell.command_executor import CommandExecutor


def register_agent_tools(
    mcp_server: FastMCP,
    document_context: DocumentContext,
    permission_manager: PermissionManager,
    command_executor: CommandExecutor,
) -> list[BaseTool]:
    """Register agent tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
        document_context: Document context for tracking file contents
        permission_manager: Permission manager for access control

    Returns:
        List of registered tools
    """
    # Create agent tool
    agent_tool = AgentTool(document_context, permission_manager,command_executor)

    # Register agent tool
    ToolRegistry.register_tool(mcp_server, agent_tool)

    # Return list of registered tools
    return [agent_tool]
