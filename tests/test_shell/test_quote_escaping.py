"""Tests for single quote escaping in command executor."""

import os
import sys
import pytest

from mcp_claude_code.tools.shell.base import CommandResult


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Single quote escaping test only applies to Unix shells",
)
async def test_execute_command_with_single_quotes(command_executor, temp_dir) -> None:
    """Test executing a command that contains single quotes."""
    # Create a test file with a string containing single quotes
    test_file = os.path.join(temp_dir, "single_quote_test.txt")
    with open(test_file, "w") as f:
        f.write('file_path="/test/path"\nother_line')

    # Command with single quotes in the pattern (which previously would fail)
    command = f"grep -A1 'file_path=\"' {test_file}"

    # Execute the command (cwd parameter removed as it's handled by persistent sessions)
    result: CommandResult = await command_executor.execute_command(command)

    # Verify result
    assert result.is_success, f"Command failed with stderr: {result.stderr}"
    assert 'file_path="/test/path"' in result.stdout
    assert "other_line" in result.stdout


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Single quote escaping test only applies to Unix shells",
)
async def test_execute_command_with_complex_quotes(command_executor, temp_dir) -> None:
    """Test executing a command with complex quote patterns."""
    # Create a test file with multiple quote patterns
    test_file = os.path.join(temp_dir, "complex_quote_test.txt")
    with open(test_file, "w") as f:
        f.write("line with 'single' quotes\n")
        f.write('line with "double" quotes\n')
        f.write("line with both 'single' and \"double\" quotes\n")
        f.write("line with file_path cannot be empty error\n")

    # Test commands with various quote patterns
    commands = [
        f"grep 'single' {test_file}",
        f'grep "double" {test_file}',
        f'grep -n -B1 -A1 "file_path cannot be empty" {test_file}',
    ]

    for cmd in commands:
        # Execute the command (cwd parameter removed as it's handled by persistent sessions)
        result: CommandResult = await command_executor.execute_command(cmd)

        # Verify result
        assert result.is_success, f"Command failed: {cmd}\nStderr: {result.stderr}"
        assert result.stdout.strip(), f"Command returned empty output: {cmd}"
