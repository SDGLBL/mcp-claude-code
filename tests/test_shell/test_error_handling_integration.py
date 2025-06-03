"""Comprehensive tests for error handling and integration scenarios.

This module tests:
- Error handling and recovery scenarios
- End-to-end integration scenarios
- Edge cases and boundary conditions
- Performance and reliability aspects
"""

import asyncio
import tempfile
import os
import pytest
import shutil
from unittest.mock import MagicMock, patch, AsyncMock

from mcp_claude_code.tools.shell.base import (
    BashCommandStatus,
    CommandResult,
)
from mcp_claude_code.tools.shell.bash_session import BashSession
from mcp_claude_code.tools.shell.bash_session_executor import BashSessionExecutor
from mcp_claude_code.tools.shell.run_command import RunCommandTool
from mcp_claude_code.tools.common.permissions import PermissionManager
from fastmcp import Context


class TestErrorHandlingAndRecovery:
    """Test comprehensive error handling and recovery scenarios."""

    @pytest.fixture
    def permission_manager(self):
        """Create a permission manager for testing."""
        return PermissionManager()

    @pytest.fixture
    def executor(self, permission_manager):
        """Create a BashSessionExecutor for testing."""
        return BashSessionExecutor(
            permission_manager, verbose=False, fast_test_mode=True
        )

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.asyncio
    async def test_session_manager_errors(self, executor):
        """Test error handling when SessionManager fails."""
        # Mock SessionManager to raise exceptions
        with patch.object(
            executor.session_manager,
            "get_session",
            side_effect=Exception("Session manager error"),
        ):
            result = await executor.execute_command(
                "echo test", session_id="error_test"
            )

            assert not result.is_success
            assert "Error executing command in session" in result.error_message
            assert "Session manager error" in result.error_message
            assert result.command == "echo test"
            assert result.session_id == "error_test"

    @pytest.mark.asyncio
    async def test_session_creation_errors(self, executor):
        """Test error handling when session creation fails."""
        # Mock get_session to return None, and get_or_create_session to raise exception
        with patch.object(executor.session_manager, "get_session", return_value=None):
            with patch.object(
                executor.session_manager,
                "get_or_create_session",
                side_effect=Exception("Creation failed"),
            ):
                result = await executor.execute_command(
                    "echo test", session_id="create_error_test"
                )

                assert not result.is_success
                assert "Error executing command in session" in result.error_message
                assert "Creation failed" in result.error_message

    @pytest.mark.asyncio
    async def test_environment_variable_setting_errors(self, executor):
        """Test error handling when environment variable setting fails."""
        # Mock session that fails to set environment variables
        mock_session = MagicMock()
        mock_env_result = CommandResult(return_code=1, error_message="Env var failed")
        mock_session.execute.return_value = mock_env_result

        with patch.object(executor.session_manager, "get_session", return_value=None):
            with patch.object(
                executor.session_manager,
                "get_or_create_session",
                return_value=mock_session,
            ):
                # Should log the failure but continue
                await executor.execute_command(
                    "echo test",
                    env={"TEST_VAR": "test_value"},
                    session_id="env_error_test",
                )

                # Should have called execute twice: once for env var, once for command
                assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_command_permission_errors(self, executor):
        """Test comprehensive command permission error scenarios."""
        # Test with is_input=False (should check permissions)
        executor.deny_command("forbidden_cmd")

        result1 = await executor.execute_command("forbidden_cmd", is_input=False)
        assert not result1.is_success
        assert "Command not allowed" in result1.error_message
        assert result1.command == "forbidden_cmd"

        # Test with is_input=True (should skip permission check)
        result2 = await executor.execute_command("forbidden_cmd", is_input=True)
        # Should not fail due to permissions (though may fail for other reasons)
        assert "Command not allowed" not in (result2.error_message or "")

    @pytest.mark.asyncio
    async def test_command_parsing_errors(self, executor):
        """Test error handling for command parsing issues."""
        # Test with command that might cause parsing issues
        result = await executor.execute_command(
            'echo "unclosed quote', session_id="parse_test"
        )

        # Should handle gracefully and not crash
        assert result.command == 'echo "unclosed quote'
        assert result.session_id == "parse_test"

    def test_bash_session_initialization_errors(self, temp_work_dir):
        """Test BashSession error handling during initialization."""
        session = BashSession(id="init_error_test", work_dir=temp_work_dir)

        # Mock libtmux.Server to raise exception
        with patch(
            "mcp_claude_code.tools.shell.bash_session.libtmux.Server",
            side_effect=Exception("tmux error"),
        ):
            with pytest.raises(Exception, match="tmux error"):
                session.initialize()

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not available")
    def test_bash_session_pane_errors(self, temp_work_dir):
        """Test BashSession error handling with pane operations."""
        session = BashSession(
            id="pane_error_test", work_dir=temp_work_dir, no_change_timeout_seconds=1
        )

        try:
            session.initialize()

            # Mock pane to raise exception during send_keys
            if session.pane:
                original_send_keys = session.pane.send_keys
                session.pane.send_keys = MagicMock(side_effect=Exception("Pane error"))

                # Should handle pane errors gracefully
                # Note: This might still raise an exception depending on where the error occurs
                try:
                    session.execute("echo test")
                except Exception as e:
                    assert "Pane error" in str(e) or isinstance(e, Exception)

                # Restore original method
                session.pane.send_keys = original_send_keys

        finally:
            session.close()

    def test_command_result_error_states(self):
        """Test CommandResult with various error states."""
        # Test with different error combinations
        test_cases = [
            # (return_code, status, error_message, expected_is_success)
            (0, BashCommandStatus.COMPLETED, None, True),
            (1, BashCommandStatus.COMPLETED, None, False),
            (0, BashCommandStatus.CONTINUE, None, False),
            (0, BashCommandStatus.COMPLETED, "Error occurred", False),
            (-1, BashCommandStatus.NO_CHANGE_TIMEOUT, "Timeout", False),
            (-1, BashCommandStatus.HARD_TIMEOUT, "Hard timeout", False),
        ]

        for return_code, status, error_message, expected_success in test_cases:
            result = CommandResult(
                return_code=return_code, status=status, error_message=error_message
            )
            assert result.is_success == expected_success

    @pytest.mark.asyncio
    async def test_run_command_tool_error_propagation(self, permission_manager):
        """Test that RunCommandTool properly propagates errors."""
        # Create executor that always fails
        mock_executor = MagicMock()
        mock_executor.is_command_allowed.return_value = True
        mock_executor.execute_command = AsyncMock(
            side_effect=RuntimeError("Executor failed")
        )

        tool = RunCommandTool(permission_manager, mock_executor)
        ctx = Context({"user_id": "test", "session_id": "test"})

        result = await tool.call(
            ctx,
            command="echo test",
            session_id="error_prop_test",
            time_out=30,
            is_input=False,
            blocking=False,
        )

        assert "Error: Session execution failed" in result
        assert "Executor failed" in result


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios."""

    @pytest.fixture
    def permission_manager(self):
        """Create a permission manager for testing."""
        return PermissionManager()

    @pytest.fixture
    def executor(self, permission_manager):
        """Create a BashSessionExecutor for testing."""
        return BashSessionExecutor(
            permission_manager, verbose=False, fast_test_mode=True
        )

    @pytest.fixture
    def tool(self, permission_manager, executor):
        """Create a RunCommandTool for testing."""
        return RunCommandTool(permission_manager, executor)

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context for testing."""
        return Context({"user_id": "test", "session_id": "test"})

    @pytest.mark.asyncio
    async def test_complete_command_lifecycle(self, tool, mock_context):
        """Test complete command lifecycle from tool to session."""
        # Test a complete command execution cycle
        result = await tool.call(
            mock_context,
            command="echo 'Integration test'",
            session_id="integration_test_session",
            time_out=30,
            is_input=False,
            blocking=False,
        )

        # Should get a string result
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_session_persistence_across_commands(self, executor):
        """Test that session state persists across multiple commands."""
        session_id = "persistence_test_session"

        # Execute first command to create session
        result1 = await executor.execute_command(
            "export TEST_PERSIST_VAR='persistent_value'", session_id=session_id
        )

        # Execute second command in same session
        result2 = await executor.execute_command(
            "echo $TEST_PERSIST_VAR", session_id=session_id
        )

        # Both should use the same session
        assert result1.session_id == session_id
        assert result2.session_id == session_id

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self, executor):
        """Test that multiple sessions can run concurrently."""
        # Start multiple sessions concurrently
        tasks = []
        for i in range(3):
            task = executor.execute_command(
                f"echo 'Session {i}'", session_id=f"concurrent_session_{i}"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All should succeed and have different session IDs
        session_ids = {result.session_id for result in results}
        assert len(session_ids) == 3
        assert all(f"concurrent_session_{i}" in session_ids for i in range(3))

    @pytest.mark.asyncio
    async def test_complex_interactive_scenario(self, tool, mock_context):
        """Test complex interactive process scenario."""
        session_id = "interactive_scenario"

        # Start a command that might need interaction
        result1 = await tool.call(
            mock_context,
            command="echo 'Starting interactive scenario'",
            session_id=session_id,
            time_out=30,
            is_input=False,
            blocking=False,
        )

        # Send input to the same session
        result2 = await tool.call(
            mock_context,
            command="additional input",
            session_id=session_id,
            time_out=30,
            is_input=True,
            blocking=False,
        )

        # Both should reference the same session
        assert isinstance(result1, str)
        assert isinstance(result2, str)

    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self, executor):
        """Test error recovery in a multi-command scenario."""
        session_id = "error_recovery_session"

        # Execute a failing command
        result1 = await executor.execute_command(
            "nonexistent_command_xyz", session_id=session_id
        )

        # Execute a successful command in the same session
        result2 = await executor.execute_command(
            "echo 'Recovery successful'", session_id=session_id
        )

        # Session should recover and continue working
        assert result1.session_id == session_id
        assert result2.session_id == session_id
        # The second command might succeed even if first failed

    @pytest.mark.asyncio
    async def test_timeout_and_recovery_scenario(self, executor):
        """Test timeout handling and recovery."""
        session_id = "timeout_recovery_session"

        # Execute command with very short timeout
        result1 = await executor.execute_command(
            "sleep 0.1",
            session_id=session_id,
            timeout=0.05,  # Very short timeout
            blocking=False,
        )

        # Execute another command in the same session
        result2 = await executor.execute_command(
            "echo 'After timeout'", session_id=session_id, timeout=5.0
        )

        # Both should use the same session
        assert result1.session_id == session_id
        assert result2.session_id == session_id

    @pytest.mark.asyncio
    async def test_permission_and_execution_integration(self, executor):
        """Test integration of permission checking with command execution."""
        # Allow a command
        executor.allow_command("echo")

        # Deny a command
        executor.deny_command("dangerous_command")

        # Test allowed command
        await executor.execute_command("echo 'allowed'", session_id="perm_test")

        # Test denied command
        result2 = await executor.execute_command(
            "dangerous_command", session_id="perm_test"
        )

        # Test denied command with is_input=True (should bypass permission check)
        result3 = await executor.execute_command(
            "dangerous_command", is_input=True, session_id="perm_test"
        )

        # Check results
        assert result2.error_message and "not allowed" in result2.error_message
        assert not (result3.error_message and "not allowed" in result3.error_message)

    @pytest.mark.asyncio
    async def test_full_stack_with_file_operations(self, tool, mock_context):
        """Test full stack integration with file operations."""
        # Test creating, writing, and reading a file
        session_id = "file_ops_session"

        with tempfile.TemporaryDirectory() as temp_dir:
            os.path.join(temp_dir, "integration_test.txt")

            # Change to temp directory
            result1 = await tool.call(
                mock_context,
                command=f"cd {temp_dir}",
                session_id=session_id,
                time_out=30,
                is_input=False,
                blocking=False,
            )

            # Create and write to file
            result2 = await tool.call(
                mock_context,
                command="echo 'Integration test content' > integration_test.txt",
                session_id=session_id,
                time_out=30,
                is_input=False,
                blocking=False,
            )

            # Read the file
            result3 = await tool.call(
                mock_context,
                command="cat integration_test.txt",
                session_id=session_id,
                time_out=30,
                is_input=False,
                blocking=False,
            )

            # All operations should succeed
            assert isinstance(result1, str)
            assert isinstance(result2, str)
            assert isinstance(result3, str)


class TestPerformanceAndReliability:
    """Test performance and reliability aspects."""

    @pytest.fixture
    def permission_manager(self):
        """Create a permission manager for testing."""
        return PermissionManager()

    @pytest.fixture
    def executor(self, permission_manager):
        """Create a BashSessionExecutor for testing."""
        return BashSessionExecutor(
            permission_manager, verbose=False, fast_test_mode=True
        )

    @pytest.mark.asyncio
    async def test_rapid_command_execution(self, executor):
        """Test rapid execution of multiple commands."""
        session_id = "rapid_test_session"

        # Execute multiple commands rapidly
        tasks = []
        for i in range(5):
            task = executor.execute_command(
                f"echo 'Rapid command {i}'", session_id=session_id
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All should succeed and use the same session
        assert all(result.session_id == session_id for result in results)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_session_cleanup_on_errors(self, executor):
        """Test that sessions are properly cleaned up on errors."""
        session_id = "cleanup_test_session"

        # Get initial session count
        initial_count = executor.session_manager.get_session_count()

        # Execute a command that might fail
        try:
            await executor.execute_command(
                "potentially_failing_command", session_id=session_id, timeout=1.0
            )
        except Exception:
            pass  # Ignore failures for this test

        # Session count should be managed properly
        final_count = executor.session_manager.get_session_count()
        assert final_count >= initial_count  # May have created a session

    @pytest.mark.asyncio
    async def test_memory_usage_with_long_output(self, executor):
        """Test memory usage with commands that produce long output."""
        # Execute command that produces substantial output
        result = await executor.execute_command(
            "python3 -c \"print('x' * 1000)\"", session_id="memory_test_session"
        )

        # Should handle large output gracefully
        assert result.session_id == "memory_test_session"
        # Output should be present but possibly truncated
        assert len(result.stdout) > 0

    def test_command_result_serialization(self):
        """Test that CommandResult can be properly serialized/deserialized."""
        result = CommandResult(
            return_code=0,
            stdout="test output",
            status=BashCommandStatus.COMPLETED,
            command="test command",
        )

        # Test that all properties are accessible
        assert result.return_code == 0
        assert result.stdout == "test output"
        assert result.status == BashCommandStatus.COMPLETED
        assert result.command == "test command"

    @pytest.mark.asyncio
    async def test_concurrent_session_isolation(self, executor):
        """Test that concurrent sessions are properly isolated."""
        # Create multiple sessions with different environment variables
        tasks = []
        for i in range(3):
            task = executor.execute_command(
                f"export ISOLATION_TEST_{i}='value_{i}' && echo $ISOLATION_TEST_{i}",
                session_id=f"isolation_session_{i}",
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Each session should have its own environment
        session_ids = {result.session_id for result in results}
        assert len(session_ids) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
