"""Tests for session-based run_command implementation.

This module tests the new session-based functionality of the run_command tool,
including session persistence, state management, backward compatibility, and error handling.
"""

import os
import shutil
import tempfile
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from mcp_claude_code.tools.common.permissions import PermissionManager

from mcp_claude_code.tools.shell.bash_session import BashSession
from mcp_claude_code.tools.shell.command_executor import CommandExecutor
from mcp_claude_code.tools.shell.run_command import RunCommandTool
from mcp_claude_code.tools.shell.session_manager import SessionManager
from mcp_claude_code.tools.shell.session_storage import SessionStorage


class TestBashSessionBasics:
    """Test basic BashSession functionality."""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_bash_session_initialization(self, temp_work_dir):
        """Test BashSession initialization."""
        session = BashSession(
            work_dir=temp_work_dir,
            username="testuser",
            no_change_timeout_seconds=30,
            max_memory_mb=512,
        )

        assert session.work_dir == temp_work_dir
        assert session.username == "testuser"
        assert session.NO_CHANGE_TIMEOUT_SECONDS == 30
        assert session.max_memory_mb == 512
        assert not session._initialized
        assert not session._closed

        session.close()

    def test_bash_session_execute_simple_command(self, temp_work_dir):
        """Test executing a simple command in bash session."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session = BashSession(
            work_dir=temp_work_dir,
            no_change_timeout_seconds=5,  # Short timeout for testing
        )

        try:
            # Test echo command
            result = session.execute("echo 'Hello, World!'")

            assert result.is_success
            assert "Hello, World!" in result.stdout
            assert result.stderr == ""
        finally:
            session.close()

    def test_session_manager_singleton(self):
        """Test that SessionManager follows singleton pattern."""
        manager1 = SessionManager()
        manager2 = SessionManager()
        assert manager1 is manager2


class TestSessionPersistenceAndState:
    """Test session persistence and state management."""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def setup_method(self):
        """Clear sessions before each test."""
        SessionStorage.clear_all_sessions()

    def teardown_method(self):
        """Clear sessions after each test."""
        SessionStorage.clear_all_sessions()

    def test_bash_session_environment_persistence(self, temp_work_dir):
        """Test that environment variables persist across commands."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session = BashSession(work_dir=temp_work_dir, no_change_timeout_seconds=5)

        try:
            # Set an environment variable
            result = session.execute("export TEST_VAR='session_test_value'")
            assert result.is_success

            # Check that the variable persists
            result = session.execute("echo $TEST_VAR")
            assert result.is_success
            assert "session_test_value" in result.stdout
        finally:
            session.close()

    def test_bash_session_working_directory_persistence(self, temp_work_dir):
        """Test that working directory changes persist."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session = BashSession(work_dir=temp_work_dir, no_change_timeout_seconds=5)

        try:
            # Create a subdirectory
            subdir = os.path.join(temp_work_dir, "subdir")
            os.makedirs(subdir, exist_ok=True)

            # Change to subdirectory
            result = session.execute(f"cd {subdir}")
            assert result.is_success

            # Check current directory
            result = session.execute("pwd")
            assert result.is_success
            assert "subdir" in result.stdout
        finally:
            session.close()

    def test_session_storage_basic_operations(self, temp_work_dir):
        """Test basic session storage operations."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session = BashSession(work_dir=temp_work_dir)
        session_id = "test_session_1"

        try:
            # Store session
            SessionStorage.set_session(session_id, session)
            assert SessionStorage.get_session_count() == 1

            # Retrieve session
            retrieved = SessionStorage.get_session(session_id)
            assert retrieved is session

            # Check session IDs
            session_ids = SessionStorage.get_all_session_ids()
            assert session_id in session_ids

            # Remove session
            removed = SessionStorage.remove_session(session_id)
            assert removed is True
            assert SessionStorage.get_session_count() == 0
        finally:
            session.close()

    def test_session_storage_nonexistent_session(self):
        """Test retrieving nonexistent session."""
        result = SessionStorage.get_session("nonexistent")
        assert result is None

        removed = SessionStorage.remove_session("nonexistent")
        assert removed is False

    def test_session_manager_validate_session_id(self):
        """Test session ID validation."""
        session_manager = SessionManager()

        # Valid session IDs
        valid, msg = session_manager.validate_session_id("test_session_123")
        assert valid is True
        assert msg == ""

        valid, msg = session_manager.validate_session_id("test-session-456")
        assert valid is True
        assert msg == ""

        # Invalid session IDs
        valid, msg = session_manager.validate_session_id("")
        assert valid is False
        assert "cannot be empty" in msg

        valid, msg = session_manager.validate_session_id("test session with spaces")
        assert valid is False
        assert "alphanumeric characters" in msg

        valid, msg = session_manager.validate_session_id("a" * 101)  # Too long
        assert valid is False
        assert "too long" in msg


class TestBackwardCompatibility:
    """Test backward compatibility with subprocess mode."""

    @pytest.fixture
    def run_command_tool(
        self, permission_manager: "PermissionManager", command_executor: CommandExecutor
    ):
        """Create a RunCommandTool instance for testing."""
        return RunCommandTool(permission_manager, command_executor)

    @pytest.fixture
    def mcp_context(self):
        """Mock MCP context for testing."""
        mock_context = MagicMock()
        mock_context.info = AsyncMock()
        mock_context.error = AsyncMock()
        mock_context.warning = AsyncMock()
        mock_context.debug = AsyncMock()
        mock_context.report_progress = AsyncMock()
        mock_context.request_id = "test-request-id"
        mock_context.client_id = "test-client-id"
        return mock_context

    def setup_method(self):
        """Clear sessions before each test."""
        SessionStorage.clear_all_sessions()

    def teardown_method(self):
        """Clear sessions after each test."""
        SessionStorage.clear_all_sessions()

    @pytest.mark.asyncio
    async def test_run_command_subprocess_mode(
        self, run_command_tool, mcp_context, temp_dir
    ):
        """Test run_command in subprocess mode (backward compatibility)."""
        # Execute without session_id (should use subprocess mode)
        result = await run_command_tool.call(
            mcp_context,
            command="echo 'subprocess mode'",
            cwd=temp_dir,
            shell_type=None,
            use_login_shell=True,
            session_id=None,  # No session ID = subprocess mode
            session_timeout=30,
            blocking=False,
        )

        assert "subprocess mode" in result
        assert "Error:" not in result

    @pytest.mark.asyncio
    async def test_run_command_session_mode_fallback(
        self, run_command_tool, mcp_context, temp_dir
    ):
        """Test run_command falls back to subprocess mode when tmux is unavailable."""
        with patch("shutil.which", return_value=None):  # Mock tmux as unavailable
            session_id = "test_session_fallback"

            # Execute with session_id but tmux unavailable (should fallback to subprocess)
            result = await run_command_tool.call(
                mcp_context,
                command="echo 'fallback mode'",
                cwd=temp_dir,
                shell_type=None,
                use_login_shell=True,
                session_id=session_id,
                session_timeout=30,
                blocking=False,
            )

            assert "fallback mode" in result
            assert "Error:" not in result

            # Verify warning was logged about fallback
            mcp_context.warning.assert_called()
            warning_call_args = mcp_context.warning.call_args[0][0]
            assert "falling back to subprocess mode" in warning_call_args

    @pytest.mark.asyncio
    async def test_subprocess_mode_isolation(
        self, run_command_tool, mcp_context, temp_dir
    ):
        """Test that subprocess mode doesn't share state between commands."""
        # Set environment variable in subprocess mode
        result1 = await run_command_tool.call(
            mcp_context,
            command="export SUBPROCESS_VAR='test_value'",
            cwd=temp_dir,
            session_id=None,  # Subprocess mode
            session_timeout=30,
            blocking=False,
            shell_type=None,
            use_login_shell=True,
        )
        assert "Error:" not in result1

        # Try to access it in another command (should fail in subprocess mode)
        result2 = await run_command_tool.call(
            mcp_context,
            command="echo $SUBPROCESS_VAR",
            cwd=temp_dir,
            session_id=None,  # Subprocess mode
            session_timeout=30,
            blocking=False,
            shell_type=None,
            use_login_shell=True,
        )
        # In subprocess mode, environment variable should not persist
        assert "test_value" not in result2

    @pytest.mark.asyncio
    async def test_session_vs_subprocess_behavior_difference(
        self, run_command_tool, mcp_context, temp_dir
    ):
        """Test the behavior difference between session and subprocess modes."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        # Test subprocess mode (no persistence)
        await run_command_tool.call(
            mcp_context,
            command="export TEST_MODE='subprocess'",
            cwd=temp_dir,
            session_id=None,
            session_timeout=30,
            blocking=False,
            shell_type=None,
            use_login_shell=True,
        )

        result_subprocess = await run_command_tool.call(
            mcp_context,
            command="echo $TEST_MODE",
            cwd=temp_dir,
            session_id=None,
            session_timeout=30,
            blocking=False,
            shell_type=None,
            use_login_shell=True,
        )

        # Test session mode (with persistence)
        session_id = "persistence_test"
        await run_command_tool.call(
            mcp_context,
            command="export TEST_MODE='session'",
            cwd=temp_dir,
            session_id=session_id,
            session_timeout=30,
            blocking=False,
            shell_type=None,
            use_login_shell=True,
        )

        result_session = await run_command_tool.call(
            mcp_context,
            command="echo $TEST_MODE",
            cwd=temp_dir,
            session_id=session_id,
            session_timeout=30,
            blocking=False,
            shell_type=None,
            use_login_shell=True,
        )

        # Subprocess mode should not persist environment
        assert "subprocess" not in result_subprocess
        # Session mode should persist environment
        assert "session" in result_session

    @pytest.mark.asyncio
    async def test_existing_code_compatibility(
        self, run_command_tool, mcp_context, temp_dir
    ):
        """Test that existing code using run_command still works unchanged."""
        # This simulates how the tool was called before session support
        result = await run_command_tool.call(
            mcp_context,
            command="echo 'existing functionality'",
            cwd=temp_dir,
            shell_type="bash",
            use_login_shell=True,
            session_id=None,  # This is the key - None means old behavior
            session_timeout=30,  # New parameter with default
            blocking=False,  # New parameter with default
        )

        assert "existing functionality" in result
        assert "Error:" not in result


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    @pytest.fixture
    def run_command_tool(
        self, permission_manager: "PermissionManager", command_executor: CommandExecutor
    ):
        """Create a RunCommandTool instance for testing."""
        return RunCommandTool(permission_manager, command_executor)

    @pytest.fixture
    def mcp_context(self):
        """Mock MCP context for testing."""
        mock_context = MagicMock()
        mock_context.info = AsyncMock()
        mock_context.error = AsyncMock()
        mock_context.warning = AsyncMock()
        mock_context.debug = AsyncMock()
        return mock_context

    def setup_method(self):
        """Clear sessions before each test."""
        SessionStorage.clear_all_sessions()

    def teardown_method(self):
        """Clear sessions after each test."""
        SessionStorage.clear_all_sessions()

    @pytest.mark.asyncio
    async def test_run_command_invalid_session_id(
        self, run_command_tool, mcp_context, temp_dir
    ):
        """Test error handling for invalid session IDs."""
        # Test with invalid session ID
        result = await run_command_tool.call(
            mcp_context,
            command="echo 'test'",
            cwd=temp_dir,
            shell_type=None,
            use_login_shell=True,
            session_id="invalid session id with spaces",  # Invalid characters
            session_timeout=30,
            blocking=False,
        )

        assert "Error: Invalid session_id" in result
        assert "alphanumeric characters" in result

    @pytest.mark.asyncio
    async def test_run_command_invalid_working_directory(
        self, run_command_tool, mcp_context
    ):
        """Test error handling for invalid working directory."""
        result = await run_command_tool.call(
            mcp_context,
            command="echo 'test'",
            cwd="/nonexistent/directory",
            shell_type=None,
            use_login_shell=True,
            session_id=None,
            session_timeout=30,
            blocking=False,
        )

        # The error could be either "not allowed" or "does not exist" depending on permissions check order
        assert "Error:" in result
        assert (
            "Working directory not allowed" in result
            or "Working directory does not exist" in result
        )

    @pytest.mark.asyncio
    async def test_run_command_disallowed_command(
        self, run_command_tool, mcp_context, temp_dir
    ):
        """Test error handling for disallowed commands."""
        result = await run_command_tool.call(
            mcp_context,
            command="rm -rf /",  # This should be disallowed
            cwd=temp_dir,
            shell_type=None,
            use_login_shell=True,
            session_id=None,
            session_timeout=30,
            blocking=False,
        )

        assert "Error: Command not allowed" in result

    def test_bash_session_with_invalid_work_dir(self):
        """Test BashSession with invalid working directory."""
        # This should not fail during initialization, but during execution
        session = BashSession(work_dir="/nonexistent/path")
        assert session.work_dir == "/nonexistent/path"
        session.close()

    def test_session_storage_with_invalid_session_object(self):
        """Test SessionStorage with invalid session object."""
        # Store a non-session object
        SessionStorage.set_session("invalid", "not_a_session")

        # Should still be retrievable (storage doesn't validate types)
        result = SessionStorage.get_session("invalid")
        assert result == "not_a_session"

        # Cleanup should handle invalid objects gracefully
        removed = SessionStorage.remove_session("invalid")
        assert removed is True


class TestSessionTimeoutAndCleanup:
    """Test session timeout and cleanup functionality."""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def setup_method(self):
        """Clear sessions before each test."""
        SessionStorage.clear_all_sessions()

    def teardown_method(self):
        """Clear sessions after each test."""
        SessionStorage.clear_all_sessions()

    def test_session_storage_cleanup_expired(self, temp_work_dir):
        """Test cleanup of expired sessions."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session1 = BashSession(work_dir=temp_work_dir)
        session2 = BashSession(work_dir=temp_work_dir)

        try:
            SessionStorage.set_session("session1", session1)
            SessionStorage.set_session("session2", session2)

            # Mock older access time for session1
            SessionStorage._last_access["session1"] = time.time() - 3600  # 1 hour ago

            # Cleanup expired sessions (max age 1800 seconds = 30 minutes)
            cleaned = SessionStorage.cleanup_expired_sessions(1800)

            assert cleaned == 1
            assert SessionStorage.get_session("session1") is None
            assert SessionStorage.get_session("session2") is not None
        finally:
            session1.close()
            session2.close()

    def test_session_manager_cleanup_operations(self, temp_work_dir):
        """Test session manager cleanup operations."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session_manager = SessionManager()

        # Create some sessions
        session1 = session_manager.get_or_create_session("session1", temp_work_dir)
        session2 = session_manager.get_or_create_session("session2", temp_work_dir)

        assert session_manager.get_session_count() == 2

        # Remove one session
        removed = session_manager.remove_session("session1")
        assert removed is True
        assert session_manager.get_session_count() == 1

        # Clear all sessions
        cleared = session_manager.clear_all_sessions()
        assert cleared == 1
        assert session_manager.get_session_count() == 0

    def test_bash_session_cleanup(self, temp_work_dir):
        """Test session cleanup on close."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session = BashSession(work_dir=temp_work_dir)
        session.initialize()

        # Session should be initialized
        assert session._initialized
        assert session.session is not None

        # Close the session
        session.close()
        assert session._closed

    @pytest.mark.skip(reason="Timeout testing can be flaky in CI environments")
    def test_bash_session_command_timeout(self, temp_work_dir):
        """Test command timeout functionality."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session = BashSession(work_dir=temp_work_dir, no_change_timeout_seconds=2)

        try:
            # Execute a command that should timeout
            result = session.execute("sleep 10", blocking=False)

            # Should timeout within the configured timeout period
            assert not result.is_success
            assert "timed out" in result.error_message
        finally:
            session.close()

    def test_session_automatic_cleanup_on_del(self, temp_work_dir):
        """Test that sessions are cleaned up when objects are deleted."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        # Create session in a scope that will be deleted
        def create_session():
            session = BashSession(work_dir=temp_work_dir)
            session.initialize()
            return session

        session = create_session()
        assert session._initialized

        # Delete the session object
        del session

        # Python's garbage collector should have called __del__
        # This is more of a smoke test since GC timing is not guaranteed
        import gc

        gc.collect()  # Force garbage collection
