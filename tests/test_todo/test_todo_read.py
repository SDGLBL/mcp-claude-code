"""Tests for TodoRead tool."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from mcp_claude_code.tools.todo.base import TodoBaseTool, TodoStorage
from mcp_claude_code.tools.todo.todo_read import TodoReadTool


class TestTodoReadTool:
    """Test the TodoRead tool."""

    @pytest.fixture
    def todo_read_tool(self):
        """Create a TodoRead tool instance for testing."""
        return TodoReadTool()

    def setup_method(self):
        """Clear storage before each test."""
        TodoStorage._sessions.clear()

    def teardown_method(self):
        """Clear storage after each test."""
        TodoStorage._sessions.clear()

    def test_initialization(self, todo_read_tool: TodoReadTool):
        """Test TodoRead tool initialization."""
        assert todo_read_tool.name == "todo_read"
        assert (
            "read the current to-do list for the session"
            in todo_read_tool.description.lower()
        )

    @pytest.mark.asyncio
    async def test_read_empty_session(self, todo_read_tool: TodoReadTool, mcp_context):
        """Test reading todos from an empty session."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Call the tool
            session_id = "empty-session-123"
            result = await todo_read_tool.call(ctx=mcp_context, session_id=session_id)

            # Verify result is empty JSON array
            assert result == "[]"

            # Verify logging calls
            tool_ctx.info.assert_any_call(f"Reading todos for session: {session_id}")
            tool_ctx.info.assert_any_call(
                f"No todos found for session {session_id} (returning empty list)"
            )

    @pytest.mark.asyncio
    async def test_read_session_with_todos(
        self, todo_read_tool: TodoReadTool, mcp_context
    ):
        """Test reading todos from a session with existing todos."""
        # Set up test data
        session_id = "test-session-456"
        test_todos = [
            {
                "id": "task-1",
                "content": "Complete project setup",
                "status": "in_progress",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "Write documentation",
                "status": "pending",
                "priority": "medium",
            },
            {
                "id": "task-3",
                "content": "Deploy to production",
                "status": "completed",
                "priority": "low",
            },
        ]

        # Store test todos
        TodoStorage.set_todos(session_id, test_todos)

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Call the tool
            result = await todo_read_tool.call(ctx=mcp_context, session_id=session_id)

            # Parse the JSON result
            parsed_result = json.loads(result)
            assert parsed_result == test_todos
            assert len(parsed_result) == 3

            # Verify specific todo items
            assert parsed_result[0]["id"] == "task-1"
            assert parsed_result[0]["status"] == "in_progress"
            assert parsed_result[1]["content"] == "Write documentation"
            assert parsed_result[2]["priority"] == "low"

            # Verify logging calls
            tool_ctx.info.assert_any_call(f"Reading todos for session: {session_id}")
            tool_ctx.info.assert_any_call(
                f"Found {len(test_todos)} todos for session {session_id}"
            )

    @pytest.mark.asyncio
    async def test_invalid_session_id(self, todo_read_tool: TodoReadTool, mcp_context):
        """Test reading with invalid session ID."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Test empty session ID
            result = await todo_read_tool.call(ctx=mcp_context, session_id="")
            assert "Error: Invalid session_id" in result
            assert "Session ID is required but was empty" in result

            # Test short session ID
            result = await todo_read_tool.call(ctx=mcp_context, session_id="ab")
            assert "Error: Invalid session_id" in result
            assert "Session ID too short" in result

            # Test session ID with invalid characters
            result = await todo_read_tool.call(
                ctx=mcp_context, session_id="session with spaces"
            )
            assert "Error: Invalid session_id" in result
            assert "can only contain alphanumeric characters" in result

    @pytest.mark.asyncio
    async def test_missing_session_id(self, todo_read_tool: TodoReadTool, mcp_context):
        """Test reading without providing session_id."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Call without session_id
            result = await todo_read_tool.call(ctx=mcp_context)
            assert "Error: Parameter 'session_id' is required but was None" in result

            # Call with None session_id
            result = await todo_read_tool.call(ctx=mcp_context, session_id=None)
            assert "Error: Parameter 'session_id' is required but was None" in result

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolation(
        self, todo_read_tool: TodoReadTool, mcp_context
    ):
        """Test that reading from different sessions returns different todos."""
        # Set up multiple sessions with different todos
        session1 = "session-1"
        session2 = "session-2"

        todos1 = [
            {
                "id": "task-1",
                "content": "Session 1 task",
                "status": "pending",
                "priority": "high",
            }
        ]
        todos2 = [
            {
                "id": "task-2",
                "content": "Session 2 task A",
                "status": "in_progress",
                "priority": "medium",
            },
            {
                "id": "task-3",
                "content": "Session 2 task B",
                "status": "completed",
                "priority": "low",
            },
        ]

        TodoStorage.set_todos(session1, todos1)
        TodoStorage.set_todos(session2, todos2)

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Read from session 1
            result1 = await todo_read_tool.call(ctx=mcp_context, session_id=session1)
            parsed1 = json.loads(result1)
            assert len(parsed1) == 1
            assert parsed1[0]["content"] == "Session 1 task"

            # Read from session 2
            result2 = await todo_read_tool.call(ctx=mcp_context, session_id=session2)
            parsed2 = json.loads(result2)
            assert len(parsed2) == 2
            assert parsed2[0]["content"] == "Session 2 task A"
            assert parsed2[1]["content"] == "Session 2 task B"

    @pytest.mark.asyncio
    async def test_read_after_update(self, todo_read_tool: TodoReadTool, mcp_context):
        """Test reading todos after they have been updated."""
        session_id = "update-test-session"

        # Initial todos
        initial_todos = [
            {
                "id": "task-1",
                "content": "Initial task",
                "status": "pending",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session_id, initial_todos)

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Read initial todos
            result = await todo_read_tool.call(ctx=mcp_context, session_id=session_id)
            parsed = json.loads(result)
            assert len(parsed) == 1
            assert parsed[0]["content"] == "Initial task"
            assert parsed[0]["status"] == "pending"

            # Update todos
            updated_todos = [
                {
                    "id": "task-1",
                    "content": "Updated task",
                    "status": "completed",
                    "priority": "high",
                },
                {
                    "id": "task-2",
                    "content": "New task",
                    "status": "pending",
                    "priority": "medium",
                },
            ]
            TodoStorage.set_todos(session_id, updated_todos)

            # Read updated todos
            result = await todo_read_tool.call(ctx=mcp_context, session_id=session_id)
            parsed = json.loads(result)
            assert len(parsed) == 2
            assert parsed[0]["content"] == "Updated task"
            assert parsed[0]["status"] == "completed"
            assert parsed[1]["content"] == "New task"

    @pytest.mark.asyncio
    async def test_json_formatting(self, todo_read_tool: TodoReadTool, mcp_context):
        """Test that the result is properly formatted JSON."""
        session_id = "json-test"

        # Todos with special characters that need proper JSON encoding
        todos = [
            {
                "id": "special-task",
                "content": 'Task with "quotes" and \n newlines',
                "status": "pending",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session_id, todos)

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Call the tool
            result = await todo_read_tool.call(ctx=mcp_context, session_id=session_id)

            # Verify it's valid JSON
            parsed = json.loads(result)
            assert isinstance(parsed, list)
            assert len(parsed) == 1
            assert parsed[0]["content"] == 'Task with "quotes" and \n newlines'

    @pytest.mark.asyncio
    async def test_exception_handling(self, todo_read_tool: TodoReadTool, mcp_context):
        """Test exception handling in the read tool."""
        # Mock context calls
        tool_ctx = AsyncMock()

        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Mock TodoStorage.get_todos to raise an exception
            with patch.object(
                TodoStorage, "get_todos", side_effect=Exception("Storage error")
            ):
                result = await todo_read_tool.call(
                    ctx=mcp_context, session_id="test-session"
                )

                assert "Error reading todos: Storage error" in result
                tool_ctx.error.assert_called_with("Error reading todos: Storage error")
