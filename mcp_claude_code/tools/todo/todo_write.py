"""TodoWrite tool implementation.

This module provides the TodoWrite tool for creating and managing a structured task list for a session.
"""

from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.todo.base import TodoBaseTool, TodoStorage


@final
class TodoWriteTool(TodoBaseTool):
    """Tool for creating and managing a structured task list for a session."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "todo_write"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Use this tool to create and manage a structured task list for your current coding session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.
It also helps the user understand the progress of the task and overall progress of their requests.

## When to Use This Tool
Use this tool proactively in these scenarios:

1. Complex multi-step tasks - When a task requires 3 or more distinct steps or actions
2. Non-trivial and complex tasks - Tasks that require careful planning or multiple operations
3. User explicitly requests todo list - When the user directly asks you to use the todo list
4. User provides multiple tasks - When users provide a list of things to be done (numbered or comma-separated)
5. After receiving new instructions - Immediately capture user requirements as todos. Feel free to edit the todo list based on new information.
6. After completing a task - Mark it complete and add any new follow-up tasks
7. When you start working on a new task, mark the todo as in_progress. Ideally you should only have one todo as in_progress at a time. Complete existing tasks before starting new ones.

## When NOT to Use This Tool

Skip using this tool when:
1. There is only a single, straightforward task
2. The task is trivial and tracking it provides no organizational benefit
3. The task can be completed in less than 3 trivial steps
4. The task is purely conversational or informational

NOTE that you should use should not use this tool if there is only one trivial task to do. In this case you are better off just doing the task directly.

## Task States and Management

1. **Task States**: Use these states to track progress:
   - pending: Task not yet started
   - in_progress: Currently working on (limit to ONE task at a time)
   - completed: Task finished successfully

2. **Task Management**:
   - Update task status in real-time as you work
   - Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
   - Only have ONE task in_progress at any time
   - Complete current tasks before starting new ones

3. **Task Breakdown**:
   - Create specific, actionable items
   - Break complex tasks into smaller, manageable steps
   - Use clear, descriptive task names

When in doubt, use this tool. Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully."""

    @property
    @override
    def parameters(self) -> dict[str, Any]:
        """Get the parameter specifications for the tool.

        Returns:
            Parameter specifications
        """
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Unique identifier for the Claude Desktop session (generate using timestamp command in seconds)",
                },
                "todos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Description of the task to be completed",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "Current status of the task",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "Priority level of the task",
                            },
                            "id": {
                                "type": "string",
                                "description": "Unique identifier for the task",
                            },
                        },
                        "required": ["content", "status", "priority", "id"],
                        "additionalProperties": False,
                    },
                    "description": "The complete todo list to store for this session",
                },
            },
            "required": ["session_id", "todos"],
            "additionalProperties": False,
            "$schema": "http://json-schema.org/draft-07/schema#",
        }

    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.

        Returns:
            List of required parameter names
        """
        return ["session_id", "todos"]

    @override
    async def call(self, ctx: MCPContext, **params: Any) -> str:
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
        todos = params.get("todos")

        if session_id is None:
            await tool_ctx.error("Parameter 'session_id' is required but was None")
            return "Error: Parameter 'session_id' is required but was None"

        if todos is None:
            await tool_ctx.error("Parameter 'todos' is required but was None")
            return "Error: Parameter 'todos' is required but was None"

        session_id = str(session_id)

        # Validate session ID
        is_valid, error_msg = self.validate_session_id(session_id)
        if not is_valid:
            await tool_ctx.error(f"Invalid session_id: {error_msg}")
            return f"Error: Invalid session_id: {error_msg}"

        # Normalize todos list (auto-generate missing fields)
        todos = self.normalize_todos_list(todos)

        # Validate todos list
        is_valid, error_msg = self.validate_todos_list(todos)
        if not is_valid:
            await tool_ctx.error(f"Invalid todos: {error_msg}")
            return f"Error: Invalid todos: {error_msg}"

        await tool_ctx.info(f"Writing {len(todos)} todos for session: {session_id}")

        try:
            # Store todos in memory
            TodoStorage.set_todos(session_id, todos)

            # Log storage stats
            session_count = TodoStorage.get_session_count()
            await tool_ctx.info(
                f"Successfully stored todos. Total active sessions: {session_count}"
            )

            # Provide feedback about the todos
            if todos:
                status_counts = {}
                priority_counts = {}

                for todo in todos:
                    status = todo.get("status", "unknown")
                    priority = todo.get("priority", "unknown")

                    status_counts[status] = status_counts.get(status, 0) + 1
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1

                # Create summary
                summary_parts = []
                if status_counts:
                    status_summary = ", ".join(
                        [f"{count} {status}" for status, count in status_counts.items()]
                    )
                    summary_parts.append(f"Status: {status_summary}")

                if priority_counts:
                    priority_summary = ", ".join(
                        [
                            f"{count} {priority}"
                            for priority, count in priority_counts.items()
                        ]
                    )
                    summary_parts.append(f"Priority: {priority_summary}")

                summary = (
                    f"Successfully stored {len(todos)} todos for session {session_id}.\n"
                    + "; ".join(summary_parts)
                )

                return summary
            else:
                return f"Successfully cleared todos for session {session_id} (stored empty list)."

        except Exception as e:
            await tool_ctx.error(f"Error storing todos: {str(e)}")
            return f"Error storing todos: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this todo write tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def todo_write(
            ctx: MCPContext, session_id: str | int | float, todos: list[dict[str, Any]]
        ) -> str:
            return await tool_self.call(ctx, session_id=session_id, todos=todos)
