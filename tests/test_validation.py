"""Tests for parameter validation in MCP Claude Code tools."""

from mcp_claude_code.tools.common.validation import (
    validate_path_parameter,
)


def test_validate_path_parameter():
    """Test validation of path parameters."""
    # None path
    result = validate_path_parameter(None)
    assert result.is_error
    assert "path" in result.error_message.lower()  # Default name is 'path'

    # Empty path
    result = validate_path_parameter("")
    assert result.is_error
    assert "empty string" in result.error_message

    # Whitespace only path
    result = validate_path_parameter("  ")
    assert result.is_error

    # Valid path
    result = validate_path_parameter("/valid/path")
    assert not result.is_error

    # Custom parameter name
    result = validate_path_parameter(None, "project_dir")
    assert result.is_error
    assert "project_dir" in result.error_message
