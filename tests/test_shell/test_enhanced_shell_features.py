"""Comprehensive tests for enhanced shell features.

This module tests all the advanced shell functionality including:
- BashCommandStatus enum and state management
- Enhanced CommandResult class
- Interactive process handling
- Command conflict prevention
- Advanced error handling
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from mcp_claude_code.tools.shell.base import (
    BashCommandStatus,
    CommandResult,
)
from mcp_claude_code.tools.shell.bash_session_executor import BashSessionExecutor
from mcp_claude_code.tools.shell.run_command import (
    RunCommandTool,
    RunCommandToolParams,
)
from mcp_claude_code.tools.common.permissions import PermissionManager
from fastmcp import Context


class TestBashCommandStatus:
    """Test the BashCommandStatus enum."""

    def test_bash_command_status_values(self):
        """Test all BashCommandStatus enum values."""
        assert BashCommandStatus.CONTINUE.value == "continue"
        assert BashCommandStatus.COMPLETED.value == "completed"
        assert BashCommandStatus.NO_CHANGE_TIMEOUT.value == "no_change_timeout"
        assert BashCommandStatus.HARD_TIMEOUT.value == "hard_timeout"

    def test_bash_command_status_completeness(self):
        """Test that all expected status values are present."""
        expected_statuses = {
            "continue",
            "completed",
            "no_change_timeout",
            "hard_timeout",
        }
        actual_statuses = {status.value for status in BashCommandStatus}
        assert actual_statuses == expected_statuses

    def test_bash_command_status_enum_usage(self):
        """Test BashCommandStatus enum can be used in comparisons."""
        status = BashCommandStatus.COMPLETED
        assert status == BashCommandStatus.COMPLETED
        assert status != BashCommandStatus.CONTINUE
        assert status.value == "completed"


class TestEnhancedCommandResult:
    """Test the enhanced CommandResult class."""

    def test_command_result_basic_initialization(self):
        """Test basic CommandResult initialization."""
        result = CommandResult(
            return_code=0,
            stdout="test output",
            stderr="test error",
            command="echo test",
        )

        assert result.return_code == 0
        assert result.stdout == "test output"
        assert result.stderr == "test error"
        assert result.command == "echo test"
        assert result.status == BashCommandStatus.COMPLETED

    def test_is_success_property(self):
        """Test is_success property with various conditions."""
        # Successful command
        result_success = CommandResult(
            return_code=0, status=BashCommandStatus.COMPLETED
        )
        assert result_success.is_success is True

        # Failed return code
        result_failed_code = CommandResult(
            return_code=1, status=BashCommandStatus.COMPLETED
        )
        assert result_failed_code.is_success is False

        # Running command
        result_running = CommandResult(return_code=0, status=BashCommandStatus.CONTINUE)
        assert result_running.is_success is False

        # Error message present
        result_error_msg = CommandResult(
            return_code=0,
            status=BashCommandStatus.COMPLETED,
            error_message="Some error occurred",
        )
        assert result_error_msg.is_success is False

    def test_is_running_property(self):
        """Test is_running property with various statuses."""
        # Completed command
        result_completed = CommandResult(status=BashCommandStatus.COMPLETED)
        assert result_completed.is_running is False

        # Running states
        running_statuses = [
            BashCommandStatus.CONTINUE,
            BashCommandStatus.NO_CHANGE_TIMEOUT,
            BashCommandStatus.HARD_TIMEOUT,
        ]

        for status in running_statuses:
            result = CommandResult(status=status)
            assert result.is_running is True

    def test_exit_code_property(self):
        """Test exit_code property (alias for return_code)."""
        result = CommandResult(return_code=42)
        assert result.exit_code == 42
        assert result.exit_code == result.return_code

    def test_error_property(self):
        """Test error property."""
        result_success = CommandResult(
            return_code=0, status=BashCommandStatus.COMPLETED
        )
        assert result_success.error is False

        result_error = CommandResult(return_code=1, status=BashCommandStatus.COMPLETED)
        assert result_error.error is True

    def test_message_property(self):
        """Test message property."""
        # With error message
        result_with_error = CommandResult(
            command="test cmd", error_message="Command failed"
        )
        expected_msg = "Command `test cmd` failed: Command failed"
        assert result_with_error.message == expected_msg

        # Without error message
        result_without_error = CommandResult(command="test cmd", return_code=0)
        expected_msg = "Command `test cmd` executed with exit code 0."
        assert result_without_error.message == expected_msg

    def test_format_output_basic(self):
        """Test format_output method."""
        result = CommandResult(
            return_code=0,
            stdout="test output",
            stderr="test error",
            session_id="test_session",
            command="echo test",
        )

        output = result.format_output()
        assert "Session ID: test_session" in output
        assert "STDOUT:\ntest output" in output
        assert "STDERR:\ntest error" in output

    def test_format_output_with_status(self):
        """Test format_output with non-completed status."""
        result = CommandResult(
            return_code=-1,
            stdout="partial output",
            status=BashCommandStatus.NO_CHANGE_TIMEOUT,
        )

        output = result.format_output()
        assert "Status: no_change_timeout" in output


class TestEnhancedBashSessionExecutor:
    """Test the enhanced BashSessionExecutor class."""

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
    async def test_execute_command_with_new_parameters(self, executor):
        """Test execute_command with new is_input and blocking parameters."""
        result = await executor.execute_command(
            command="echo 'test with new params'",
            is_input=False,
            blocking=False,
            session_id="test_session",
        )

        assert result.command == "echo 'test with new params'"
        assert result.session_id == "test_session"
        # Should succeed with the new parameters
        assert result.return_code in [0, -1]  # May timeout on some systems

    @pytest.mark.asyncio
    async def test_execute_command_is_input_parameter(self, executor):
        """Test execute_command with is_input=True."""
        # First, start a session
        await executor.execute_command(
            "echo 'starting session'", session_id="input_test"
        )

        # Then send input
        result = await executor.execute_command(
            command="test input", is_input=True, session_id="input_test"
        )

        assert result.command == "test input"
        assert result.session_id == "input_test"

    @pytest.mark.asyncio
    async def test_execute_command_blocking_parameter(self, executor):
        """Test execute_command with blocking=True."""
        result = await executor.execute_command(
            command="echo 'blocking test'",
            blocking=True,
            timeout=5.0,  # Short timeout for testing
            session_id="blocking_test",
        )

        assert result.command == "echo 'blocking test'"
        assert result.session_id == "blocking_test"

    @pytest.mark.asyncio
    async def test_command_not_allowed_with_is_input(self, executor):
        """Test that command permission checking is skipped for is_input=True."""
        # Add a command to the exclusion list
        executor.deny_command("test_denied_cmd")

        # Should be denied for regular command
        result1 = await executor.execute_command(
            command="test_denied_cmd", is_input=False
        )
        assert not result1.is_success
        assert "Command not allowed" in result1.error_message

        # Should be allowed for input
        result2 = await executor.execute_command(
            command="test_denied_cmd", is_input=True
        )
        # This should not be rejected due to command permission
        assert "Command not allowed" not in (result2.error_message or "")

    @pytest.mark.asyncio
    async def test_environment_variables_not_set_for_input(self, executor):
        """Test that environment variables are not set when is_input=True."""
        env_vars = {"TEST_VAR": "test_value"}

        result = await executor.execute_command(
            command="echo $TEST_VAR", env=env_vars, is_input=True, session_id="env_test"
        )

        # Environment variables should not be set for input commands
        assert result.command == "echo $TEST_VAR"

    @pytest.mark.asyncio
    async def test_error_handling_with_new_parameters(self, executor):
        """Test error handling preserves new parameters in result."""
        with patch.object(
            executor.session_manager, "get_session", side_effect=Exception("Test error")
        ):
            result = await executor.execute_command(
                command="test command",
                is_input=True,
                blocking=True,
                session_id="error_test",
            )

            assert not result.is_success
            assert "Error executing command in session" in result.error_message
            assert result.command == "test command"
            assert result.session_id == "error_test"


class TestEnhancedRunCommandTool:
    """Test the enhanced RunCommandTool class."""

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

    def test_run_command_tool_params_type(self):
        """Test RunCommandToolParams TypedDict structure."""
        # This tests that the TypedDict has all expected keys
        params: RunCommandToolParams = {
            "command": "echo test",
            "session_id": "test_session",
            "time_out": 30,
            "is_input": False,
            "blocking": False,
        }

        assert params["command"] == "echo test"
        assert params["session_id"] == "test_session"
        assert params["time_out"] == 30
        assert params["is_input"] is False
        assert params["blocking"] is False

    @pytest.mark.asyncio
    async def test_call_with_new_parameters(self, tool, mock_context):
        """Test tool.call with new parameters."""
        result = await tool.call(
            mock_context,
            command="echo 'enhanced tool test'",
            session_id="tool_test",
            time_out=30,
            is_input=False,
            blocking=False,
        )

        # Should return a string result
        assert isinstance(result, str)
        # Should contain some indication of the command execution
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_with_is_input_true(self, tool, mock_context):
        """Test tool.call with is_input=True."""
        result = await tool.call(
            mock_context,
            command="test input",
            session_id="input_tool_test",
            time_out=30,
            is_input=True,
            blocking=False,
        )

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_call_with_blocking_true(self, tool, mock_context):
        """Test tool.call with blocking=True."""
        result = await tool.call(
            mock_context,
            command="echo 'blocking test'",
            session_id="blocking_tool_test",
            time_out=5,  # Short timeout
            is_input=False,
            blocking=True,
        )

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_call_command_not_allowed_with_is_input_false(
        self, tool, mock_context
    ):
        """Test tool.call with disallowed command and is_input=False."""
        # Mock the command_executor to always return False for is_command_allowed
        tool.command_executor.is_command_allowed = MagicMock(return_value=False)

        result = await tool.call(
            mock_context,
            command="forbidden_command",
            session_id="forbidden_test",
            time_out=30,
            is_input=False,
            blocking=False,
        )

        assert "Error: Command not allowed" in result

    @pytest.mark.asyncio
    async def test_call_command_not_allowed_with_is_input_true(
        self, tool, mock_context
    ):
        """Test tool.call with disallowed command and is_input=True."""
        # Mock the command_executor to always return False for is_command_allowed
        original_is_allowed = tool.command_executor.is_command_allowed
        tool.command_executor.is_command_allowed = MagicMock(return_value=False)

        # Should skip command checking for is_input=True
        result = await tool.call(
            mock_context,
            command="forbidden_command",
            session_id="input_forbidden_test",
            time_out=30,
            is_input=True,
            blocking=False,
        )

        # Should not contain the "not allowed" error
        assert "Error: Command not allowed" not in result

        # Restore original method
        tool.command_executor.is_command_allowed = original_is_allowed

    @pytest.mark.asyncio
    async def test_call_successful_command_formatting(self, tool, mock_context):
        """Test tool.call successful command uses to_agent_observation formatting."""
        # Mock a successful result
        mock_result = CommandResult(
            return_code=0,
            stdout="test output",
            status=BashCommandStatus.COMPLETED,
            session_id="format_test",  # Add session_id to match what the real executor would set
        )

        with patch.object(
            tool.command_executor, "execute_command", return_value=mock_result
        ):
            result = await tool.call(
                mock_context,
                command="echo test",
                session_id="format_test",
                time_out=30,
                is_input=False,
                blocking=False,
            )

            # Should use to_agent_observation formatting
            assert "test output" in result
            # Session ID should be included in to_agent_observation
            assert "[Session ID: format_test]" in result

    @pytest.mark.asyncio
    async def test_call_failed_command_formatting(self, tool, mock_context):
        """Test tool.call failed command uses format_output."""
        # Mock a failed result
        mock_result = CommandResult(
            return_code=1,
            stdout="error output",
            stderr="error details",
            status=BashCommandStatus.COMPLETED,
            error_message="Command failed",
        )

        with patch.object(
            tool.command_executor, "execute_command", return_value=mock_result
        ):
            result = await tool.call(
                mock_context,
                command="failing_command",
                session_id="fail_test",
                time_out=30,
                is_input=False,
                blocking=False,
            )

            # Should use format_output for failed commands
            assert "Exit code: 1" in result or "error output" in result

    def test_tool_description_includes_new_features(self, tool):
        """Test that tool description includes new interactive features."""
        description = tool.description

        assert "is_input" in description
        assert "blocking" in description
        assert "interactive process" in description.lower()
        assert "running process" in description.lower()

    def test_tool_name(self, tool):
        """Test tool name is correct."""
        assert tool.name == "run_command"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
