"""Base functionality for todo tools.

This module provides common functionality for todo tools, including in-memory storage
for managing todo lists across different Claude Desktop sessions.
"""

import re
from abc import ABC
from typing import Any, final

from mcp.server.fastmcp import Context as MCPContext

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.context import ToolContext, create_tool_context


@final
class TodoStorage:
    """In-memory storage for todo lists, separated by session ID.

    This class provides persistent storage for the lifetime of the MCP server process,
    allowing different Claude Desktop conversations to maintain separate todo lists.
    """

    # Class-level storage shared across all tool instances
    _sessions: dict[str, list[dict[str, Any]]] = {}

    @classmethod
    def get_todos(cls, session_id: str) -> list[dict[str, Any]]:
        """Get the todo list for a specific session.

        Args:
            session_id: Unique identifier for the Claude Desktop session

        Returns:
            List of todo items for the session, empty list if session doesn't exist
        """
        return cls._sessions.get(session_id, [])

    @classmethod
    def set_todos(cls, session_id: str, todos: list[dict[str, Any]]) -> None:
        """Set the todo list for a specific session.

        Args:
            session_id: Unique identifier for the Claude Desktop session
            todos: Complete list of todo items to store
        """
        cls._sessions[session_id] = todos

    @classmethod
    def get_session_count(cls) -> int:
        """Get the number of active sessions.

        Returns:
            Number of sessions with stored todos
        """
        return len(cls._sessions)

    @classmethod
    def get_all_session_ids(cls) -> list[str]:
        """Get all active session IDs.

        Returns:
            List of all session IDs with stored todos
        """
        return list(cls._sessions.keys())

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        """Delete a session and its todos.

        Args:
            session_id: Session ID to delete

        Returns:
            True if session was deleted, False if it didn't exist
        """
        if session_id in cls._sessions:
            del cls._sessions[session_id]
            return True
        return False


class TodoBaseTool(BaseTool, ABC):
    """Base class for todo tools.

    Provides common functionality for working with todo lists, including
    session ID validation and todo structure validation.
    """

    def create_tool_context(self, ctx: MCPContext) -> ToolContext:
        """Create a tool context with the tool name.

        Args:
            ctx: MCP context

        Returns:
            Tool context
        """
        tool_ctx = create_tool_context(ctx)
        return tool_ctx

    def set_tool_context_info(self, tool_ctx: ToolContext) -> None:
        """Set the tool info on the context.

        Args:
            tool_ctx: Tool context
        """
        tool_ctx.set_tool_info(self.name)

    def validate_session_id(self, session_id: str) -> tuple[bool, str]:
        """Validate session ID format and security.

        Args:
            session_id: Session ID to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for None or empty first
        if session_id is None or session_id == "":
            return False, "Session ID is required but was empty"

        if not isinstance(session_id, str):
            return False, "Session ID must be a string"

        # Check length (reasonable bounds)
        if len(session_id) < 5:
            return False, "Session ID too short (minimum 5 characters)"

        if len(session_id) > 100:
            return False, "Session ID too long (maximum 100 characters)"

        # Check format - allow alphanumeric, hyphens, underscores
        # This prevents path traversal and other security issues
        if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
            return (
                False,
                "Session ID can only contain alphanumeric characters, hyphens, and underscores",
            )

        return True, ""

    def validate_todo_item(self, todo: dict[str, Any]) -> tuple[bool, str]:
        """Validate a single todo item structure.

        Args:
            todo: Todo item to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(todo, dict):
            return False, "Todo item must be an object"

        # Check required fields
        required_fields = ["content", "status", "priority", "id"]
        for field in required_fields:
            if field not in todo:
                return False, f"Todo item missing required field: {field}"

        # Validate content
        content = todo.get("content")
        if not isinstance(content, str) or not content.strip():
            return False, "Todo content must be a non-empty string"

        # Validate status
        valid_statuses = ["pending", "in_progress", "completed"]
        status = todo.get("status")
        if status not in valid_statuses:
            return False, f"Todo status must be one of: {', '.join(valid_statuses)}"

        # Validate priority
        valid_priorities = ["high", "medium", "low"]
        priority = todo.get("priority")
        if priority not in valid_priorities:
            return False, f"Todo priority must be one of: {', '.join(valid_priorities)}"

        # Validate ID
        todo_id = todo.get("id")
        if not isinstance(todo_id, str) or not todo_id.strip():
            return False, "Todo id must be a non-empty string"

        return True, ""

    def validate_todos_list(self, todos: list[dict[str, Any]]) -> tuple[bool, str]:
        """Validate a list of todo items.

        Args:
            todos: List of todo items to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(todos, list):
            return False, "Todos must be a list"

        # Check each todo item
        for i, todo in enumerate(todos):
            is_valid, error_msg = self.validate_todo_item(todo)
            if not is_valid:
                return False, f"Todo item {i}: {error_msg}"

        # Check for duplicate IDs
        todo_ids = [todo.get("id") for todo in todos]
        if len(todo_ids) != len(set(todo_ids)):
            return False, "Todo items must have unique IDs"

        return True, ""
