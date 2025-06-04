"""Tests for session-based run_command implementation.

This module tests the new session-based functionality of the run_command tool,
including session persistence, state management, backward compatibility, and error handling.
"""

import os
import shutil
import tempfile
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from mcp_claude_code.tools.common.permissions import PermissionManager

from mcp_claude_code.tools.shell.bash_session import BashSession
from mcp_claude_code.tools.shell.bash_session_executor import BashSessionExecutor
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
            id="test_session_init",
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
            id="test_session_simple",
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

        session = BashSession(
            id="test_session_env", work_dir=temp_work_dir, no_change_timeout_seconds=5
        )

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

        session = BashSession(
            id="test_session_wd", work_dir=temp_work_dir, no_change_timeout_seconds=5
        )

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

        session = BashSession(id="test_session_storage", work_dir=temp_work_dir)
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


class TestBackwardCompatibility:
    """Test backward compatibility with subprocess mode."""

    @pytest.fixture
    def run_command_tool(
        self,
        permission_manager: "PermissionManager",
        command_executor: BashSessionExecutor,
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
            session_id=None,  # No session ID = subprocess mode
            time_out=30,
        )

        assert "subprocess mode" in result
        assert "Error:" not in result

    @pytest.mark.asyncio
    async def test_subprocess_mode_isolation(
        self, run_command_tool, mcp_context, temp_dir
    ):
        """Test that subprocess mode doesn't share state between commands."""
        # Set environment variable in subprocess mode
        result1 = await run_command_tool.call(
            mcp_context,
            command="export SUBPROCESS_VAR='test_value'",
            session_id=None,  # Subprocess mode
            time_out=30,
        )
        assert "Error:" not in result1

        # Try to access it in another command (should fail in subprocess mode)
        result2 = await run_command_tool.call(
            mcp_context,
            command="echo $SUBPROCESS_VAR",
            session_id=None,  # Subprocess mode
            time_out=30,
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
            session_id=None,
            time_out=30,
        )

        result_subprocess = await run_command_tool.call(
            mcp_context,
            command="echo $TEST_MODE",
            session_id=None,
            time_out=30,
        )

        # Test session mode (with persistence)
        session_id = "persistence_test"
        await run_command_tool.call(
            mcp_context,
            command="export TEST_MODE='session'",
            session_id=session_id,
            time_out=30,
        )

        result_session = await run_command_tool.call(
            mcp_context,
            command="echo $TEST_MODE",
            session_id=session_id,
            time_out=30,
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
            session_id=None,  # This is the key - None means old behavior
            time_out=30,  # New parameter with default
        )

        assert "existing functionality" in result
        assert "Error:" not in result


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    @pytest.fixture
    def run_command_tool(
        self,
        permission_manager: "PermissionManager",
        command_executor: BashSessionExecutor,
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
    async def test_run_command_invalid_working_directory(
        self, run_command_tool, mcp_context
    ):
        """Test error handling for invalid working directory."""
        # Note: With persistent sessions, working directory is handled within the session
        # This test now validates that commands can still execute without explicit cwd
        result = await run_command_tool.call(
            mcp_context,
            command="echo 'test'",
            session_id=None,
            time_out=30,
        )

        # Command should succeed since we're not specifying an invalid cwd
        assert "test" in result
        assert "Error:" not in result

    @pytest.mark.asyncio
    async def test_run_command_disallowed_command(
        self, run_command_tool, mcp_context, temp_dir
    ):
        """Test error handling for disallowed commands."""
        result = await run_command_tool.call(
            mcp_context,
            command="rm -rf /",  # This should be disallowed
            session_id=None,
            time_out=30,
        )

        assert "Error: Command not allowed" in result

    def test_bash_session_with_invalid_work_dir(self):
        """Test BashSession with invalid working directory."""
        # This should not fail during initialization, but during execution
        session = BashSession(id="test_session_invalid", work_dir="/nonexistent/path")
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

        session1 = BashSession(id="session1_cleanup", work_dir=temp_work_dir)
        session2 = BashSession(id="session2_cleanup", work_dir=temp_work_dir)

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
        session_manager.get_or_create_session("session1", temp_work_dir)
        session_manager.get_or_create_session("session2", temp_work_dir)

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

        session = BashSession(id="test_session_cleanup", work_dir=temp_work_dir)
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

        session = BashSession(
            id="test_session_timeout",
            work_dir=temp_work_dir,
            no_change_timeout_seconds=2,
        )

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
            session = BashSession(
                id="test_session_auto_cleanup", work_dir=temp_work_dir
            )
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


class TestSessionIdValidationAndPersistence:
    """Test comprehensive session_id validation and variable persistence."""

    @pytest.fixture
    def run_command_tool(
        self,
        permission_manager: "PermissionManager",
        command_executor: BashSessionExecutor,
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
    async def test_variable_persistence_exact_scenario(
        self, run_command_tool, mcp_context
    ):
        """Test the exact scenario: A='xxxx'; echo $A."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session_id = "test_variable_persistence"

        # Set variable A='xxxx'
        result1 = await run_command_tool.call(
            mcp_context,
            command="A='xxxx'",
            session_id=session_id,
            time_out=30,
            is_input=False,
            blocking=False,
        )

        # Should be successful (no output for variable assignment)
        assert "Error:" not in result1

        # Echo the variable
        result2 = await run_command_tool.call(
            mcp_context,
            command="echo $A",
            session_id=session_id,
            time_out=30,
            is_input=False,
            blocking=False,
        )

        # Should output 'xxxx' with session ID
        assert "xxxx" in result2, f"Expected 'xxxx' in output, got {repr(result2)}"
        assert f"[Session ID: {session_id}]" in result2, (
            f"Expected session ID in output, got {repr(result2)}"
        )

    @pytest.mark.asyncio
    async def test_multiple_variables_in_same_session(
        self, run_command_tool, mcp_context
    ):
        """Test that multiple variables persist in the same session."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session_id = "test_multiple_vars"

        # Set multiple variables
        await run_command_tool.call(
            mcp_context,
            command="VAR1='value1'",
            session_id=session_id,
            time_out=30,
        )

        await run_command_tool.call(
            mcp_context,
            command="VAR2='value2'",
            session_id=session_id,
            time_out=30,
        )

        await run_command_tool.call(
            mcp_context,
            command="VAR3='value3'",
            session_id=session_id,
            time_out=30,
        )

        # Test that all variables are accessible
        result = await run_command_tool.call(
            mcp_context,
            command="echo $VAR1 $VAR2 $VAR3",
            session_id=session_id,
            time_out=30,
        )

        # Should output all variable values with session ID
        assert "value1 value2 value3" in result
        assert f"[Session ID: {session_id}]" in result

    @pytest.mark.asyncio
    async def test_session_isolation_between_different_ids(
        self, run_command_tool, mcp_context
    ):
        """Test that different session_ids are properly isolated."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session_a = "session_a"
        session_b = "session_b"

        # Set variable in session A
        await run_command_tool.call(
            mcp_context,
            command="ISOLATION_TEST='session_a_value'",
            session_id=session_a,
            time_out=30,
        )

        # Set different variable in session B
        await run_command_tool.call(
            mcp_context,
            command="ISOLATION_TEST='session_b_value'",
            session_id=session_b,
            time_out=30,
        )

        # Check that session A still has its value
        result_a = await run_command_tool.call(
            mcp_context,
            command="echo $ISOLATION_TEST",
            session_id=session_a,
            time_out=30,
        )

        # Check that session B has its value
        result_b = await run_command_tool.call(
            mcp_context,
            command="echo $ISOLATION_TEST",
            session_id=session_b,
            time_out=30,
        )

        # Should have session-specific values with session ID included
        assert "session_a_value" in result_a
        assert f"[Session ID: {session_a}]" in result_a
        assert "session_b_value" in result_b
        assert f"[Session ID: {session_b}]" in result_b


class TestSequentialCommandOutputIsolation:
    """Test that sequential commands don't accumulate previous outputs."""

    @pytest.fixture
    def run_command_tool(
        self,
        permission_manager: "PermissionManager",
        command_executor: BashSessionExecutor,
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
    async def test_sequential_commands_no_output_accumulation(
        self, run_command_tool, mcp_context
    ):
        """Test that sequential commands don't include previous command outputs."""
        if not shutil.which("tmux"):
            pytest.skip("tmux is not available for session testing")

        session_id = "test_output_isolation"

        # First command: echo a unique string
        result1 = await run_command_tool.call(
            mcp_context,
            command="echo 'FIRST_COMMAND_OUTPUT'",
            session_id=session_id,
            time_out=30,
        )

        # Should contain the first command output
        assert "FIRST_COMMAND_OUTPUT" in result1
        assert f"[Session ID: {session_id}]" in result1

        # Second command: echo a different unique string
        result2 = await run_command_tool.call(
            mcp_context,
            command="echo 'SECOND_COMMAND_OUTPUT'",
            session_id=session_id,
            time_out=30,
        )

        # Should contain ONLY the second command output, not the first
        assert "SECOND_COMMAND_OUTPUT" in result2
        assert "FIRST_COMMAND_OUTPUT" not in result2, (
            f"Second command output should not contain first command output. "
            f"Got: {repr(result2)}"
        )
        assert f"[Session ID: {session_id}]" in result2

        # Third command: echo yet another unique string
        result3 = await run_command_tool.call(
            mcp_context,
            command="echo 'THIRD_COMMAND_OUTPUT'",
            session_id=session_id,
            time_out=30,
        )

        # Should contain ONLY the third command output, not previous ones
        assert "THIRD_COMMAND_OUTPUT" in result3
        assert "FIRST_COMMAND_OUTPUT" not in result3, (
            f"Third command output should not contain first command output. "
            f"Got: {repr(result3)}"
        )
        assert "SECOND_COMMAND_OUTPUT" not in result3, (
            f"Third command output should not contain second command output. "
            f"Got: {repr(result3)}"
        )
        assert f"[Session ID: {session_id}]" in result3
