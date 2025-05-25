"""Tests for todo validation functions."""

import pytest

from mcp_claude_code.tools.todo.base import TodoBaseTool


# Create a concrete test implementation of TodoBaseTool for testing
class TestTodoBaseTool(TodoBaseTool):
    """Test implementation of TodoBaseTool."""

    @property
    def name(self):
        return "test_todo"

    @property
    def description(self):
        return "Test todo tool"

    @property
    def parameters(self):
        return {}

    @property
    def required(self):
        return []

    async def call(self, ctx, **params):
        return "test"

    def register(self, mcp_server):
        pass


class TestTodoValidation:
    """Test todo validation functions."""

    @pytest.fixture
    def todo_tool(self):
        """Create a test todo tool instance."""
        return TestTodoBaseTool()

    def test_valid_session_ids(self, todo_tool):
        """Test validation of valid session IDs."""
        valid_ids = [
            "session123",
            "1704067200123456789",
            "session_2024-01-01",
            "sess-123",
            "abcde",  # minimum length
            "a" * 100,  # maximum length
            "SESSION_ID_123",
            "session-with-hyphens",
            "session_with_underscores",
            "mixed123_-session",
        ]

        for session_id in valid_ids:
            is_valid, error_msg = todo_tool.validate_session_id(session_id)
            assert is_valid, (
                f"Session ID '{session_id}' should be valid but got error: {error_msg}"
            )
            assert error_msg == ""

    def test_invalid_session_ids(self, todo_tool):
        """Test validation of invalid session IDs."""
        invalid_cases = [
            ("", "Session ID is required but was empty"),
            (None, "Session ID is required but was empty"),
            ("a", "Session ID too short (minimum 5 characters)"),
            ("ab", "Session ID too short (minimum 5 characters)"),
            ("abcd", "Session ID too short (minimum 5 characters)"),
            ("a" * 101, "Session ID too long (maximum 100 characters)"),
            (
                "session with spaces",
                "Session ID can only contain alphanumeric characters, hyphens, and underscores",
            ),
            (
                "session/with/slashes",
                "Session ID can only contain alphanumeric characters, hyphens, and underscores",
            ),
            (
                "session.with.dots",
                "Session ID can only contain alphanumeric characters, hyphens, and underscores",
            ),
            (
                "session@domain.com",
                "Session ID can only contain alphanumeric characters, hyphens, and underscores",
            ),
            (
                "session+plus",
                "Session ID can only contain alphanumeric characters, hyphens, and underscores",
            ),
            (
                "session#hash",
                "Session ID can only contain alphanumeric characters, hyphens, and underscores",
            ),
            (123, "Session ID must be a string"),
            ([], "Session ID must be a string"),
            ({}, "Session ID must be a string"),
        ]

        for session_id, expected_error in invalid_cases:
            is_valid, error_msg = todo_tool.validate_session_id(session_id)
            assert not is_valid, f"Session ID '{session_id}' should be invalid"
            assert expected_error in error_msg

    def test_valid_todo_items(self, todo_tool):
        """Test validation of valid todo items."""
        valid_todos = [
            {
                "id": "task-1",
                "content": "Test task",
                "status": "pending",
                "priority": "high",
            },
            {
                "id": "task_2",
                "content": "Another test task with longer description",
                "status": "in_progress",
                "priority": "medium",
            },
            {
                "id": "completed-task",
                "content": "Completed task",
                "status": "completed",
                "priority": "low",
            },
            {
                "id": "task-with-special-chars",
                "content": "Task with special chars: @#$%^&*()",
                "status": "pending",
                "priority": "high",
            },
            # Test numeric IDs (should be valid now)
            {
                "id": 123,
                "content": "Task with integer ID",
                "status": "pending",
                "priority": "medium",
            },
            {
                "id": 45.6,
                "content": "Task with float ID",
                "status": "in_progress",
                "priority": "low",
            },
        ]

        for todo in valid_todos:
            is_valid, error_msg = todo_tool.validate_todo_item(todo)
            assert is_valid, (
                f"Todo {todo['id']} should be valid but got error: {error_msg}"
            )
            assert error_msg == ""

    def test_invalid_todo_items(self, todo_tool):
        """Test validation of invalid todo items."""
        invalid_cases = [
            # Missing fields
            (
                {"content": "Test", "status": "pending", "priority": "high"},
                "missing required field: id",
            ),
            (
                {"id": "task-1", "status": "pending", "priority": "high"},
                "missing required field: content",
            ),
            (
                {"id": "task-1", "content": "Test", "priority": "high"},
                "missing required field: status",
            ),
            (
                {"id": "task-1", "content": "Test", "status": "pending"},
                "missing required field: priority",
            ),
            # Invalid types
            ("not a dict", "Todo item must be an object"),
            ([], "Todo item must be an object"),
            (None, "Todo item must be an object"),
            # Invalid content
            (
                {
                    "id": "task-1",
                    "content": "",
                    "status": "pending",
                    "priority": "high",
                },
                "Todo content must be a non-empty string",
            ),
            (
                {
                    "id": "task-1",
                    "content": "   ",
                    "status": "pending",
                    "priority": "high",
                },
                "Todo content must be a non-empty string",
            ),
            (
                {
                    "id": "task-1",
                    "content": None,
                    "status": "pending",
                    "priority": "high",
                },
                "Todo content must be a non-empty string",
            ),
            (
                {
                    "id": "task-1",
                    "content": 123,
                    "status": "pending",
                    "priority": "high",
                },
                "Todo content must be a non-empty string",
            ),
            # Invalid status
            (
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "invalid",
                    "priority": "high",
                },
                "Todo status must be one of: pending, in_progress, completed",
            ),
            (
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "done",
                    "priority": "high",
                },
                "Todo status must be one of: pending, in_progress, completed",
            ),
            (
                {"id": "task-1", "content": "Test", "status": "", "priority": "high"},
                "Todo status must be one of: pending, in_progress, completed",
            ),
            (
                {"id": "task-1", "content": "Test", "status": None, "priority": "high"},
                "Todo status must be one of: pending, in_progress, completed",
            ),
            # Invalid priority
            (
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "pending",
                    "priority": "urgent",
                },
                "Todo priority must be one of: high, medium, low",
            ),
            (
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "pending",
                    "priority": "critical",
                },
                "Todo priority must be one of: high, medium, low",
            ),
            (
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "pending",
                    "priority": "",
                },
                "Todo priority must be one of: high, medium, low",
            ),
            (
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "pending",
                    "priority": None,
                },
                "Todo priority must be one of: high, medium, low",
            ),
            # Invalid ID
            (
                {"id": "", "content": "Test", "status": "pending", "priority": "high"},
                "Todo id must not be empty",
            ),
            (
                {
                    "id": "   ",
                    "content": "Test",
                    "status": "pending",
                    "priority": "high",
                },
                "Todo id must not be empty",
            ),
            (
                {
                    "id": None,
                    "content": "Test",
                    "status": "pending",
                    "priority": "high",
                },
                "Todo id is required",
            ),
            # Note: Integer IDs like 123 are now valid, so that test case is removed
        ]

        for todo, expected_error_part in invalid_cases:
            is_valid, error_msg = todo_tool.validate_todo_item(todo)
            assert not is_valid, f"Todo should be invalid: {todo}"
            assert expected_error_part in error_msg

    def test_valid_todos_lists(self, todo_tool):
        """Test validation of valid todo lists."""
        valid_lists = [
            # Empty list
            [],
            # Single todo
            [
                {
                    "id": "task-1",
                    "content": "Test",
                    "status": "pending",
                    "priority": "high",
                }
            ],
            # Multiple todos
            [
                {
                    "id": "task-1",
                    "content": "Task 1",
                    "status": "pending",
                    "priority": "high",
                },
                {
                    "id": "task-2",
                    "content": "Task 2",
                    "status": "in_progress",
                    "priority": "medium",
                },
                {
                    "id": "task-3",
                    "content": "Task 3",
                    "status": "completed",
                    "priority": "low",
                },
            ],
            # All status types
            [
                {
                    "id": "pending-task",
                    "content": "Pending",
                    "status": "pending",
                    "priority": "high",
                },
                {
                    "id": "in-progress-task",
                    "content": "In Progress",
                    "status": "in_progress",
                    "priority": "medium",
                },
                {
                    "id": "completed-task",
                    "content": "Completed",
                    "status": "completed",
                    "priority": "low",
                },
            ],
        ]

        for todos_list in valid_lists:
            is_valid, error_msg = todo_tool.validate_todos_list(todos_list)
            assert is_valid, f"Todos list should be valid but got error: {error_msg}"
            assert error_msg == ""

    def test_invalid_todos_lists(self, todo_tool):
        """Test validation of invalid todo lists."""
        invalid_cases = [
            # Non-list types
            ("not a list", "Todos must be a list"),
            ({"not": "a list"}, "Todos must be a list"),
            (None, "Todos must be a list"),
            # List with invalid todos
            (
                [{"invalid": "todo"}],
                "Todo item 0: Todo item missing required field: content",
            ),
            (
                [
                    {
                        "id": "task-1",
                        "content": "Valid",
                        "status": "pending",
                        "priority": "high",
                    },
                    {
                        "id": "task-2",
                        "content": "",
                        "status": "pending",
                        "priority": "high",
                    },  # Invalid content
                ],
                "Todo item 1: Todo content must be a non-empty string",
            ),
            # Duplicate IDs
            (
                [
                    {
                        "id": "task-1",
                        "content": "Task 1",
                        "status": "pending",
                        "priority": "high",
                    },
                    {
                        "id": "task-1",
                        "content": "Task 2",
                        "status": "completed",
                        "priority": "low",
                    },  # Duplicate ID
                ],
                "Todo items must have unique IDs",
            ),
            (
                [
                    {
                        "id": "duplicate",
                        "content": "First",
                        "status": "pending",
                        "priority": "high",
                    },
                    {
                        "id": "unique",
                        "content": "Middle",
                        "status": "in_progress",
                        "priority": "medium",
                    },
                    {
                        "id": "duplicate",
                        "content": "Last",
                        "status": "completed",
                        "priority": "low",
                    },  # Duplicate ID
                ],
                "Todo items must have unique IDs",
            ),
        ]

        for todos_list, expected_error_part in invalid_cases:
            is_valid, error_msg = todo_tool.validate_todos_list(todos_list)
            assert not is_valid, f"Todos list should be invalid: {todos_list}"
            assert expected_error_part in error_msg

    def test_edge_cases(self, todo_tool):
        """Test edge cases for validation."""
        # Very long content
        long_content = "x" * 10000
        long_todo = {
            "id": "long-task",
            "content": long_content,
            "status": "pending",
            "priority": "high",
        }
        is_valid, error_msg = todo_tool.validate_todo_item(long_todo)
        assert is_valid, f"Long content should be valid: {error_msg}"

        # Very long ID
        long_id = "task-" + "x" * 1000
        long_id_todo = {
            "id": long_id,
            "content": "Test",
            "status": "pending",
            "priority": "high",
        }
        is_valid, error_msg = todo_tool.validate_todo_item(long_id_todo)
        assert is_valid, f"Long ID should be valid: {error_msg}"

        # Large list of todos
        large_list = []
        for i in range(1000):
            large_list.append(
                {
                    "id": f"task-{i}",
                    "content": f"Task {i}",
                    "status": "pending",
                    "priority": "medium",
                }
            )
        is_valid, error_msg = todo_tool.validate_todos_list(large_list)
        assert is_valid, f"Large list should be valid: {error_msg}"
