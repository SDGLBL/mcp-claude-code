"""Base functionality for todo tools.

This module provides common functionality for todo tools, including in-memory storage
for managing todo lists across different Claude Desktop sessions.
"""

import re
import time
from abc import ABC
from typing import Any, final

from fastmcp import Context as MCPContext

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.context import ToolContext, create_tool_context


@final
class TodoStorage:
    """In-memory storage for todo lists, separated by session ID.

    This class provides persistent storage for the lifetime of the MCP server process,
    allowing different Claude Desktop conversations to maintain separate todo lists.
    Each session stores both the todo list and a timestamp of when it was last updated.
    """

    # Class-level storage shared across all tool instances
    # Structure: {session_id: {"todos": [...], "last_updated": timestamp}}
    _sessions: dict[str, dict[str, Any]] = {}

    @classmethod
    def get_todos(cls, session_id: str) -> list[dict[str, Any]]:
        """Get the todo list for a specific session.

        Args:
            session_id: Unique identifier for the Claude Desktop session

        Returns:
            List of todo items for the session, empty list if session doesn't exist
        """
        session_data = cls._sessions.get(session_id, {})
        return session_data.get("todos", [])

    @classmethod
    def set_todos(cls, session_id: str, todos: list[dict[str, Any]]) -> None:
        """Set the todo list for a specific session.

        Args:
            session_id: Unique identifier for the Claude Desktop session
            todos: Complete list of todo items to store
        """
        cls._sessions[session_id] = {"todos": todos, "last_updated": time.time()}

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

    @classmethod
    def get_session_last_updated(cls, session_id: str) -> float | None:
        """Get the last updated timestamp for a session.

        Args:
            session_id: Session ID to check

        Returns:
            Timestamp when session was last updated, or None if session doesn't exist
        """
        session_data = cls._sessions.get(session_id)
        if session_data:
            return session_data.get("last_updated")
        return None

    @classmethod
    def find_latest_active_session(cls) -> str | None:
        """Find the chronologically latest session with unfinished todos.

        Returns the session ID of the most recently updated session that has unfinished todos.
        Returns None if no sessions have unfinished todos.

        Returns:
            Session ID with unfinished todos that was most recently updated, or None if none found
        """
        from mcp_claude_code.prompts.project_todo_reminder import has_unfinished_todos

        latest_session = None
        latest_timestamp = 0

        for session_id, session_data in cls._sessions.items():
            todos = session_data.get("todos", [])
            if has_unfinished_todos(todos):
                last_updated = session_data.get("last_updated", 0)
                if last_updated > latest_timestamp:
                    latest_timestamp = last_updated
                    latest_session = session_id

        return latest_session


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

    def normalize_todo_item(self, todo: dict[str, Any], index: int) -> dict[str, Any]:
        """Normalize a single todo item by auto-generating missing required fields.

        Args:
            todo: Todo item to normalize
            index: Index of the todo item for generating unique IDs

        Returns:
            Normalized todo item with all required fields
        """
        normalized = dict(todo)  # Create a copy

        # Auto-generate ID if missing or normalize existing ID to string
        if "id" not in normalized or not str(normalized.get("id")).strip():
            normalized["id"] = f"todo-{index + 1}"
        else:
            # Ensure ID is stored as a string for consistency
            normalized["id"] = str(normalized["id"]).strip()

        # Auto-generate priority if missing (but don't fix invalid values)
        if "priority" not in normalized:
            normalized["priority"] = "medium"

        # Ensure status defaults to pending if missing (but don't fix invalid values)
        if "status" not in normalized:
            normalized["status"] = "pending"

        return normalized

    def normalize_todos_list(self, todos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize a list of todo items by auto-generating missing fields.

        Args:
            todos: List of todo items to normalize

        Returns:
            Normalized list of todo items with all required fields
        """
        if not isinstance(todos, list):
            return []  # Return empty list for invalid input

        normalized_todos = []
        used_ids = set()

        for i, todo in enumerate(todos):
            if not isinstance(todo, dict):
                continue  # Skip invalid items

            normalized = self.normalize_todo_item(todo, i)

            # Don't auto-fix duplicate IDs - let validation catch them
            used_ids.add(normalized["id"])
            normalized_todos.append(normalized)

        return normalized_todos

    def validate_session_id(self, session_id: str | None) -> tuple[bool, str]:
        """Validate session ID format and security.

        Args:
            session_id: Session ID to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for None or empty first
        if session_id is None or session_id == "":
            return False, "Session ID is required but was empty"

        # Check if it's a string
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
        if todo_id is None:
            return False, "Todo id is required"

        # Accept string, int, or float IDs
        if not isinstance(todo_id, (str, int, float)):
            return False, "Todo id must be a string, integer, or number"

        # Convert to string and check if it's non-empty after stripping
        todo_id_str = str(todo_id).strip()
        if not todo_id_str:
            return False, "Todo id must not be empty"

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
