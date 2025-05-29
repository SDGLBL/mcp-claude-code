"""Thinking tool implementation.

This module provides the ThinkingTool for Claude to engage in structured thinking.
"""

from typing import Annotated, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.context import create_tool_context


Thought = Annotated[
    str,
    Field(
        description="The detailed thought process to record",
        min_length=1,
    ),
]


class ThinkingToolParams(TypedDict):
    """Parameters for the ThinkingTool.

    Attributes:
        thought: The detailed thought process to record
    """

    thought: Thought


@final
class ThinkingTool(BaseTool):
    """Tool for Claude to engage in structured thinking."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "think"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Use the tool to think about something. It will not obtain new information or make any changes to the repository, but just log the thought. Use it when complex reasoning or brainstorming is needed. 
Ensure thinking content is concise and accurate, without needing to include code details

Common use cases:
1. When exploring a repository and discovering the source of a bug, call this tool to brainstorm several unique ways of fixing the bug, and assess which change(s) are likely to be simplest and most effective
2. After receiving test results, use this tool to brainstorm ways to fix failing tests
3. When planning a complex refactoring, use this tool to outline different approaches and their tradeoffs
4. When designing a new feature, use this tool to think through architecture decisions and implementation details
5. When debugging a complex issue, use this tool to organize your thoughts and hypotheses
6. When considering changes to the plan or shifts in thinking that the user has not previously mentioned, consider whether it is necessary to confirm with the user. 

<think_example>
Feature Implementation Planning
- New code search feature requirements:
* Search for code patterns across multiple files
* Identify function usages and references
* Analyze import relationships
* Generate summary of matching patterns
- Implementation considerations:
* Need to leverage existing search mechanisms
* Should use regex for pattern matching
* Results need consistent format with other search methods
* Must handle large codebases efficiently
- Design approach:
1. Create new CodeSearcher class that follows existing search patterns
2. Implement core pattern matching algorithm
3. Add result formatting methods
4. Integrate with file traversal system
5. Add caching for performance optimization
- Testing strategy:
* Unit tests for search accuracy
* Integration tests with existing components
* Performance tests with large codebases
</think_example>"""

    def __init__(self) -> None:
        """Initialize the thinking tool."""
        pass

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[ThinkingToolParams],
    ) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = create_tool_context(ctx)
        tool_ctx.set_tool_info(self.name)

        # Extract parameters
        thought = params.get("thought")

        # Validate required thought parameter
        if not thought:
            await tool_ctx.error(
                "Parameter 'thought' is required but was None or empty"
            )
            return "Error: Parameter 'thought' is required but was None or empty"

        if thought.strip() == "":
            await tool_ctx.error("Parameter 'thought' cannot be empty")
            return "Error: Parameter 'thought' cannot be empty"

        # Log the thought but don't take action
        await tool_ctx.info("Thinking process recorded")

        # Return confirmation
        return "I've recorded your thinking process. You can continue with your next action based on this analysis."

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this thinking tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.description)
        async def think(
            ctx: MCPContext,
            thought: Thought,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(ctx, thought=thought)
