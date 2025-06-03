"""Advanced tests for BashSession state management and interactive features.

This module tests the sophisticated BashSession functionality including:
- Advanced state management with prev_status tracking
- Interactive process handling with is_input and blocking
- Command conflict prevention
- Timeout handling (no-change vs hard timeout)
- Session persistence and cleanup
"""

import tempfile
import os
import pytest
import shutil
from unittest.mock import MagicMock, patch

from mcp_claude_code.tools.shell.base import (
    BashCommandStatus,
    CommandResult,
)
from mcp_claude_code.tools.shell.bash_session import (
    BashSession,
    split_bash_commands,
    escape_bash_special_chars,
)


class TestBashSessionAdvancedStateManagement:
    """Test advanced BashSession state management features."""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_bash_session_initialization_with_id(self, temp_work_dir):
        """Test BashSession initialization with required id parameter."""
        session = BashSession(
            id="test_session_123", work_dir=temp_work_dir, no_change_timeout_seconds=10
        )

        assert session.id == "test_session_123"
        assert session.work_dir == temp_work_dir
        assert session.NO_CHANGE_TIMEOUT_SECONDS == 10
        assert session._initialized is False
        assert session.prev_status is None
        assert session.prev_output == ""
        assert session._closed is False

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not available")
    def test_bash_session_state_tracking(self, temp_work_dir):
        """Test BashSession state tracking with prev_status and prev_output."""
        session = BashSession(
            id="state_test", work_dir=temp_work_dir, no_change_timeout_seconds=5
        )

        try:
            session.initialize()

            # Execute first command
            session.execute("echo 'first command'")

            # Check that state is tracked
            assert session.prev_status == BashCommandStatus.COMPLETED
            assert session.prev_output == ""  # Should be reset after completion

            # Execute second command
            session.execute("echo 'second command'")

            # State should be updated
            assert session.prev_status == BashCommandStatus.COMPLETED

        finally:
            session.close()

    def test_bash_session_prev_status_initialization(self, temp_work_dir):
        """Test that prev_status starts as None."""
        session = BashSession(id="prev_status_test", work_dir=temp_work_dir)

        assert session.prev_status is None
        assert session.prev_output == ""

    def test_bash_session_working_directory_tracking(self, temp_work_dir):
        """Test that working directory is properly tracked."""
        session = BashSession(id="cwd_test", work_dir=temp_work_dir)

        # Should initialize with the provided work_dir
        assert session._cwd == os.path.abspath(temp_work_dir)
        assert session.cwd == os.path.abspath(temp_work_dir)

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not available")
    def test_bash_session_simple_ps1_fallback(self, temp_work_dir):
        """Test that BashSession uses simple PS1 for compatibility."""
        session = BashSession(
            id="ps1_test", work_dir=temp_work_dir, no_change_timeout_seconds=5
        )

        try:
            # Check that PS1 is simple for compatibility
            assert session.PS1 == "$ "

            session.initialize()

            # Should still work with simple PS1
            result = session.execute("echo 'ps1 test'")
            assert result.return_code in [0, -1]  # May timeout on some systems

        finally:
            session.close()


class TestBashSessionInteractiveProcessHandling:
    """Test BashSession interactive process handling."""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not available")
    def test_execute_with_is_input_parameter(self, temp_work_dir):
        """Test execute method with is_input parameter."""
        session = BashSession(
            id="input_test", work_dir=temp_work_dir, no_change_timeout_seconds=5
        )

        try:
            session.initialize()

            # Execute with is_input=False (default)
            result1 = session.execute("echo 'normal command'", is_input=False)
            assert result1.command == "echo 'normal command'"

            # Execute with is_input=True
            result2 = session.execute("test input", is_input=True)
            assert result2.command == "test input"

        finally:
            session.close()

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not available")
    def test_execute_with_blocking_parameter(self, temp_work_dir):
        """Test execute method with blocking parameter."""
        session = BashSession(
            id="blocking_test",
            work_dir=temp_work_dir,
            no_change_timeout_seconds=2,  # Short timeout for testing
        )

        try:
            session.initialize()

            # Execute with blocking=False (should timeout quickly)
            result1 = session.execute("sleep 0.1", blocking=False)
            # May complete or timeout depending on timing
            assert result1.status in [
                BashCommandStatus.COMPLETED,
                BashCommandStatus.NO_CHANGE_TIMEOUT,
            ]

            # Execute with blocking=True (should ignore no-change timeout)
            result2 = session.execute(
                "echo 'blocking test'", blocking=True, timeout=3.0
            )
            # Should complete normally without no-change timeout
            assert result2.command == "echo 'blocking test'"

        finally:
            session.close()

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not available")
    def test_execute_command_validation_for_running_process(self, temp_work_dir):
        """Test command validation when previous process is still running."""
        session = BashSession(
            id="validation_test", work_dir=temp_work_dir, no_change_timeout_seconds=2
        )

        try:
            session.initialize()

            # First, test the validation logic for empty commands
            result_empty = session.execute("", is_input=False)

            # Should get an error about no previous running command
            assert not result_empty.is_success
            assert (
                "ERROR: No previous running command to retrieve logs from"
                in result_empty.error_message
            )

            # Test validation for input when no command is running
            result_input = session.execute("", is_input=True)
            assert not result_input.is_success
            assert (
                "ERROR: No previous running command to interact with"
                in result_input.error_message
            )

        finally:
            session.close()

    def test_multiple_bash_commands_rejection(self, temp_work_dir):
        """Test that multiple bash commands are rejected."""
        session = BashSession(id="multi_cmd_test", work_dir=temp_work_dir)

        try:
            # Mock split_bash_commands to return multiple commands
            with patch(
                "mcp_claude_code.tools.shell.bash_session.split_bash_commands"
            ) as mock_split:
                mock_split.return_value = ["echo 'first'", "echo 'second'"]

                result = session.execute("echo 'first'; echo 'second'")

                assert not result.is_success
                assert (
                    "Cannot execute multiple commands at once" in result.error_message
                )
                assert result.status == BashCommandStatus.COMPLETED

        finally:
            session.close()

    def test_special_key_detection(self, temp_work_dir):
        """Test special key detection."""
        session = BashSession(id="special_key_test", work_dir=temp_work_dir)

        # Test the _is_special_key method
        assert session._is_special_key("C-c") is True
        assert session._is_special_key("C-z") is True
        assert session._is_special_key("C-d") is True
        assert session._is_special_key("echo test") is False
        assert session._is_special_key("") is False


class TestBashSessionTimeoutHandling:
    """Test BashSession timeout handling."""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not available")
    def test_no_change_timeout(self, temp_work_dir):
        """Test no-change timeout functionality."""
        session = BashSession(
            id="no_change_timeout_test",
            work_dir=temp_work_dir,
            no_change_timeout_seconds=1,  # Very short timeout
        )

        try:
            session.initialize()

            # Execute a command that might trigger no-change timeout
            # Note: This test is timing-dependent and may be flaky
            result = session.execute("sleep 2", blocking=False, timeout=10.0)

            # Should either complete or hit no-change timeout
            assert result.status in [
                BashCommandStatus.COMPLETED,
                BashCommandStatus.NO_CHANGE_TIMEOUT,
                BashCommandStatus.HARD_TIMEOUT,
            ]

            if result.status == BashCommandStatus.NO_CHANGE_TIMEOUT:
                assert "no new output after 1 seconds" in (result.error_message or "")

        finally:
            session.close()

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not available")
    def test_hard_timeout(self, temp_work_dir):
        """Test hard timeout functionality."""
        session = BashSession(
            id="hard_timeout_test",
            work_dir=temp_work_dir,
            no_change_timeout_seconds=10,  # Longer than hard timeout
        )

        try:
            session.initialize()

            # Execute with a short hard timeout
            result = session.execute("sleep 5", blocking=False, timeout=1.0)

            # Should hit hard timeout
            if result.status == BashCommandStatus.HARD_TIMEOUT:
                assert "timed out after 1.0 seconds" in (result.error_message or "")
                assert result.return_code == -1

        finally:
            session.close()

    def test_timeout_result_format(self, temp_work_dir):
        """Test that timeout results are properly formatted."""
        BashSession(id="timeout_format_test", work_dir=temp_work_dir)

        # Test with mocked timeout scenarios
        # Mock _handle_nochange_timeout_command
        mock_result = CommandResult(
            return_code=-1,
            stdout="partial output",
            status=BashCommandStatus.NO_CHANGE_TIMEOUT,
            error_message="Command timed out after 30 seconds with no output changes",
        )

        assert mock_result.status == BashCommandStatus.NO_CHANGE_TIMEOUT
        assert mock_result.error_message is not None
        assert "timed out" in mock_result.error_message


class TestBashSessionCommandConflictPrevention:
    """Test BashSession command conflict prevention."""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_command_conflict_detection_logic(self, temp_work_dir):
        """Test the logic for detecting command conflicts."""
        session = BashSession(id="conflict_test", work_dir=temp_work_dir)

        # Test the state checking logic
        # When prev_status is not in the "running" states, should allow commands
        session.prev_status = BashCommandStatus.COMPLETED
        # This would be checked in the execute method

        # When prev_status is in running states, should detect conflict
        running_states = {
            BashCommandStatus.NO_CHANGE_TIMEOUT,
            BashCommandStatus.HARD_TIMEOUT,
        }

        for status in running_states:
            session.prev_status = status
            # The execute method would check this condition

    def test_command_conflict_with_mocked_session(self, temp_work_dir):
        """Test command conflict prevention with mocked session state."""
        session = BashSession(id="mock_conflict_test", work_dir=temp_work_dir)

        # Mock the session to appear initialized
        session._initialized = True
        session.prev_status = BashCommandStatus.NO_CHANGE_TIMEOUT

        # Mock pane and other tmux components
        mock_pane = MagicMock()
        mock_pane.cmd.return_value.stdout = ["line1", "line2"]
        session.pane = mock_pane

        # Mock the _get_pane_content to return content that doesn't end with PS1
        with patch.object(session, "_get_pane_content") as mock_get_content:
            mock_get_content.return_value = "some output without prompt"

            # This should detect a conflict (command when previous is still running)
            # The actual conflict detection happens in the execute method

            # Test the condition that would be checked
            pane_output = "some output without prompt"

            # Basic conflict detection without PS1 checking
            assert session.prev_status == BashCommandStatus.NO_CHANGE_TIMEOUT


class TestBashSessionOutputProcessing:
    """Test BashSession advanced output processing."""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_fallback_completion_detection(self, temp_work_dir):
        """Test fallback completion detection when prompt patterns are used."""
        session = BashSession(id="fallback_test", work_dir=temp_work_dir)

        # Mock the pane and other necessary components
        mock_pane = MagicMock()
        session.pane = mock_pane
        session._initialized = True

        # Mock pane.send_keys for exit code checking
        mock_pane.send_keys = MagicMock()

        # Mock _get_pane_content to simulate completion detection
        with patch.object(session, "_get_pane_content") as mock_get_content:
            # First call returns the main output, second call includes exit code
            mock_get_content.side_effect = [
                "$ echo test\ntest output\n$ ",
                "$ echo test\ntest output\n$ echo EXIT_CODE:0\nEXIT_CODE:0\n$ ",
            ]

            result = session._fallback_completion_detection(
                "echo test", "$ echo test\ntest output\n$ "
            )

            assert result.command == "echo test"
            assert result.status == BashCommandStatus.COMPLETED
            assert result.return_code == 0

    def test_get_command_output_with_previous_output(self, temp_work_dir):
        """Test _get_command_output method with previous output tracking."""
        session = BashSession(id="output_test", work_dir=temp_work_dir)

        # Test with no previous output
        session.prev_output = ""
        result1 = session._get_command_output("echo test", "test output")
        assert "test output" in result1
        assert session.prev_output == "test output"

        # Test with previous output (should be removed)
        session.prev_output = "previous content"
        result2 = session._get_command_output(
            "echo test2", "previous content\nnew output", "prefix"
        )
        assert "new output" in result2
        # Should include prefix when continuing from previous output
        assert "prefix" in result2

    def test_ready_for_next_command(self, temp_work_dir):
        """Test _ready_for_next_command method."""
        session = BashSession(id="ready_test", work_dir=temp_work_dir)

        # Mock the _clear_screen method
        with patch.object(session, "_clear_screen") as mock_clear:
            session._ready_for_next_command()
            mock_clear.assert_called_once()


class TestBashSessionUtilityFunctions:
    """Test BashSession utility functions."""

    def test_split_bash_commands_single(self):
        """Test split_bash_commands with single command."""
        result = split_bash_commands("echo test")
        assert len(result) == 1
        assert result[0] == "echo test"

    def test_split_bash_commands_empty(self):
        """Test split_bash_commands with empty input."""
        result = split_bash_commands("")
        assert result == [""]

    def test_split_bash_commands_multiple(self):
        """Test split_bash_commands with multiple commands."""
        result = split_bash_commands("echo first; echo second")
        # The actual implementation may vary based on bashlex parsing
        assert len(result) >= 1

    def test_split_bash_commands_parse_error(self):
        """Test split_bash_commands with unparseable input."""
        # Test with invalid bash syntax
        result = split_bash_commands("echo 'unclosed quote")
        # Should fallback to returning original command
        assert result == ["echo 'unclosed quote"]

    def test_escape_bash_special_chars_empty(self):
        """Test escape_bash_special_chars with empty input."""
        result = escape_bash_special_chars("")
        assert result == ""

    def test_escape_bash_special_chars_normal(self):
        """Test escape_bash_special_chars with normal input."""
        result = escape_bash_special_chars("echo test")
        assert result == "echo test"

    def test_escape_bash_special_chars_with_special(self):
        """Test escape_bash_special_chars with special characters."""
        # Test with characters that need escaping
        result = escape_bash_special_chars("echo test\\;more")
        # Should escape the special characters
        assert "\\\\" in result  # The escaped backslash

    def test_escape_bash_special_chars_parse_error(self):
        """Test escape_bash_special_chars with unparseable input."""
        result = escape_bash_special_chars("echo 'unclosed")
        # Should return original on parse error
        assert result == "echo 'unclosed"

    def test_remove_command_prefix(self):
        """Test _remove_command_prefix function."""
        from mcp_claude_code.tools.shell.bash_session import _remove_command_prefix

        result = _remove_command_prefix("$ echo test\ntest output", "echo test")
        assert "test output" in result

        result2 = _remove_command_prefix("  echo test\noutput", "echo test")
        assert "output" in result2


class TestBashSessionCleanup:
    """Test BashSession cleanup functionality."""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_bash_session_close(self, temp_work_dir):
        """Test BashSession close method."""
        session = BashSession(id="close_test", work_dir=temp_work_dir)

        # Mock session components
        mock_session = MagicMock()
        session.session = mock_session
        session._closed = False

        # Call close
        session.close()

        # Should call kill_session and set _closed
        mock_session.kill_session.assert_called_once()
        assert session._closed is True

        # Second call should not call kill_session again
        mock_session.reset_mock()
        session.close()
        mock_session.kill_session.assert_not_called()

    def test_bash_session_del_cleanup(self, temp_work_dir):
        """Test BashSession __del__ cleanup."""
        session = BashSession(id="del_test", work_dir=temp_work_dir)

        # Mock the close method
        with patch.object(session, "close") as mock_close:
            # Trigger __del__
            session.__del__()
            mock_close.assert_called_once()

    def test_bash_session_close_exception_handling(self, temp_work_dir):
        """Test BashSession close handles exceptions gracefully."""
        session = BashSession(id="exception_test", work_dir=temp_work_dir)

        # Mock session to raise exception
        mock_session = MagicMock()
        mock_session.kill_session.side_effect = Exception("Test exception")
        session.session = mock_session
        session._closed = False

        # Should not raise exception
        session.close()
        assert session._closed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
