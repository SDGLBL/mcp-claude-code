"""Tests for project todo reminder functionality."""

from mcp_claude_code.prompts.project_todo_reminder import (
    PROJECT_TODO_EMPTY_REMINDER,
    format_todo_list_concise,
    get_project_todo_reminder,
    has_unfinished_todos,
)
from mcp_claude_code.tools.todo.base import TodoStorage


class TestFormatTodoListConcise:
    """Test the format_todo_list_concise function."""

    def test_empty_list(self):
        """Test formatting empty todo list."""
        result = format_todo_list_concise([])
        assert result == "No todos found."

    def test_single_todo_pending(self):
        """Test formatting single pending todo."""
        todos = [
            {
                "id": "task-1",
                "content": "Test task",
                "status": "pending",
                "priority": "high",
            }
        ]
        result = format_todo_list_concise(todos)
        expected = "[ ] 🔴 Test task (id: task-1)"
        assert result == expected

    def test_single_todo_in_progress(self):
        """Test formatting single in-progress todo."""
        todos = [
            {
                "id": "task-1",
                "content": "Test task",
                "status": "in_progress",
                "priority": "medium",
            }
        ]
        result = format_todo_list_concise(todos)
        expected = "[~] 🟡 Test task (id: task-1)"
        assert result == expected

    def test_single_todo_completed(self):
        """Test formatting single completed todo."""
        todos = [
            {
                "id": "task-1",
                "content": "Test task",
                "status": "completed",
                "priority": "low",
            }
        ]
        result = format_todo_list_concise(todos)
        expected = "[✓] 🟢 Test task (id: task-1)"
        assert result == expected

    def test_multiple_todos_mixed_status(self):
        """Test formatting multiple todos with mixed statuses."""
        todos = [
            {
                "id": "task-1",
                "content": "Completed task",
                "status": "completed",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "In progress task",
                "status": "in_progress",
                "priority": "medium",
            },
            {
                "id": "task-3",
                "content": "Pending task",
                "status": "pending",
                "priority": "low",
            },
        ]
        result = format_todo_list_concise(todos)
        expected_lines = [
            "[✓] 🔴 Completed task (id: task-1)",
            "[~] 🟡 In progress task (id: task-2)",
            "[ ] 🟢 Pending task (id: task-3)",
        ]
        expected = "\n".join(expected_lines)
        assert result == expected

    def test_all_priority_levels(self):
        """Test formatting todos with all priority levels."""
        todos = [
            {
                "id": "high-task",
                "content": "High priority task",
                "status": "pending",
                "priority": "high",
            },
            {
                "id": "med-task",
                "content": "Medium priority task",
                "status": "pending",
                "priority": "medium",
            },
            {
                "id": "low-task",
                "content": "Low priority task",
                "status": "pending",
                "priority": "low",
            },
        ]
        result = format_todo_list_concise(todos)
        expected_lines = [
            "[ ] 🔴 High priority task (id: high-task)",
            "[ ] 🟡 Medium priority task (id: med-task)",
            "[ ] 🟢 Low priority task (id: low-task)",
        ]
        expected = "\n".join(expected_lines)
        assert result == expected

    def test_unknown_status_and_priority(self):
        """Test formatting todos with unknown status and priority."""
        todos = [
            {
                "id": "task-1",
                "content": "Task with unknown status",
                "status": "unknown_status",
                "priority": "unknown_priority",
            }
        ]
        result = format_todo_list_concise(todos)
        expected = "[?] ⚪ Task with unknown status (id: task-1)"
        assert result == expected

    def test_missing_fields_with_defaults(self):
        """Test formatting todos with missing fields using defaults."""
        todos = [
            {
                "id": "task-1",
                "content": "Task with missing fields",
                # Missing status and priority - should use defaults from get()
            }
        ]
        result = format_todo_list_concise(todos)
        expected = "[?] 🟡 Task with missing fields (id: task-1)"
        assert result == expected

    def test_empty_content_and_id(self):
        """Test formatting todos with empty content and id."""
        todos = [
            {
                "id": "",
                "content": "",
                "status": "pending",
                "priority": "medium",
            }
        ]
        result = format_todo_list_concise(todos)
        expected = "[ ] 🟡 No content (id: no-id)"
        assert result == expected

    def test_complex_content(self):
        """Test formatting todos with complex content."""
        todos = [
            {
                "id": "complex-task",
                "content": "Implement user authentication with OAuth2 and JWT tokens",
                "status": "in_progress",
                "priority": "high",
            }
        ]
        result = format_todo_list_concise(todos)
        expected = "[~] 🔴 Implement user authentication with OAuth2 and JWT tokens (id: complex-task)"
        assert result == expected


class TestHasUnfinishedTodos:
    """Test the has_unfinished_todos function."""

    def test_empty_list(self):
        """Test empty todo list."""
        result = has_unfinished_todos([])
        assert result is False

    def test_all_completed(self):
        """Test list with all completed todos."""
        todos = [
            {
                "id": "task-1",
                "content": "Completed task 1",
                "status": "completed",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "Completed task 2",
                "status": "completed",
                "priority": "medium",
            },
        ]
        result = has_unfinished_todos(todos)
        assert result is False

    def test_has_pending_todos(self):
        """Test list with pending todos."""
        todos = [
            {
                "id": "task-1",
                "content": "Completed task",
                "status": "completed",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "Pending task",
                "status": "pending",
                "priority": "medium",
            },
        ]
        result = has_unfinished_todos(todos)
        assert result is True

    def test_has_in_progress_todos(self):
        """Test list with in-progress todos."""
        todos = [
            {
                "id": "task-1",
                "content": "Completed task",
                "status": "completed",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "In progress task",
                "status": "in_progress",
                "priority": "medium",
            },
        ]
        result = has_unfinished_todos(todos)
        assert result is True

    def test_mixed_unfinished_todos(self):
        """Test list with both pending and in-progress todos."""
        todos = [
            {
                "id": "task-1",
                "content": "Pending task",
                "status": "pending",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "In progress task",
                "status": "in_progress",
                "priority": "medium",
            },
            {
                "id": "task-3",
                "content": "Completed task",
                "status": "completed",
                "priority": "low",
            },
        ]
        result = has_unfinished_todos(todos)
        assert result is True

    def test_only_pending_todos(self):
        """Test list with only pending todos."""
        todos = [
            {
                "id": "task-1",
                "content": "Pending task 1",
                "status": "pending",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "Pending task 2",
                "status": "pending",
                "priority": "medium",
            },
        ]
        result = has_unfinished_todos(todos)
        assert result is True

    def test_only_in_progress_todos(self):
        """Test list with only in-progress todos."""
        todos = [
            {
                "id": "task-1",
                "content": "In progress task 1",
                "status": "in_progress",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "In progress task 2",
                "status": "in_progress",
                "priority": "medium",
            },
        ]
        result = has_unfinished_todos(todos)
        assert result is True

    def test_missing_status_field(self):
        """Test todos with missing status field (should default to pending)."""
        todos = [
            {
                "id": "task-1",
                "content": "Task without status",
                "priority": "medium",
                # Missing status field
            }
        ]
        result = has_unfinished_todos(todos)
        assert result is True  # Should treat missing status as pending

    def test_unknown_status(self):
        """Test todos with unknown status."""
        todos = [
            {
                "id": "task-1",
                "content": "Task with unknown status",
                "status": "unknown_status",
                "priority": "medium",
            }
        ]
        result = has_unfinished_todos(todos)
        assert result is False  # Unknown status is not considered unfinished


class TestGetProjectTodoReminder:
    """Test the get_project_todo_reminder function."""

    def setup_method(self):
        """Clear TodoStorage before each test."""
        TodoStorage._sessions.clear()

    def teardown_method(self):
        """Clear TodoStorage after each test."""
        TodoStorage._sessions.clear()

    def test_empty_todos_returns_empty_reminder(self):
        """Test that empty todos return the empty reminder."""
        session_id = "test-session-empty"
        TodoStorage.set_todos(session_id, [])

        result = get_project_todo_reminder(session_id)
        assert result == PROJECT_TODO_EMPTY_REMINDER

    def test_nonexistent_session_returns_empty_reminder(self):
        """Test that nonexistent session returns the empty reminder."""
        result = get_project_todo_reminder("nonexistent-session")
        assert result == PROJECT_TODO_EMPTY_REMINDER

    def test_all_completed_todos_returns_empty_reminder(self):
        """Test that all completed todos return the empty reminder."""
        session_id = "test-session-completed"
        todos = [
            {
                "id": "task-1",
                "content": "Completed task 1",
                "status": "completed",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "Completed task 2",
                "status": "completed",
                "priority": "medium",
            },
        ]
        TodoStorage.set_todos(session_id, todos)

        result = get_project_todo_reminder(session_id)
        assert result == PROJECT_TODO_EMPTY_REMINDER

    def test_unfinished_todos_returns_full_reminder(self):
        """Test that unfinished todos return the full reminder."""
        session_id = "test-session-unfinished"
        todos = [
            {
                "id": "task-1",
                "content": "Completed task",
                "status": "completed",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "Pending task",
                "status": "pending",
                "priority": "medium",
            },
        ]
        TodoStorage.set_todos(session_id, todos)

        result = get_project_todo_reminder(session_id)

        # Should contain the full reminder structure
        assert "<system-reminder>" in result
        assert "The to-do list session ID is: test-session-unfinished" in result
        assert "[ ] 🟡 Pending task (id: task-2)" in result
        assert "[✓] 🔴 Completed task (id: task-1)" in result

    def test_only_pending_todos_returns_full_reminder(self):
        """Test that only pending todos return the full reminder."""
        session_id = "test-session-pending"
        todos = [
            {
                "id": "task-1",
                "content": "Pending task 1",
                "status": "pending",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "Pending task 2",
                "status": "pending",
                "priority": "low",
            },
        ]
        TodoStorage.set_todos(session_id, todos)

        result = get_project_todo_reminder(session_id)

        assert "test-session-pending" in result
        assert "[ ] 🔴 Pending task 1 (id: task-1)" in result
        assert "[ ] 🟢 Pending task 2 (id: task-2)" in result

    def test_only_in_progress_todos_returns_full_reminder(self):
        """Test that only in-progress todos return the full reminder."""
        session_id = "test-session-in-progress"
        todos = [
            {
                "id": "task-1",
                "content": "In progress task",
                "status": "in_progress",
                "priority": "medium",
            },
        ]
        TodoStorage.set_todos(session_id, todos)

        result = get_project_todo_reminder(session_id)

        assert "test-session-in-progress" in result
        assert "[~] 🟡 In progress task (id: task-1)" in result

    def test_complex_mixed_todos_returns_full_reminder(self):
        """Test complex scenario with mixed todo statuses."""
        session_id = "test-session-complex"
        todos = [
            {
                "id": "auth-impl",
                "content": "Implement user authentication system",
                "status": "in_progress",
                "priority": "high",
            },
            {
                "id": "write-tests",
                "content": "Write unit tests for login functionality",
                "status": "pending",
                "priority": "medium",
            },
            {
                "id": "update-docs",
                "content": "Update API documentation",
                "status": "pending",
                "priority": "low",
            },
            {
                "id": "setup-db",
                "content": "Set up production database",
                "status": "completed",
                "priority": "high",
            },
        ]
        TodoStorage.set_todos(session_id, todos)

        result = get_project_todo_reminder(session_id)

        # Should contain session ID
        assert "test-session-complex" in result

        # Should contain all todos in formatted form
        assert "[~] 🔴 Implement user authentication system (id: auth-impl)" in result
        assert (
            "[ ] 🟡 Write unit tests for login functionality (id: write-tests)"
            in result
        )
        assert "[ ] 🟢 Update API documentation (id: update-docs)" in result
        assert "[✓] 🔴 Set up production database (id: setup-db)" in result

        # Should contain the reminder structure
        assert "<system-reminder>" in result
        assert "You can use the todo_write tool" in result

    def test_reminder_format_matches_template(self):
        """Test that the returned reminder matches the expected template format."""
        session_id = "test-format"
        todos = [
            {
                "id": "task-1",
                "content": "Test task",
                "status": "pending",
                "priority": "medium",
            }
        ]
        TodoStorage.set_todos(session_id, todos)

        result = get_project_todo_reminder(session_id)

        # Should start and end with system-reminder tags
        assert result.startswith("<system-reminder>")
        assert result.endswith("</system-reminder>")

        # Should contain expected template elements
        assert f"The to-do list session ID is: {session_id}" in result
        assert "You can use the todo_write tool" in result
        assert "so you do not need to read it using the todo_read tool" in result

    def test_session_isolation(self):
        """Test that different sessions return different reminders."""
        session1 = "session-1"
        session2 = "session-2"

        # Set up different todos for each session
        todos1 = [
            {
                "id": "task-1",
                "content": "Task for session 1",
                "status": "pending",
                "priority": "high",
            }
        ]
        todos2 = [
            {
                "id": "task-2",
                "content": "Task for session 2",
                "status": "completed",
                "priority": "medium",
            }
        ]

        TodoStorage.set_todos(session1, todos1)
        TodoStorage.set_todos(session2, todos2)

        result1 = get_project_todo_reminder(session1)
        result2 = get_project_todo_reminder(session2)

        # Session 1 should have unfinished todos (full reminder)
        assert "session-1" in result1
        assert "Task for session 1" in result1
        assert "pending" not in result1  # Status should be shown as [ ]

        # Session 2 should have all completed todos (empty reminder)
        assert result2 == PROJECT_TODO_EMPTY_REMINDER
        assert "session-2" not in result2
        assert "Task for session 2" not in result2

    def test_edge_case_empty_session_id(self):
        """Test behavior with empty session ID."""
        result = get_project_todo_reminder("")
        assert result == PROJECT_TODO_EMPTY_REMINDER
