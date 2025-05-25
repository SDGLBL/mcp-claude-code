"""Tests for new continue_latest_todo functionality."""

import time

from mcp_claude_code.prompts.project_todo_reminder import (
    PROJECT_TODO_EMPTY_REMINDER,
    get_project_todo_reminder,
)
from mcp_claude_code.tools.todo.base import TodoStorage


class TestGetProjectTodoReminderWithNoneSessionId:
    """Test the get_project_todo_reminder function with None session_id."""

    def setup_method(self):
        """Clear TodoStorage before each test."""
        TodoStorage._sessions.clear()

    def teardown_method(self):
        """Clear TodoStorage after each test."""
        TodoStorage._sessions.clear()

    def test_none_session_id_no_active_sessions(self):
        """Test behavior with None session_id when no active sessions exist."""
        result = get_project_todo_reminder(None)
        assert result == PROJECT_TODO_EMPTY_REMINDER

    def test_none_session_id_with_active_session(self):
        """Test behavior with None session_id when an active session exists."""
        session_id = "test-session-active"
        todos = [
            {
                "id": "task-1",
                "content": "Active task",
                "status": "pending",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session_id, todos)

        result = get_project_todo_reminder(None)

        # Should find the active session and return full reminder
        assert "test-session-active" in result
        assert "[ ] 🔴 Active task (id: task-1)" in result
        assert "<system-reminder>" in result

    def test_none_session_id_multiple_active_sessions(self):
        """Test behavior with None session_id when multiple active sessions exist."""
        # Set up multiple sessions with unfinished todos
        session1 = "session-1"
        todos1 = [
            {
                "id": "task-1",
                "content": "Task from session 1",
                "status": "pending",
                "priority": "high",
            }
        ]

        session2 = "session-2"
        todos2 = [
            {
                "id": "task-2",
                "content": "Task from session 2",
                "status": "in_progress",
                "priority": "medium",
            }
        ]

        TodoStorage.set_todos(session1, todos1)
        TodoStorage.set_todos(session2, todos2)

        result = get_project_todo_reminder(None)

        # Should return a reminder for one of the active sessions
        # (Implementation returns the first one found)
        assert "<system-reminder>" in result
        # Should contain one of the sessions
        has_session1 = "session-1" in result and "Task from session 1" in result
        has_session2 = "session-2" in result and "Task from session 2" in result
        assert has_session1 or has_session2

    def test_none_session_id_only_completed_sessions(self):
        """Test behavior with None session_id when only completed sessions exist."""
        session_id = "test-session-completed"
        todos = [
            {
                "id": "task-1",
                "content": "Completed task",
                "status": "completed",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session_id, todos)

        result = get_project_todo_reminder(None)
        assert result == PROJECT_TODO_EMPTY_REMINDER


class TestTodoStorageFindLatestActiveSession:
    """Test the TodoStorage.find_latest_active_session method."""

    def setup_method(self):
        """Clear TodoStorage before each test."""
        TodoStorage._sessions.clear()

    def teardown_method(self):
        """Clear TodoStorage after each test."""
        TodoStorage._sessions.clear()

    def test_no_sessions(self):
        """Test when no sessions exist."""
        result = TodoStorage.find_latest_active_session()
        assert result is None

    def test_no_active_sessions(self):
        """Test when sessions exist but none have unfinished todos."""
        session_id = "session-completed"
        todos = [
            {
                "id": "task-1",
                "content": "Completed task",
                "status": "completed",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session_id, todos)

        result = TodoStorage.find_latest_active_session()
        assert result is None

    def test_single_active_session(self):
        """Test when one session has unfinished todos."""
        session_id = "session-active"
        todos = [
            {
                "id": "task-1",
                "content": "Active task",
                "status": "pending",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session_id, todos)

        result = TodoStorage.find_latest_active_session()
        assert result == session_id

    def test_multiple_active_sessions(self):
        """Test when multiple sessions have unfinished todos."""
        # Set up first session with unfinished todos
        session1 = "session-1"
        todos1 = [
            {
                "id": "task-1",
                "content": "Pending task",
                "status": "pending",
                "priority": "high",
            }
        ]

        # Set up second session with unfinished todos
        session2 = "session-2"
        todos2 = [
            {
                "id": "task-2",
                "content": "In progress task",
                "status": "in_progress",
                "priority": "medium",
            }
        ]

        TodoStorage.set_todos(session1, todos1)
        TodoStorage.set_todos(session2, todos2)

        result = TodoStorage.find_latest_active_session()

        # Should return one of the active sessions
        assert result in [session1, session2]

    def test_mixed_sessions(self):
        """Test when some sessions have unfinished todos and others don't."""
        # Session with completed todos
        completed_session = "session-completed"
        completed_todos = [
            {
                "id": "task-completed",
                "content": "Completed task",
                "status": "completed",
                "priority": "high",
            }
        ]

        # Session with unfinished todos
        active_session = "session-active"
        active_todos = [
            {
                "id": "task-active",
                "content": "Active task",
                "status": "pending",
                "priority": "medium",
            }
        ]

        # Session with empty todos
        empty_session = "session-empty"
        empty_todos = []

        TodoStorage.set_todos(completed_session, completed_todos)
        TodoStorage.set_todos(active_session, active_todos)
        TodoStorage.set_todos(empty_session, empty_todos)

        result = TodoStorage.find_latest_active_session()
        assert result == active_session

    def test_in_progress_todos_are_active(self):
        """Test that in_progress todos are considered active."""
        session_id = "session-in-progress"
        todos = [
            {
                "id": "task-1",
                "content": "In progress task",
                "status": "in_progress",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session_id, todos)

        result = TodoStorage.find_latest_active_session()
        assert result == session_id

    def test_pending_todos_are_active(self):
        """Test that pending todos are considered active."""
        session_id = "session-pending"
        todos = [
            {
                "id": "task-1",
                "content": "Pending task",
                "status": "pending",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session_id, todos)

        result = TodoStorage.find_latest_active_session()
        assert result == session_id

    def test_chronological_ordering_latest_session(self):
        """Test that find_latest_active_session returns the chronologically latest session."""
        # Create first session
        session1 = "session-older"
        todos1 = [
            {
                "id": "task-1",
                "content": "Older pending task",
                "status": "pending",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session1, todos1)

        # Wait a bit to ensure different timestamps
        time.sleep(0.01)

        # Create second session (should be latest)
        session2 = "session-newer"
        todos2 = [
            {
                "id": "task-2",
                "content": "Newer pending task",
                "status": "pending",
                "priority": "medium",
            }
        ]
        TodoStorage.set_todos(session2, todos2)

        result = TodoStorage.find_latest_active_session()
        assert result == session2  # Should return the newer session

    def test_chronological_ordering_with_updates(self):
        """Test that updating a session makes it the latest."""
        # Create first session
        session1 = "session-1"
        todos1 = [
            {
                "id": "task-1",
                "content": "First task",
                "status": "pending",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(session1, todos1)

        # Wait a bit
        time.sleep(0.01)

        # Create second session
        session2 = "session-2"
        todos2 = [
            {
                "id": "task-2",
                "content": "Second task",
                "status": "pending",
                "priority": "medium",
            }
        ]
        TodoStorage.set_todos(session2, todos2)

        # Verify session2 is latest
        assert TodoStorage.find_latest_active_session() == session2

        # Wait a bit, then update session1
        time.sleep(0.01)
        updated_todos1 = [
            {
                "id": "task-1",
                "content": "Updated first task",
                "status": "pending",
                "priority": "high",
            },
            {
                "id": "task-3",
                "content": "New task in old session",
                "status": "pending",
                "priority": "low",
            },
        ]
        TodoStorage.set_todos(session1, updated_todos1)

        # Now session1 should be latest due to the update
        result = TodoStorage.find_latest_active_session()
        assert result == session1

    def test_timestamp_tracking(self):
        """Test that timestamps are properly tracked."""
        session_id = "session-timestamp-test"
        start_time = time.time()

        todos = [
            {
                "id": "task-1",
                "content": "Test task",
                "status": "pending",
                "priority": "medium",
            }
        ]
        TodoStorage.set_todos(session_id, todos)

        end_time = time.time()

        # Check that timestamp was recorded
        timestamp = TodoStorage.get_session_last_updated(session_id)
        assert timestamp is not None
        assert start_time <= timestamp <= end_time

    def test_get_session_last_updated_nonexistent(self):
        """Test getting timestamp for nonexistent session."""
        result = TodoStorage.get_session_last_updated("nonexistent-session")
        assert result is None

    def test_chronological_ordering_ignores_completed_sessions(self):
        """Test that completed sessions are ignored even if they're newer."""
        # Create session with active todos
        active_session = "session-active"
        active_todos = [
            {
                "id": "task-active",
                "content": "Active task",
                "status": "pending",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(active_session, active_todos)

        # Wait a bit
        time.sleep(0.01)

        # Create newer session but with completed todos
        completed_session = "session-completed"
        completed_todos = [
            {
                "id": "task-completed",
                "content": "Completed task",
                "status": "completed",
                "priority": "high",
            }
        ]
        TodoStorage.set_todos(completed_session, completed_todos)

        # Should still return the active session, not the newer completed one
        result = TodoStorage.find_latest_active_session()
        assert result == active_session
