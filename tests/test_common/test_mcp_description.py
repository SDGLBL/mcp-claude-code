"""Tests for the BaseTool mcp_description method.

This module contained tests for the mcp_description method of the BaseTool class,
but that functionality has been removed in favor of pydantic Field annotations.
These tests are now obsolete.
"""

from unittest.mock import MagicMock

import pytest


from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.common.thinking_tool import ThinkingTool
from mcp_claude_code.tools.filesystem.read import ReadTool


class TestMCPDescription:
    """Test cases for the BaseTool.mcp_description method (OBSOLETE)."""

    @pytest.fixture
    def permission_manager(self):
        """Create a test permission manager."""
        return MagicMock(spec=PermissionManager)

    @pytest.fixture
    def thinking_tool(self):
        """Create a thinking tool."""
        return ThinkingTool()

    @pytest.fixture
    def read_files_tool(self, permission_manager):
        """Create a read files tool."""
        return ReadTool(permission_manager)

    def test_tools_have_basic_properties(self, thinking_tool, read_files_tool):
        """Test that tools still have basic properties after refactor."""
        # Verify basic tool properties still exist
        assert thinking_tool.name == "think"
        assert "think" in thinking_tool.description.lower()

        assert read_files_tool.name == "read"
        assert "read" in read_files_tool.description.lower()
