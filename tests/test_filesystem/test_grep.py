"""Tests for the grep tool implementation."""

import os
import shutil
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool
from mcp_claude_code.tools.filesystem.grep import Grep

if TYPE_CHECKING:
    from mcp_claude_code.tools.common.permissions import PermissionManager


class TestGrep:
    """Test the Grep class."""

    @pytest.fixture
    def grep_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create a Grep instance for testing."""
        return Grep(permission_manager)

    @pytest.fixture
    def setup_allowed_path(
        self,
        permission_manager: "PermissionManager",
        temp_dir: str,
    ):
        """Set up an allowed path for testing."""
        permission_manager.add_allowed_path(temp_dir)
        return temp_dir

    def test_tool_properties(self, grep_tool: Grep):
        """Test basic properties of the Grep tool."""
        assert grep_tool.name == "grep"
        assert "Fast content search tool" in grep_tool.description

    @pytest.mark.asyncio
    async def test_grep_file_path_fallback(
        self,
        grep_tool: Grep,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test grep with a file path using the fallback implementation."""
        # Create a test file with searchable content
        test_file_path = os.path.join(setup_allowed_path, "grep_test.txt")
        with open(test_file_path, "w") as f:
            f.write("This is line one with searchable content.\n")
            f.write("This is line two with other content.\n")
            f.write("This is line three with searchable pattern.\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.warning = AsyncMock()
        tool_ctx.report_progress = AsyncMock()

        # Force using the fallback implementation
        with patch.object(Grep, "is_ripgrep_installed", return_value=False):
            with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
                with patch.object(
                    FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
                ):
                    result = await grep_tool.call(
                        mcp_context,
                        pattern="searchable",
                        path=test_file_path,
                    )

        # Verify result
        assert "line one with searchable content" in result
        assert "line three with searchable pattern" in result
        assert "line two with other content" not in result
        assert test_file_path in result

    @pytest.mark.asyncio
    async def test_grep_file_pattern_mismatch_fallback(
        self,
        grep_tool: Grep,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test grep with a file path that doesn't match the include pattern using fallback."""
        # Create a test file
        test_file_path = os.path.join(setup_allowed_path, "test_text.txt")
        with open(test_file_path, "w") as f:
            f.write("This file should not be searched.\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.warning = AsyncMock()

        # Force using the fallback implementation
        with patch.object(Grep, "is_ripgrep_installed", return_value=False):
            with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
                with patch.object(
                    FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
                ):
                    result = await grep_tool.call(
                        mcp_context,
                        pattern="pattern",
                        path=test_file_path,
                        include="*.py",
                    )

        # Verify result
        assert "does not match pattern '*.py'" in result

    @pytest.mark.asyncio
    async def test_grep_directory_path_fallback(
        self,
        grep_tool: Grep,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test grep with a directory path using fallback implementation."""
        # Create a test directory with multiple files
        test_dir = os.path.join(setup_allowed_path, "grep_dir")
        os.makedirs(test_dir, exist_ok=True)

        # Create files with searchable content
        with open(os.path.join(test_dir, "file1.txt"), "w") as f:
            f.write("This is file1 with findable content.\n")

        with open(os.path.join(test_dir, "file2.py"), "w") as f:
            f.write("# This is file2 with findable content\n")
            f.write("def test_function():\n")
            f.write("    return 'Not findable'\n")

        # Create a subdirectory with more files
        subdir = os.path.join(test_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)

        with open(os.path.join(subdir, "file3.txt"), "w") as f:
            f.write("This is file3 with different content.\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.warning = AsyncMock()
        tool_ctx.report_progress = AsyncMock()

        # Force using the fallback implementation
        with patch.object(Grep, "is_ripgrep_installed", return_value=False):
            with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
                with patch.object(
                    FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
                ):
                    result = await grep_tool.call(
                        mcp_context, pattern="findable", path=test_dir
                    )

        # Verify result contains matches from both files
        assert "file1 with findable content" in result
        assert "file2 with findable content" in result
        assert "different content" not in result

    @pytest.mark.asyncio
    async def test_grep_with_include_pattern_fallback(
        self,
        grep_tool: Grep,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test grep with an include pattern using fallback implementation."""
        # Create a test directory with multiple files
        test_dir = os.path.join(setup_allowed_path, "grep_include_dir")
        os.makedirs(test_dir, exist_ok=True)

        # Create files with searchable content
        with open(os.path.join(test_dir, "file1.txt"), "w") as f:
            f.write("This is file1 with findable content.\n")

        with open(os.path.join(test_dir, "file2.py"), "w") as f:
            f.write("# This is file2 with findable content\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.warning = AsyncMock()
        tool_ctx.report_progress = AsyncMock()

        # Force using the fallback implementation
        with patch.object(Grep, "is_ripgrep_installed", return_value=False):
            with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
                with patch.object(
                    FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
                ):
                    result = await grep_tool.call(
                        mcp_context,
                        pattern="findable",
                        path=test_dir,
                        include="*.py",
                    )

        # Verify result only contains matches from Python files
        assert "file1 with findable content" not in result
        assert "file2 with findable content" in result

    @pytest.mark.asyncio
    async def test_ripgrep_json_output_parsing(self, grep_tool: Grep):
        """Test parsing of ripgrep JSON output."""
        # Sample JSON output from ripgrep
        sample_output = """
{"type":"begin","data":{"path":{"text":"/path/to/file1.txt"}}}
{"type":"match","data":{"path":{"text":"/path/to/file1.txt"},"lines":{"text":"This is line one with a match."},"line_number":1,"absolute_offset":0,"submatches":[{"match":{"text":"match"},"start":25,"end":30}]}}
{"type":"match","data":{"path":{"text":"/path/to/file1.txt"},"lines":{"text":"Another line with a match here."},"line_number":3,"absolute_offset":60,"submatches":[{"match":{"text":"match"},"start":18,"end":23}]}}
{"type":"end","data":{"path":{"text":"/path/to/file1.txt"},"binary":false,"stats":{"matches":2,"searches":1}}}
{"type":"begin","data":{"path":{"text":"/path/to/file2.py"}}}
{"type":"match","data":{"path":{"text":"/path/to/file2.py"},"lines":{"text":"def find_match():"},"line_number":5,"absolute_offset":120,"submatches":[{"match":{"text":"match"},"start":9,"end":14}]}}
{"type":"end","data":{"path":{"text":"/path/to/file2.py"},"binary":false,"stats":{"matches":1,"searches":1}}}
"""

        result = grep_tool.parse_ripgrep_json_output(sample_output)

        # Check that the parsed output contains the expected elements
        assert "Found 3 matches in 2 file" in result
        assert "/path/to/file1.txt:1:" in result
        assert "This is line one with a match." in result
        assert "/path/to/file1.txt:3:" in result
        assert "Another line with a match here." in result
        assert "/path/to/file2.py:5:" in result
        assert "def find_match()" in result

    @pytest.mark.asyncio
    async def test_empty_ripgrep_json_output(self, grep_tool: Grep):
        """Test parsing empty ripgrep JSON output."""
        result = grep_tool.parse_ripgrep_json_output("")
        assert "No matches found" in result

    @pytest.mark.asyncio
    async def test_ripgrep_integration(
        self,
        grep_tool: Grep,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test integration with real ripgrep if it's available."""
        # Only run this test if ripgrep is actually installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create a test file with searchable content
        test_file_path = os.path.join(setup_allowed_path, "ripgrep_test.txt")
        with open(test_file_path, "w") as f:
            f.write("This is line one with ripgrep searchable content.\n")
            f.write("This is line two with other content.\n")
            f.write("This is line three with ripgrep searchable pattern.\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.warning = AsyncMock()

        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await grep_tool.call(
                    mcp_context,
                    pattern="ripgrep",
                    path=test_file_path,
                )

        # Verify result
        assert "line one with ripgrep searchable content" in result
        assert "line three with ripgrep searchable pattern" in result
        assert "line two with other content" not in result
        assert test_file_path in result

    @pytest.mark.asyncio
    async def test_no_pattern_parameter(
        self,
        grep_tool: Grep,
        mcp_context: MagicMock,
    ):
        """Test grep without required pattern parameter."""
        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.info = AsyncMock()

        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await grep_tool.call(mcp_context)

        # Verify result
        assert "Error: Parameter 'pattern' is required" in result
        # tool_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_path_parameter(
        self,
        grep_tool: Grep,
        mcp_context: MagicMock,
    ):
        """Test grep with invalid path parameter."""
        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.info = AsyncMock()

        with patch.object(
            FilesystemBaseTool,
            "validate_path",
            return_value=MagicMock(is_error=True, error_message="Invalid path"),
        ):
            with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
                with patch.object(
                    FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
                ):
                    result = await grep_tool.call(
                        mcp_context, pattern="test", path="/invalid/path"
                    )

        # Verify result
        assert "Error: Invalid path" in result
        # tool_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_ripgrep_command_error(
        self,
        grep_tool: Grep,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test handling of ripgrep command execution errors."""
        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.info = AsyncMock()

        # Patch ripgrep installation check and subprocess to simulate an error
        with patch.object(Grep, "is_ripgrep_installed", return_value=True):
            with patch(
                "asyncio.create_subprocess_exec",
                side_effect=Exception("Command execution error"),
            ):
                with patch.object(
                    FilesystemBaseTool, "set_tool_context_info", AsyncMock()
                ):
                    with patch.object(
                        FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
                    ):
                        result = await grep_tool.call(
                            mcp_context, pattern="test", path=setup_allowed_path
                        )

        # Verify result
        assert "Error running ripgrep" in result
        assert "Command execution error" in result
        # tool_ctx.error.assert_called()
