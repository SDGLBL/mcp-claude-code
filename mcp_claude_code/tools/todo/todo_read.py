"""TodoRead tool implementation.

This module provides the TodoRead tool for reading the current todo list for a session.
"""

import json
from typing import Annotated, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.todo.base import TodoBaseTool, TodoStorage

SessionId = Annotated[
    str | int | float,
    Field(
        description="Unique identifier for the Claude Desktop session (generate using timestamp command)"
    ),
]


class TodoReadToolParams(TypedDict):
    """Parameters for the TodoReadTool.

    Attributes:
        session_id: Unique identifier for the Claude Desktop session (generate using timestamp command)
    """

    session_id: SessionId


@final
class TodoReadTool(TodoBaseTool):
    """Tool for reading the current todo list for a session."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "todo_read"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Use this tool to read the current to-do list for the session. This tool should be used proactively and frequently to ensure that you are aware of
the status of the current task list. You should make use of this tool as often as possible, especially in the following situations:
- At the beginning of conversations to see what's pending
- Before starting new tasks to prioritize work
- When the user asks about previous tasks or plans
- Whenever you're uncertain about what to do next
- After completing tasks to update your understanding of remaining work
- After every few messages to ensure you're on track

Usage:
- This tool requires a session_id parameter to identify the Claude Desktop conversation
- Returns a list of todo items with their status, priority, and content
- Use this information to track progress and plan next steps
- If no todos exist yet for the session, an empty list will be returned"""

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[TodoReadToolParams],
    ) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = self.create_tool_context(ctx)
        self.set_tool_context_info(tool_ctx)

        # Extract parameters
        session_id = params.get("session_id")

        # Validate required parameters for direct calls (not through MCP framework)
        if session_id is None:
            await tool_ctx.error("Parameter 'session_id' is required but was None")
            return "Error: Parameter 'session_id' is required but was None"

        session_id = str(session_id)

        # Validate session ID
        is_valid, error_msg = self.validate_session_id(session_id)
        if not is_valid:
            await tool_ctx.error(f"Invalid session_id: {error_msg}")
            return f"Error: Invalid session_id: {error_msg}"

        await tool_ctx.info(f"Reading todos for session: {session_id}")

        try:
            # Get todos from storage
            todos = TodoStorage.get_todos(session_id)

            # Log status
            if todos:
                await tool_ctx.info(
                    f"Found {len(todos)} todos for session {session_id}"
                )
            else:
                await tool_ctx.info(
                    f"No todos found for session {session_id} (returning empty list)"
                )

            # Return todos as JSON string
            result = json.dumps(todos, indent=2)

            return result

        except Exception as e:
            await tool_ctx.error(f"Error reading todos: {str(e)}")
            return f"Error reading todos: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this todo read tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.description)
        async def todo_read(
            ctx: MCPContext,
            session_id: SessionId,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(ctx, session_id=session_id)
