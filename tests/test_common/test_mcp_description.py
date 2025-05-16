"""Tests for the BaseTool mcp_description method.

This module contains tests for the mcp_description method of the BaseTool class.
"""

from unittest.mock import MagicMock

import pytest

from mcp_claude_code.tools.common.context import DocumentContext
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.common.thinking_tool import ThinkingTool
from mcp_claude_code.tools.filesystem.edit_file import EditFileTool
from mcp_claude_code.tools.filesystem.read import ReadTool


class TestMCPDescription:
    """Test cases for the BaseTool.mcp_description method."""

    @pytest.fixture
    def document_context(self):
        """Create a test document context."""
        return MagicMock(spec=DocumentContext)

    @pytest.fixture
    def permission_manager(self):
        """Create a test permission manager."""
        return MagicMock(spec=PermissionManager)

    @pytest.fixture
    def thinking_tool(self):
        """Create a thinking tool."""
        return ThinkingTool()

    @pytest.fixture
    def read_files_tool(self, document_context, permission_manager):
        """Create a read files tool."""
        return ReadTool(document_context, permission_manager)

    @pytest.fixture
    def edit_file_tool(self, document_context, permission_manager):
        """Create an edit file tool."""
        return EditFileTool(document_context, permission_manager)

    def test_mcp_description_simple_tool(self, thinking_tool):
        """Test mcp_description for simple tool with single parameter."""
        # Get the mcp_description
        mcp_desc = thinking_tool.mcp_description

        # Verify it contains the base description
        assert "Use the tool to think about something" in mcp_desc

        # Verify it includes parameter description
        assert "Args:" in mcp_desc
        assert "thought: Thought" in mcp_desc

        # Verify it includes return description
        assert "Returns:" in mcp_desc

    def test_mcp_description_with_multiple_parameters(self, read_files_tool):
        """Test mcp_description for a tool with multiple parameters."""
        # Get the mcp_description
        mcp_desc = read_files_tool.mcp_description

        # Verify it contains the base description
        assert "Reads a file from the local filesystem" in mcp_desc

        # Verify it includes parameter descriptions
        assert "Args:" in mcp_desc
        assert "file_path: File Path" in mcp_desc

        # Verify it includes parameter description from the description field
        assert "The absolute path to the file to read" in mcp_desc

        # Verify it includes return description
        assert "Returns:" in mcp_desc

    def test_mcp_description_with_optional_parameters(self, edit_file_tool):
        """Test mcp_description for a tool with optional parameters."""
        # Get the mcp_description
        mcp_desc = edit_file_tool.mcp_description

        # Verify it contains the base description
        assert "Make line-based edits to a text file" in mcp_desc

        # Verify it includes all parameter descriptions
        assert "Args:" in mcp_desc
        assert "path: Path" in mcp_desc
        assert "edits: Edits" in mcp_desc
        assert "dry_run: Dry Run (optional)" in mcp_desc

        # Verify it includes return description
        assert "Returns:" in mcp_desc

    def test_mcp_description_format(self, thinking_tool):
        """Test that mcp_description follows proper formatting."""
        mcp_desc = thinking_tool.mcp_description

        # Check for proper section spacing
        sections = mcp_desc.split("\n\n")
        assert len(sections) >= 3  # Description, Args, Returns at minimum

        # Verify blank lines between sections
        assert "\n\nArgs:" in mcp_desc
        assert "\n\nReturns:" in mcp_desc
