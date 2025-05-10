"""Tools package for MCP Claude Code.

This package contains all the tools for the MCP Claude Code server.
It provides a unified interface for registering all tools with an MCP server.

This includes a "think" tool implementation based on Anthropic's research showing
improved performance for complex tool-based interactions when Claude has a dedicated
space for structured thinking. It also includes an "agent" tool that enables Claude
to delegate tasks to sub-agents for concurrent execution and specialized processing.
"""

from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.agent import register_agent_tools
from mcp_claude_code.tools.common import register_thinking_tool
from mcp_claude_code.tools.common.context import DocumentContext
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.filesystem import register_filesystem_tools
from mcp_claude_code.tools.jupyter import register_jupyter_tools
from mcp_claude_code.tools.shell import register_shell_tools
from mcp_claude_code.tools.shell.command_executor import CommandExecutor


def register_all_tools(
    mcp_server: FastMCP,
    document_context: DocumentContext,
    permission_manager: PermissionManager,
    agent_model: str | None = None,
    agent_max_tokens: int | None = None,
    agent_api_key: str | None = None,
    agent_base_url: str | None = None,
    agent_max_iterations: int = 10,
    agent_max_tool_uses: int = 30,
    enable_agent_tool: bool = False,
) -> None:
    """Register all Claude Code tools with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
        document_context: Document context for tracking file contents
        permission_manager: Permission manager for access control
        agent_model: Optional model name for agent tool in LiteLLM format
        agent_max_tokens: Optional maximum tokens for agent responses
        agent_api_key: Optional API key for the LLM provider
        agent_base_url: Optional base URL for the LLM provider API endpoint
        agent_max_iterations: Maximum number of iterations for agent (default: 10)
        agent_max_tool_uses: Maximum number of total tool uses for agent (default: 30)
        enable_agent_tool: Whether to enable the agent tool (default: False)
    """
    # Register all filesystem tools
    register_filesystem_tools(mcp_server, document_context, permission_manager)

    # Register all jupyter tools
    register_jupyter_tools(mcp_server, document_context, permission_manager)

    # Register shell tools
    register_shell_tools(mcp_server, permission_manager)

    # Register agent tools only if enabled
    if enable_agent_tool:
        register_agent_tools(
            mcp_server, 
            document_context, 
            permission_manager,
            CommandExecutor(permission_manager),
            agent_model=agent_model,
            agent_max_tokens=agent_max_tokens,
            agent_api_key=agent_api_key,
            agent_base_url=agent_base_url,
            agent_max_iterations=agent_max_iterations,
            agent_max_tool_uses=agent_max_tool_uses
        )
    
    # Initialize and register thinking tool
    register_thinking_tool(mcp_server)
