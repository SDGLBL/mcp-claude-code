"""Tests for the refactored filesystem tools."""

import os
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from mcp_claude_code.tools.common.permissions import PermissionManager

from mcp_claude_code.tools.filesystem import (
    Edit,
    ReadTool,
    Write,
    get_filesystem_tools,
)


class TestRefactoredFileTools:
    """Test the refactored filesystem tools."""

    @pytest.fixture
    def fs_tools(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create filesystem tool instances for testing."""
        return get_filesystem_tools(permission_manager)

    @pytest.fixture
    def read_files_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create a ReadTool instance for testing."""
        return ReadTool(permission_manager)

    @pytest.fixture
    def write_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create a Write instance for testing."""
        return Write(permission_manager)

    @pytest.fixture
    def edit_file_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create an Edit instance for testing."""
        return Edit(permission_manager)

    @pytest.fixture
    def setup_allowed_path(
        self,
        permission_manager: "PermissionManager",
        temp_dir: str,
    ):
        """Set up an allowed path for testing."""
        permission_manager.add_allowed_path(temp_dir)
        return temp_dir

    @pytest.mark.asyncio
    async def test_read_files_single_allowed(
        self,
        read_files_tool: ReadTool,
        setup_allowed_path: str,
        test_file: str,
        mcp_context: MagicMock,
    ):
        """Test reading a single allowed file with the refactored tool."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.filesystem.base.create_tool_context",
            return_value=tool_ctx,
        ):
            # Call the tool directly
            result = await read_files_tool.call(ctx=mcp_context, file_path=test_file)

            # Verify result
            assert "This is a test file content" in result
            tool_ctx.info.assert_called()

    @pytest.mark.asyncio
    async def test_write(
        self,
        write_tool: Write,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test writing a file with the refactored tool."""
        # Create a test path within allowed path
        test_path = os.path.join(setup_allowed_path, "write_test.txt")
        test_content = "Test content for writing"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.filesystem.base.create_tool_context",
            return_value=tool_ctx,
        ):
            # Call the tool directly
            result = await write_tool.call(
                ctx=mcp_context, file_path=test_path, content=test_content
            )

            # Verify result
            assert "Successfully wrote file" in result
            tool_ctx.info.assert_called()

            # Verify file was written
            assert os.path.exists(test_path)
            with open(test_path, "r") as f:
                assert f.read() == test_content

    @pytest.mark.asyncio
    async def test_edit_file(
        self,
        edit_file_tool: Edit,
        setup_allowed_path: str,
        test_file: str,
        mcp_context: MagicMock,
    ):
        """Test editing a file with the refactored tool."""
        # Set up edit parameters
        old_string = "This is a test file content."
        new_string = "This is modified content."

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.filesystem.base.create_tool_context",
            return_value=tool_ctx,
        ):
            # Call the tool directly
            result = await edit_file_tool.call(
                ctx=mcp_context,
                file_path=test_file,
                old_string=old_string,
                new_string=new_string,
                expected_replacements=1,
            )

            # Verify result
            assert "Successfully edited file" in result
            tool_ctx.info.assert_called()

            # Verify file was modified
            with open(test_file, "r") as f:
                content = f.read()
                assert "This is modified content." in content
