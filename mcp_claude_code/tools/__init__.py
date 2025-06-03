"""Tools package for MCP Claude Code.

This package contains all the tools for the MCP Claude Code server.
It provides a unified interface for registering all tools with an MCP server.

This includes a "think" tool implementation based on Anthropic's research showing
improved performance for complex tool-based interactions when Claude has a dedicated
space for structured thinking. It also includes an "agent" tool that enables Claude
to delegate tasks to sub-agents for concurrent execution and specialized processing.
"""

from fastmcp import FastMCP

from mcp_claude_code.tools.agent import register_agent_tools
from mcp_claude_code.tools.common import register_batch_tool, register_thinking_tool
from mcp_claude_code.tools.common.base import BaseTool

from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.filesystem import register_filesystem_tools
from mcp_claude_code.tools.jupyter import register_jupyter_tools
from mcp_claude_code.tools.shell import register_shell_tools
from mcp_claude_code.tools.todo import register_todo_tools


def register_all_tools(
    mcp_server: FastMCP,
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
        permission_manager: Permission manager for access control
        agent_model: Optional model name for agent tool in LiteLLM format
        agent_max_tokens: Optional maximum tokens for agent responses
        agent_api_key: Optional API key for the LLM provider
        agent_base_url: Optional base URL for the LLM provider API endpoint
        agent_max_iterations: Maximum number of iterations for agent (default: 10)
        agent_max_tool_uses: Maximum number of total tool uses for agent (default: 30)
        enable_agent_tool: Whether to enable the agent tool (default: False)
    """
    # Dictionary to store all registered tools
    all_tools: dict[str, BaseTool] = {}

    # Register all filesystem tools
    filesystem_tools = register_filesystem_tools(mcp_server, permission_manager)
    for tool in filesystem_tools:
        all_tools[tool.name] = tool

    # Register all jupyter tools
    jupyter_tools = register_jupyter_tools(mcp_server, permission_manager)
    for tool in jupyter_tools:
        all_tools[tool.name] = tool

    # Register shell tools
    shell_tools = register_shell_tools(mcp_server, permission_manager)
    for tool in shell_tools:
        all_tools[tool.name] = tool

    # Register agent tools only if enabled
    if enable_agent_tool:
        agent_tools = register_agent_tools(
            mcp_server,
            permission_manager,
            agent_model=agent_model,
            agent_max_tokens=agent_max_tokens,
            agent_api_key=agent_api_key,
            agent_base_url=agent_base_url,
            agent_max_iterations=agent_max_iterations,
            agent_max_tool_uses=agent_max_tool_uses,
        )
        for tool in agent_tools:
            all_tools[tool.name] = tool

    # Register todo tools
    todo_tools = register_todo_tools(mcp_server)
    for tool in todo_tools:
        all_tools[tool.name] = tool

    # Initialize and register thinking tool
    thinking_tool = register_thinking_tool(mcp_server)
    for tool in thinking_tool:
        all_tools[tool.name] = tool

    # Register batch tool
    register_batch_tool(mcp_server, all_tools)
