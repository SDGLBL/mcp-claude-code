"""TodoRead tool implementation.

This module provides the todo_read tool for reading the current todo list for a session.
Converted to FastMCP v2 function-based pattern.
"""

import json
from typing import Union

from fastmcp import Context as MCPContext
from fastmcp import FastMCP

from mcp_claude_code.tools.todo.base import TodoStorage
from mcp_claude_code.tools.common.context import create_tool_context


async def todo_read(session_id: Union[str, int, float], ctx: MCPContext) -> str:
    """Use this tool to read the current to-do list for the session. This tool should be used proactively and frequently to ensure that you are aware of
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
    - If no todos exist yet for the session, an empty list will be returned

    Args:
        session_id: Unique identifier for the Claude Desktop session (generate using timestamp command)
        ctx: MCP context for the tool call

    Returns:
        Todo read results
    """
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("todo_read")

    if session_id is None:
        await tool_ctx.error("Parameter 'session_id' is required but was None")
        return "Error: Parameter 'session_id' is required but was None"

    session_id = str(session_id)

    # Validate session ID
    from mcp_claude_code.tools.todo.base import TodoBaseTool

    temp_tool = type(
        "TempTool",
        (TodoBaseTool,),
        {
            "name": "temp",
            "description": "",
            "parameters": {},
            "required": [],
            "call": lambda *args: "",
            "register": lambda *args: "",
        },
    )()

    is_valid, error_msg = temp_tool.validate_session_id(session_id)
    if not is_valid:
        await tool_ctx.error(f"Invalid session_id: {error_msg}")
        return f"Error: Invalid session_id: {error_msg}"

    await tool_ctx.info(f"Reading todos for session: {session_id}")

    try:
        # Get todos from storage
        todos = TodoStorage.get_todos(session_id)

        # Log status
        if todos:
            await tool_ctx.info(f"Found {len(todos)} todos for session {session_id}")
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


def register_todo_read_tool(mcp_server: FastMCP) -> None:
    """Register the todo_read tool with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
    """
    mcp_server.tool()(todo_read)
