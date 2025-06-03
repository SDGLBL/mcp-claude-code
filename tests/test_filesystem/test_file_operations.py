"""Tests for the file operations module."""

import json
import os
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool

if TYPE_CHECKING:
    from mcp_claude_code.tools.common.permissions import PermissionManager

from mcp_claude_code.tools.filesystem.content_replace import ContentReplaceTool
from mcp_claude_code.tools.filesystem.directory_tree import DirectoryTreeTool
from mcp_claude_code.tools.filesystem.edit import Edit
from mcp_claude_code.tools.filesystem.grep import Grep
from mcp_claude_code.tools.filesystem.read import ReadTool
from mcp_claude_code.tools.filesystem.write import Write


class TestReadTool:
    """Test the ReadTool class."""

    @pytest.fixture
    def read_files_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create a ReadTool instance for testing."""
        return ReadTool(permission_manager)

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
        """Test reading a single allowed file."""
        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Mock the base class method
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await read_files_tool.call(mcp_context, file_path=test_file)

        # Verify result
        assert "This is a test file content" in result

    @pytest.mark.asyncio
    async def test_read_files_single_not_allowed(
        self, read_files_tool: ReadTool, mcp_context: MagicMock
    ):
        """Test reading a file that is not allowed."""
        # Path outside of allowed paths
        path = "/not/allowed/path.txt"

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Mock the base class method
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await read_files_tool.call(mcp_context, file_path=path)

        # Verify result
        assert "Error: Access denied" in result

    @pytest.mark.asyncio
    async def test_read_file_with_offset_and_limit(
        self,
        read_files_tool: ReadTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test reading a file with offset and limit."""
        # Create a test file with multiple lines
        test_file = os.path.join(setup_allowed_path, "multiline_test.txt")
        with open(test_file, "w") as f:
            for i in range(10):
                f.write(f"This is line {i + 1}\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Read with offset and limit
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await read_files_tool.call(
                    mcp_context, file_path=test_file, offset=2, limit=3
                )

        # Verify result contains only the requested lines
        assert "This is line 3" in result  # First line after offset
        assert "This is line 4" in result
        assert "This is line 5" in result  # Last line within limit
        assert "This is line 1" not in result  # Before offset
        assert "This is line 6" not in result  # After limit

    @pytest.mark.asyncio
    async def test_read_file_missing_path(
        self,
        read_files_tool: ReadTool,
        mcp_context: MagicMock,
    ):
        """Test reading with a missing path parameter."""
        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Mock the base class method
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await read_files_tool.call(mcp_context, file_path=None)

        # Verify result
        assert "Error: Parameter 'file_path' is required but was None" in result


class TestWrite:
    """Test the Write class."""

    @pytest.fixture
    def write_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create a Write instance for testing."""
        return Write(permission_manager)

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
    async def test_write(
        self,
        write_tool: Write,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test writing a file."""
        # Create a test path within allowed path
        test_path = os.path.join(setup_allowed_path, "write_test.txt")
        test_content = "Test content for writing"

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Mock the base class method
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await write_tool.call(
                    mcp_context, file_path=test_path, content=test_content
                )

        # Verify result
        assert "Successfully wrote file" in result

        # Verify file was written
        assert os.path.exists(test_path)
        with open(test_path, "r") as f:
            assert f.read() == test_content


class TestEdit:
    """Test the Edit class."""

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
    async def test_edit_file(
        self,
        edit_file_tool: Edit,
        setup_allowed_path: str,
        test_file: str,
        mcp_context: MagicMock,
    ):
        """Test editing a file."""
        # Set up edits
        edits = [
            {
                "oldText": "This is a test file content.",
                "newText": "This is modified content.",
            }
        ]

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Mock the base class method
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await edit_file_tool.call(
                    mcp_context,
                    file_path=test_file,
                    old_string=edits[0]["oldText"],
                    new_string=edits[0]["newText"],
                )

        # Verify result
        assert "Successfully edited file" in result

        # Verify file was modified
        with open(test_file, "r") as f:
            content = f.read()
            assert "This is modified content." in content

    @pytest.mark.asyncio
    async def test_edit_file_with_empty_oldtext(
        self,
        edit_file_tool: Edit,
        setup_allowed_path: str,
        test_file: str,
        mcp_context: MagicMock,
    ):
        """Test editing a file with empty oldText value."""
        # Set up edits with empty oldText
        edits = [
            {
                "oldText": "",  # Empty oldText
                "newText": "This is new content.",
            }
        ]

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Mock the base class method
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await edit_file_tool.call(
                    mcp_context,
                    file_path=test_file,
                    old_string=edits[0]["oldText"],
                    new_string=edits[0]["newText"],
                )

        # Verify result indicates error about empty old_string
        assert (
            "Error: Parameter 'old_string' cannot be empty for existing files" in result
        )

    @pytest.mark.asyncio
    async def test_edit_file_with_whitespace_oldtext(
        self,
        edit_file_tool: Edit,
        setup_allowed_path: str,
        test_file: str,
        mcp_context: MagicMock,
    ):
        """Test editing a file with oldText value that is only whitespace."""
        # Set up edits with whitespace oldText
        edits = [
            {
                "oldText": "   \n  \t ",  # Whitespace oldText
                "newText": "This is new content.",
            }
        ]

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Mock the base class method
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await edit_file_tool.call(
                    mcp_context,
                    file_path=test_file,
                    old_string=edits[0]["oldText"],
                    new_string=edits[0]["newText"],
                )

        # Verify result indicates error about whitespace old_string
        assert (
            "Error: Parameter 'old_string' cannot be empty for existing files" in result
        )

    @pytest.mark.asyncio
    async def test_edit_file_with_missing_oldtext(
        self,
        edit_file_tool: Edit,
        setup_allowed_path: str,
        test_file: str,
        mcp_context: MagicMock,
    ):
        """Test editing a file with a missing oldText field."""
        # Set up edits with missing oldText field
        edits = [
            {
                # Missing oldText field
                "newText": "This is new content.",
            }
        ]

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Mock the base class method
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                # Special handling for missing oldText field
                if "oldText" in edits[0]:
                    result = await edit_file_tool.call(
                        mcp_context,
                        file_path=test_file,
                        old_string=edits[0]["oldText"],
                        new_string=edits[0]["newText"],
                    )
                else:
                    result = await edit_file_tool.call(
                        mcp_context,
                        file_path=test_file,
                        old_string="",
                        new_string=edits[0]["newText"],
                    )

        # Verify result indicates error about missing old_string
        assert (
            "Error: Parameter 'old_string' cannot be empty for existing files" in result
        )


class TestDirectoryTreeTool:
    """Test the DirectoryTreeTool class."""

    @pytest.fixture
    def directory_tree_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create a DirectoryTreeTool instance for testing."""
        return DirectoryTreeTool(permission_manager)

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
    async def test_directory_tree_simple(
        self,
        directory_tree_tool: DirectoryTreeTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test getting a simple directory tree."""
        # Create a test directory structure
        test_dir = os.path.join(setup_allowed_path, "test_dir")
        os.makedirs(test_dir, exist_ok=True)

        # Create some files
        with open(os.path.join(test_dir, "file1.txt"), "w") as f:
            f.write("File 1 content")

        with open(os.path.join(test_dir, "file2.txt"), "w") as f:
            f.write("File 2 content")

        # Create a subdirectory
        subdir = os.path.join(test_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)

        with open(os.path.join(subdir, "subfile.txt"), "w") as f:
            f.write("Subfile content")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Mock the base class method
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await directory_tree_tool.call(mcp_context, path=test_dir)

        # Verify result format
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "subdir/" in result
        assert "subfile.txt" in result
        assert "Directory Stats:" in result

        # Verify the output is not JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(result)

    @pytest.mark.asyncio
    async def test_directory_tree_depth_limited(
        self,
        directory_tree_tool: DirectoryTreeTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test getting a directory tree with depth limit."""
        # Create a test directory structure with multiple levels
        test_dir = os.path.join(setup_allowed_path, "test_deep_dir")
        os.makedirs(test_dir, exist_ok=True)

        # Create level 1
        level1 = os.path.join(test_dir, "level1")
        os.makedirs(level1, exist_ok=True)
        with open(os.path.join(level1, "file1.txt"), "w") as f:
            f.write("Level 1 file")

        # Create level 2
        level2 = os.path.join(level1, "level2")
        os.makedirs(level2, exist_ok=True)
        with open(os.path.join(level2, "file2.txt"), "w") as f:
            f.write("Level 2 file")

        # Create level 3
        level3 = os.path.join(level2, "level3")
        os.makedirs(level3, exist_ok=True)
        with open(os.path.join(level3, "file3.txt"), "w") as f:
            f.write("Level 3 file")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Test with depth=1
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await directory_tree_tool.call(
                    mcp_context, path=test_dir, depth=1, include_filtered=False
                )

        # Verify result shows only level 1 and skips deeper levels
        assert "level1/" in result
        assert "file1.txt" not in result  # This is at level 2
        assert "level2/ [skipped - depth-limit]" in result
        assert "skipped due to depth limit" in result

        # Test with deeper depth
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result2 = await directory_tree_tool.call(
                    mcp_context, path=test_dir, depth=2, include_filtered=False
                )
        assert "level1/" in result2
        assert "file1.txt" in result2  # This should be visible
        assert "level2/" in result2
        assert "level3/ [skipped - depth-limit]" in result2
        # We don't care about file2.txt for this test, as it depends on directory implementation
        assert "file3.txt" not in result2  # This is at level 4

        # Test with unlimited depth
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result3 = await directory_tree_tool.call(
                    mcp_context, path=test_dir, depth=0, include_filtered=False
                )
        assert "level1/" in result3
        assert "level2/" in result3
        assert "level3/" in result3
        assert "file1.txt" in result3
        assert "file2.txt" in result3
        assert "file3.txt" in result3
        assert "[skipped - depth-limit]" not in result3

    @pytest.mark.asyncio
    async def test_directory_tree_filtered_dirs(
        self,
        directory_tree_tool: DirectoryTreeTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test directory tree with filtered directories."""
        # Create a test directory structure with filtered directories
        test_dir = os.path.join(setup_allowed_path, "test_filtered_dir")
        os.makedirs(test_dir, exist_ok=True)

        # Create a normal directory
        normal_dir = os.path.join(test_dir, "normal_dir")
        os.makedirs(normal_dir, exist_ok=True)

        # Create filtered directories
        git_dir = os.path.join(test_dir, ".git")
        node_modules = os.path.join(test_dir, "node_modules")
        venv_dir = os.path.join(test_dir, "venv")

        os.makedirs(git_dir, exist_ok=True)
        os.makedirs(node_modules, exist_ok=True)
        os.makedirs(venv_dir, exist_ok=True)

        # Add some files to each
        with open(os.path.join(normal_dir, "normal.txt"), "w") as f:
            f.write("Normal file")

        with open(os.path.join(git_dir, "HEAD"), "w") as f:
            f.write("Git HEAD file")

        with open(os.path.join(node_modules, "package.json"), "w") as f:
            f.write("Package JSON")

        with open(os.path.join(venv_dir, "pyvenv.cfg"), "w") as f:
            f.write("Python venv config")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Test with default filtering (filtered dirs should be marked but not traversed)
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await directory_tree_tool.call(mcp_context, path=test_dir)

        assert "normal_dir/" in result
        assert "normal.txt" in result
        # Check that filtered directories are marked as skipped
        assert "[skipped - filtered-directory]" in result, (
            "At least one filtered directory should be marked as skipped"
        )

        # HEAD file should not be visible because .git is filtered
        assert "HEAD" not in result
        assert "package.json" not in result
        assert "pyvenv.cfg" not in result

        # Test with include_filtered=True
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result2 = await directory_tree_tool.call(
                    mcp_context, path=test_dir, include_filtered=True
                )

        assert "normal_dir/" in result2
        assert "normal.txt" in result2

        # Filtered directories should now be included - at least one of them
        # should be visible and not marked as skipped
        has_filtered_dir = False
        if ".git/" in result2 and "[skipped - filtered-directory]" not in result2:
            has_filtered_dir = True
        elif (
            "node_modules/" in result2
            and "[skipped - filtered-directory]" not in result2
        ):
            has_filtered_dir = True
        elif "venv/" in result2 and "[skipped - filtered-directory]" not in result2:
            has_filtered_dir = True

        assert has_filtered_dir, (
            "At least one filtered directory should be included when include_filtered=True"
        )

        # At least one file in a previously filtered directory should now be visible
        has_filtered_file = False
        if "HEAD" in result2 or "package.json" in result2 or "pyvenv.cfg" in result2:
            has_filtered_file = True

        assert has_filtered_file, (
            "At least one file from a filtered directory should be visible"
        )

        # Test direct access to filtered directory
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result3 = await directory_tree_tool.call(mcp_context, path=git_dir)

        # When directly accessing a filtered directory, it should be traversed
        assert "HEAD" in result3
        assert "[skipped - filtered-directory]" not in result3

    @pytest.mark.asyncio
    async def test_directory_tree_not_allowed(
        self,
        directory_tree_tool: DirectoryTreeTool,
        mcp_context: MagicMock,
    ):
        """Test directory tree with a path that is not allowed."""
        # Path outside of allowed paths
        path = "/not/allowed/directory"

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await directory_tree_tool.call(mcp_context, path=path)

        # Verify result
        assert "Error: Access denied" in result


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

    @pytest.mark.asyncio
    async def test_search_content_file_path(
        self,
        grep_tool: Grep,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test search_content with a file path (not directory)."""
        # Create a test file with searchable content
        test_file_path = os.path.join(setup_allowed_path, "search_test.txt")
        with open(test_file_path, "w") as f:
            f.write("This is line one with searchable content.\n")
            f.write("This is line two with other content.\n")
            f.write("This is line three with searchable pattern.\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await grep_tool.call(
                    mcp_context,
                    pattern="searchable",
                    path=test_file_path,
                    file_pattern="*",
                )

        # Verify result
        assert "line one with searchable content" in result
        assert "line three with searchable pattern" in result
        assert "line two with other content" not in result
        assert test_file_path in result

    @pytest.mark.asyncio
    async def test_search_content_file_pattern_mismatch(
        self,
        grep_tool: Grep,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test search_content with a file path that doesn't match the file pattern."""
        # Create a test file
        test_file_path = os.path.join(setup_allowed_path, "test_text.txt")
        with open(test_file_path, "w") as f:
            f.write("This file should not be searched.\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await grep_tool.call(
                    mcp_context,
                    pattern="pattern",
                    path=test_file_path,
                    file_pattern="*.py",
                )

        # Verify result
        assert "File does not match pattern '*.py'" in result

    @pytest.mark.asyncio
    async def test_search_content_directory_path(
        self,
        grep_tool: Grep,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test search_content with a directory path."""
        # Create a test directory with multiple files
        test_dir = os.path.join(setup_allowed_path, "search_dir")
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

        # Test searching in all files
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await grep_tool.call(
                    mcp_context, pattern="findable", path=test_dir, file_pattern="*"
                )

        # Verify result contains matches from both files
        assert "file1 with findable content" in result
        assert "file2 with findable content" in result
        assert "different content" not in result

        # Test searching with a file pattern
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result2 = await grep_tool.call(
                    mcp_context, pattern="findable", path=test_dir, file_pattern="*.py"
                )

        # Verify result only contains matches from Python files
        assert "file1 with findable content" not in result2
        assert "file2 with findable content" in result2


class TestContentReplaceTool:
    """Test the ContentReplaceTool class."""

    @pytest.fixture
    def content_replace_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create a ContentReplaceTool instance for testing."""
        return ContentReplaceTool(permission_manager)

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
    async def test_content_replace_file_path(
        self,
        content_replace_tool: ContentReplaceTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test content_replace with a file path (not directory)."""
        # Create a test file with content to replace
        test_file_path = os.path.join(setup_allowed_path, "replace_test.txt")
        with open(test_file_path, "w") as f:
            f.write("This is old content that needs to be replaced.\n")
            f.write("This line should stay the same.\n")
            f.write("More old content here that will be replaced.\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await content_replace_tool.call(
                    mcp_context,
                    pattern="old content",
                    replacement="new content",
                    path=test_file_path,
                    file_pattern="*",
                    dry_run=False,
                )

        # Verify result
        assert "Made 2 replacements of 'old content'" in result
        assert test_file_path in result

        # Verify the file was modified
        with open(test_file_path, "r") as f:
            content = f.read()
            assert "This is new content that needs to be replaced." in content
            assert "This line should stay the same." in content
            assert "More new content here that will be replaced." in content

    @pytest.mark.asyncio
    async def test_content_replace_dry_run(
        self,
        content_replace_tool: ContentReplaceTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test content_replace with dry_run=True on a file path."""
        # Create a test file with content that would be replaced
        test_file_path = os.path.join(setup_allowed_path, "dry_run_test.txt")
        original_content = (
            "This would be replaced in a non-dry run.\n"
            "This line would stay the same.\n"
            "More content that would be replaced.\n"
        )
        with open(test_file_path, "w") as f:
            f.write(original_content)

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await content_replace_tool.call(
                    mcp_context,
                    pattern="would be replaced",
                    replacement="will be changed",
                    path=test_file_path,
                    file_pattern="*",
                    dry_run=True,
                )

        # Verify result shows what would be changed
        assert "Dry run: 2 replacements of 'would be replaced'" in result
        assert test_file_path in result

        # Verify the file was NOT modified
        with open(test_file_path, "r") as f:
            content = f.read()
            assert content == original_content

    @pytest.mark.asyncio
    async def test_content_replace_directory_path(
        self,
        content_replace_tool: ContentReplaceTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test content_replace with a directory path."""
        # Create a test directory with multiple files
        test_dir = os.path.join(setup_allowed_path, "replace_dir")
        os.makedirs(test_dir, exist_ok=True)

        # Create files with replaceable content
        with open(os.path.join(test_dir, "file1.txt"), "w") as f:
            f.write("This is file1 with replaceable text.\n")
            f.write("Another line in file1.\n")

        with open(os.path.join(test_dir, "file2.py"), "w") as f:
            f.write("# This is file2 with replaceable text\n")
            f.write("def example():\n")
            f.write("    return 'No replaceable text here'\n")

        # Create a subdirectory with more files
        subdir = os.path.join(test_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)

        with open(os.path.join(subdir, "file3.txt"), "w") as f:
            f.write("This is file3 with replaceable text.\n")

        # Mock context calls
        tool_ctx = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()

        # Test replacing in all files
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await content_replace_tool.call(
                    mcp_context,
                    pattern="replaceable text",
                    replacement="updated content",
                    path=test_dir,
                    file_pattern="*",
                    dry_run=False,
                )

        # Verify result shows replacements were made
        assert "Made" in result
        assert "replacements of 'replaceable text'" in result
        assert test_dir in result

        # Verify files were modified
        with open(os.path.join(test_dir, "file1.txt"), "r") as f:
            content = f.read()
            assert "This is file1 with updated content." in content

        with open(os.path.join(test_dir, "file2.py"), "r") as f:
            content = f.read()
            assert "# This is file2 with updated content" in content

        with open(os.path.join(subdir, "file3.txt"), "r") as f:
            content = f.read()
            assert "This is file3 with updated content." in content

        # Reset files
        with open(os.path.join(test_dir, "file1.txt"), "w") as f:
            f.write("This is file1 with replaceable text.\n")
            f.write("Another line in file1.\n")

        with open(os.path.join(test_dir, "file2.py"), "w") as f:
            f.write("# This is file2 with replaceable text\n")
            f.write("def example():\n")
            f.write("    return 'No replaceable text here'\n")

        with open(os.path.join(subdir, "file3.txt"), "w") as f:
            f.write("This is file3 with replaceable text.\n")

        # Test replacing with a file pattern - execute the replacement with Python files only
        with patch.object(FilesystemBaseTool, "set_tool_context_info", AsyncMock()):
            with patch.object(
                FilesystemBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                await content_replace_tool.call(
                    mcp_context,
                    pattern="replaceable text",
                    replacement="updated content",
                    path=test_dir,
                    file_pattern="*.py",
                    dry_run=False,
                )

            # Verify only Python files were modified
        with open(os.path.join(test_dir, "file1.txt"), "r") as f:
            content = f.read()
            assert "This is file1 with replaceable text." in content  # Unchanged

        with open(os.path.join(test_dir, "file2.py"), "r") as f:
            content = f.read()
            assert "# This is file2 with updated content" in content  # Changed

        with open(os.path.join(subdir, "file3.txt"), "r") as f:
            content = f.read()
            assert "This is file3 with replaceable text." in content  # Unchanged
