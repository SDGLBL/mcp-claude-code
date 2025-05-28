"""Tests for TodoWrite tool."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_claude_code.tools.todo.base import TodoBaseTool, TodoStorage
from mcp_claude_code.tools.todo.todo_write import TodoWriteTool


class TestTodoWriteTool:
    """Test the TodoWrite tool."""

    @pytest.fixture
    def todo_write_tool(self):
        """Create a TodoWrite tool instance for testing."""
        return TodoWriteTool()

    def setup_method(self):
        """Clear storage before each test."""
        TodoStorage._sessions.clear()

    def teardown_method(self):
        """Clear storage after each test."""
        TodoStorage._sessions.clear()

    def test_initialization(self, todo_write_tool: TodoWriteTool):
        """Test TodoWrite tool initialization."""
        assert todo_write_tool.name == "todo_write"
        assert (
            "create and manage a structured task list"
            in todo_write_tool.description.lower()
        )

    @pytest.mark.asyncio
    async def test_write_empty_todos(self, todo_write_tool: TodoWriteTool, mcp_context):
        """Test writing an empty todos list."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Call the tool with empty list
            session_id = "empty-test-session"
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=[]
            )

            # Verify result
            assert "Successfully cleared todos for session" in result
            assert session_id in result

            # Verify storage
            stored_todos = TodoStorage.get_todos(session_id)
            assert stored_todos == []
            assert TodoStorage.get_session_count() == 1

            # Verify logging calls
            tool_ctx.info.assert_any_call(f"Writing 0 todos for session: {session_id}")

    @pytest.mark.asyncio
    async def test_write_valid_todos(self, todo_write_tool: TodoWriteTool, mcp_context):
        """Test writing valid todos to a session."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Prepare test data
            session_id = "valid-test-session"
            test_todos = [
                {
                    "id": "task-1",
                    "content": "Implement user authentication",
                    "status": "in_progress",
                    "priority": "high",
                },
                {
                    "id": "task-2",
                    "content": "Write unit tests",
                    "status": "pending",
                    "priority": "medium",
                },
                {
                    "id": "task-3",
                    "content": "Update documentation",
                    "status": "completed",
                    "priority": "low",
                },
            ]

            # Call the tool
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=test_todos
            )

            # Verify result contains summary
            assert f"Successfully stored 3 todos for session {session_id}" in result
            assert "Status: 1 in_progress, 1 pending, 1 completed" in result
            assert "Priority: 1 high, 1 medium, 1 low" in result

            # Verify storage
            stored_todos = TodoStorage.get_todos(session_id)
            assert stored_todos == test_todos
            assert len(stored_todos) == 3

            # Verify logging calls
            tool_ctx.info.assert_any_call(f"Writing 3 todos for session: {session_id}")

    @pytest.mark.asyncio
    async def test_update_existing_session(
        self, todo_write_tool: TodoWriteTool, mcp_context
    ):
        """Test updating todos in an existing session."""
        session_id = "update-session"

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
            # Updated todos
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

            # Call the tool
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=updated_todos
            )

            # Verify result
            assert f"Successfully stored 2 todos for session {session_id}" in result

            # Verify storage was updated
            stored_todos = TodoStorage.get_todos(session_id)
            assert stored_todos == updated_todos
            assert len(stored_todos) == 2
            assert stored_todos[0]["content"] == "Updated task"
            assert stored_todos[0]["status"] == "completed"

            # Verify still only one session
            assert TodoStorage.get_session_count() == 1

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, todo_write_tool: TodoWriteTool, mcp_context):
        """Test writing todos to multiple sessions."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Session 1
            session1 = "session-1"
            todos1 = [
                {
                    "id": "task-1",
                    "content": "Session 1 task",
                    "status": "pending",
                    "priority": "high",
                }
            ]

            await todo_write_tool.call(
                ctx=mcp_context, session_id=session1, todos=todos1
            )

            # Session 2
            session2 = "session-2"
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

            await todo_write_tool.call(
                ctx=mcp_context, session_id=session2, todos=todos2
            )

            # Verify session isolation
            assert TodoStorage.get_session_count() == 2
            assert TodoStorage.get_todos(session1) == todos1
            assert TodoStorage.get_todos(session2) == todos2
            assert len(TodoStorage.get_todos(session1)) == 1
            assert len(TodoStorage.get_todos(session2)) == 2

    @pytest.mark.asyncio
    async def test_invalid_session_id(
        self, todo_write_tool: TodoWriteTool, mcp_context
    ):
        """Test writing with invalid session ID."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            valid_todos = [
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "pending",
                    "priority": "high",
                }
            ]

            # Test empty session ID
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id="", todos=valid_todos
            )
            assert "Error: Invalid session_id" in result
            assert "Session ID is required but was empty" in result

            # Test short session ID
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id="ab", todos=valid_todos
            )
            assert "Error: Invalid session_id" in result
            assert "Session ID too short" in result

            # Test session ID with invalid characters
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id="session/invalid", todos=valid_todos
            )
            assert "Error: Invalid session_id" in result

    @pytest.mark.asyncio
    async def test_invalid_todos(self, todo_write_tool: TodoWriteTool, mcp_context):
        """Test writing invalid todos."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            session_id = "test-session"

            # Test that missing fields are auto-generated (normalization feature)
            todos_with_missing_fields = [
                {"id": "task-1", "content": "Test", "status": "pending"}
            ]  # Missing priority - should be auto-generated as "medium"
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=todos_with_missing_fields
            )
            assert "Successfully stored" in result
            assert (
                "Priority: 1 medium" in result
            )  # Should auto-generate medium priority

            # Test invalid status
            invalid_todos = [
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "invalid",
                    "priority": "high",
                }
            ]
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=invalid_todos
            )
            assert "Error: Invalid todos" in result
            assert "Todo status must be one of" in result

            # Test duplicate IDs
            invalid_todos = [
                {
                    "id": "task-1",
                    "content": "Test 1",
                    "status": "pending",
                    "priority": "high",
                },
                {
                    "id": "task-1",
                    "content": "Test 2",
                    "status": "completed",
                    "priority": "low",
                },
            ]
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=invalid_todos
            )
            assert "Error: Invalid todos" in result
            assert "Todo items must have unique IDs" in result

    @pytest.mark.asyncio
    async def test_missing_parameters(
        self, todo_write_tool: TodoWriteTool, mcp_context
    ):
        """Test writing without required parameters."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            valid_todos = [
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "pending",
                    "priority": "high",
                }
            ]

            # Test missing session_id
            result = await todo_write_tool.call(ctx=mcp_context, todos=valid_todos)
            assert "Error: Parameter 'session_id' is required but was None" in result

            # Test missing todos
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id="test-session"
            )
            assert "Error: Parameter 'todos' is required but was None" in result

            # Test None todos
            result = await todo_write_tool.call(
                ctx=mcp_context, session_id="test-session", todos=None
            )
            assert "Error: Parameter 'todos' is required but was None" in result

    @pytest.mark.asyncio
    async def test_status_and_priority_counts(
        self, todo_write_tool: TodoWriteTool, mcp_context
    ):
        """Test that status and priority counts are correctly reported."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            session_id = "count-test"
            todos = [
                {
                    "id": "task-1",
                    "content": "High priority pending",
                    "status": "pending",
                    "priority": "high",
                },
                {
                    "id": "task-2",
                    "content": "High priority in progress",
                    "status": "in_progress",
                    "priority": "high",
                },
                {
                    "id": "task-3",
                    "content": "Medium priority pending",
                    "status": "pending",
                    "priority": "medium",
                },
                {
                    "id": "task-4",
                    "content": "Low priority completed",
                    "status": "completed",
                    "priority": "low",
                },
                {
                    "id": "task-5",
                    "content": "Low priority completed 2",
                    "status": "completed",
                    "priority": "low",
                },
            ]

            result = await todo_write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=todos
            )

            # Verify counts in result
            assert (
                "2 pending" in result
                and "1 in_progress" in result
                and "2 completed" in result
            )
            assert "2 high" in result and "1 medium" in result and "2 low" in result

    @pytest.mark.asyncio
    async def test_large_todos_list(self, todo_write_tool: TodoWriteTool, mcp_context):
        """Test writing a large number of todos."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            session_id = "large-test"

            # Create 100 todos
            large_todos = []
            for i in range(100):
                large_todos.append(
                    {
                        "id": f"task-{i}",
                        "content": f"Task number {i}",
                        "status": ["pending", "in_progress", "completed"][i % 3],
                        "priority": ["high", "medium", "low"][i % 3],
                    }
                )

            result = await todo_write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=large_todos
            )

            # Verify result
            assert f"Successfully stored 100 todos for session {session_id}" in result

            # Verify storage
            stored_todos = TodoStorage.get_todos(session_id)
            assert len(stored_todos) == 100
            assert stored_todos == large_todos

    @pytest.mark.asyncio
    async def test_exception_handling(
        self, todo_write_tool: TodoWriteTool, mcp_context
    ):
        """Test exception handling in the write tool."""
        # Mock context calls
        tool_ctx = AsyncMock()

        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Mock TodoStorage.set_todos to raise an exception
            with patch.object(
                TodoStorage, "set_todos", side_effect=Exception("Storage error")
            ):
                valid_todos = [
                    {
                        "id": "task-1",
                        "content": "Test",
                        "status": "pending",
                        "priority": "high",
                    }
                ]
                result = await todo_write_tool.call(
                    ctx=mcp_context, session_id="test-session", todos=valid_todos
                )

                assert "Error storing todos: Storage error" in result
                tool_ctx.error.assert_called_with("Error storing todos: Storage error")

    @pytest.mark.asyncio
    async def test_todos_with_special_characters(
        self, todo_write_tool: TodoWriteTool, mcp_context
    ):
        """Test writing todos with special characters in content."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            session_id = "special-chars-test"
            todos = [
                {
                    "id": "special-task",
                    "content": 'Task with "quotes", newlines\n, and special chars: @#$%^&*()',
                    "status": "pending",
                    "priority": "high",
                }
            ]

            result = await todo_write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=todos
            )

            # Verify success
            assert "Successfully stored 1 todos" in result

            # Verify storage preserved special characters
            stored_todos = TodoStorage.get_todos(session_id)
            assert stored_todos[0]["content"] == todos[0]["content"]
