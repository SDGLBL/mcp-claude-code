"""Tests for TodoStorage class."""

from mcp_claude_code.tools.todo.base import TodoStorage


class TestTodoStorage:
    """Test the TodoStorage class."""

    def setup_method(self):
        """Clear storage before each test."""
        TodoStorage._sessions.clear()

    def teardown_method(self):
        """Clear storage after each test."""
        TodoStorage._sessions.clear()

    def test_initial_state(self):
        """Test initial state of TodoStorage."""
        assert TodoStorage.get_session_count() == 0
        assert TodoStorage.get_all_session_ids() == []
        assert TodoStorage.get_todos("nonexistent") == []

    def test_set_and_get_todos(self):
        """Test setting and getting todos."""
        session_id = "test-session-123"
        todos = [
            {
                "id": "task-1",
                "content": "Test task",
                "status": "pending",
                "priority": "high",
            }
        ]

        # Set todos
        TodoStorage.set_todos(session_id, todos)

        # Verify storage
        assert TodoStorage.get_session_count() == 1
        assert session_id in TodoStorage.get_all_session_ids()

        # Get todos
        retrieved = TodoStorage.get_todos(session_id)
        assert retrieved == todos
        assert len(retrieved) == 1
        assert retrieved[0]["id"] == "task-1"

    def test_multiple_sessions(self):
        """Test managing multiple sessions."""
        session1 = "session-1"
        session2 = "session-2"

        todos1 = [
            {
                "id": "task-1",
                "content": "Task 1",
                "status": "pending",
                "priority": "high",
            }
        ]
        todos2 = [
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
        ]

        # Set todos for both sessions
        TodoStorage.set_todos(session1, todos1)
        TodoStorage.set_todos(session2, todos2)

        # Verify session count
        assert TodoStorage.get_session_count() == 2

        # Verify session IDs
        session_ids = TodoStorage.get_all_session_ids()
        assert session1 in session_ids
        assert session2 in session_ids

        # Verify session separation
        assert TodoStorage.get_todos(session1) == todos1
        assert TodoStorage.get_todos(session2) == todos2
        assert len(TodoStorage.get_todos(session1)) == 1
        assert len(TodoStorage.get_todos(session2)) == 2

    def test_update_existing_session(self):
        """Test updating todos for an existing session."""
        session_id = "update-test"

        # Initial todos
        initial_todos = [
            {
                "id": "task-1",
                "content": "Task 1",
                "status": "pending",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session_id, initial_todos)

        # Update todos
        updated_todos = [
            {
                "id": "task-1",
                "content": "Task 1 Updated",
                "status": "completed",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "Task 2",
                "status": "pending",
                "priority": "medium",
            },
        ]
        TodoStorage.set_todos(session_id, updated_todos)

        # Verify update
        assert TodoStorage.get_session_count() == 1  # Still only one session
        retrieved = TodoStorage.get_todos(session_id)
        assert retrieved == updated_todos
        assert len(retrieved) == 2
        assert retrieved[0]["content"] == "Task 1 Updated"
        assert retrieved[0]["status"] == "completed"

    def test_empty_todos_list(self):
        """Test setting empty todos list."""
        session_id = "empty-test"

        # Set empty list
        TodoStorage.set_todos(session_id, [])

        # Verify
        assert TodoStorage.get_session_count() == 1
        assert TodoStorage.get_todos(session_id) == []

    def test_delete_session(self):
        """Test deleting a session."""
        session_id = "delete-test"
        todos = [
            {
                "id": "task-1",
                "content": "Task 1",
                "status": "pending",
                "priority": "high",
            }
        ]

        # Create session
        TodoStorage.set_todos(session_id, todos)
        assert TodoStorage.get_session_count() == 1

        # Delete session
        result = TodoStorage.delete_session(session_id)
        assert result is True  # Should return True when session exists
        assert TodoStorage.get_session_count() == 0
        assert TodoStorage.get_todos(session_id) == []

        # Try to delete non-existent session
        result = TodoStorage.delete_session("nonexistent")
        assert result is False  # Should return False when session doesn't exist

    def test_complex_todo_structure(self):
        """Test storing complex todo structures."""
        session_id = "complex-test"

        # Complex todos with all fields
        todos = [
            {
                "id": "task-1",
                "content": "Implement user authentication with OAuth2 integration",
                "status": "in_progress",
                "priority": "high",
            },
            {
                "id": "task-2",
                "content": "Write comprehensive unit tests for API endpoints",
                "status": "pending",
                "priority": "medium",
            },
            {
                "id": "task-3",
                "content": "Update documentation with new features",
                "status": "completed",
                "priority": "low",
            },
        ]

        TodoStorage.set_todos(session_id, todos)
        retrieved = TodoStorage.get_todos(session_id)

        assert retrieved == todos
        assert len(retrieved) == 3

        # Verify each todo maintains its structure
        for i, todo in enumerate(retrieved):
            assert todo["id"] == todos[i]["id"]
            assert todo["content"] == todos[i]["content"]
            assert todo["status"] == todos[i]["status"]
            assert todo["priority"] == todos[i]["priority"]

    def test_session_isolation(self):
        """Test that sessions are properly isolated."""
        # Create multiple sessions with similar todo IDs
        for i in range(3):
            session_id = f"session-{i}"
            todos = [
                {
                    "id": "task-1",  # Same ID across sessions
                    "content": f"Task for session {i}",
                    "status": "pending",
                    "priority": "high",
                }
            ]
            TodoStorage.set_todos(session_id, todos)

        # Verify isolation
        assert TodoStorage.get_session_count() == 3

        for i in range(3):
            session_id = f"session-{i}"
            todos = TodoStorage.get_todos(session_id)
            assert len(todos) == 1
            assert todos[0]["content"] == f"Task for session {i}"

        # Modify one session
        TodoStorage.set_todos("session-1", [])

        # Verify other sessions are unaffected
        assert len(TodoStorage.get_todos("session-0")) == 1
        assert len(TodoStorage.get_todos("session-1")) == 0
        assert len(TodoStorage.get_todos("session-2")) == 1
