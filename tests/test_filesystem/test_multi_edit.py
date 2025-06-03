"""Tests for the multi_edit tool."""

import pytest
from unittest.mock import AsyncMock


from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.filesystem.multi_edit import MultiEdit


class TestMultiEdit:
    """Test cases for the MultiEdit tool."""

    @pytest.fixture
    def permission_manager(self):
        """Create a permission manager for testing."""
        return PermissionManager()

    @pytest.fixture
    def multi_edit_tool(self, permission_manager):
        """Create a MultiEdit tool instance for testing."""
        return MultiEdit(permission_manager)

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock MCP context."""
        ctx = AsyncMock()
        ctx.session_id = "test_session"
        return ctx

    def test_tool_properties(self, multi_edit_tool):
        """Test basic tool properties."""
        assert multi_edit_tool.name == "multi_edit"
        assert "multiple edits" in multi_edit_tool.description.lower()

    @pytest.mark.asyncio
    async def test_invalid_edit_object(self, multi_edit_tool, mock_ctx):
        """Test handling of invalid edit objects."""
        result = await multi_edit_tool.call(
            mock_ctx, file_path="/tmp/test.txt", edits=["invalid_edit"]
        )
        assert "Error: Edit at index 0 must be an object" in result

    @pytest.mark.asyncio
    async def test_missing_old_string(self, multi_edit_tool, mock_ctx):
        """Test handling of missing old_string in edit."""
        result = await multi_edit_tool.call(
            mock_ctx, file_path="/tmp/test.txt", edits=[{"new_string": "new"}]
        )
        assert (
            "Error: Parameter 'old_string' in edit at index 0 is required but was None"
            in result
        )

    @pytest.mark.asyncio
    async def test_missing_new_string(self, multi_edit_tool, mock_ctx):
        """Test handling of missing new_string in edit."""
        result = await multi_edit_tool.call(
            mock_ctx, file_path="/tmp/test.txt", edits=[{"old_string": "old"}]
        )
        assert (
            "Error: Parameter 'new_string' in edit at index 0 is required but was None"
            in result
        )

    @pytest.mark.asyncio
    async def test_identical_old_new_strings(self, multi_edit_tool, mock_ctx):
        """Test handling of identical old and new strings."""
        result = await multi_edit_tool.call(
            mock_ctx,
            file_path="/tmp/test.txt",
            edits=[{"old_string": "same", "new_string": "same"}],
        )
        assert (
            "Error: Edit at index 0: old_string and new_string are identical" in result
        )

    @pytest.mark.asyncio
    async def test_invalid_expected_replacements(self, multi_edit_tool, mock_ctx):
        """Test handling of invalid expected_replacements value."""
        result = await multi_edit_tool.call(
            mock_ctx,
            file_path="/tmp/test.txt",
            edits=[
                {"old_string": "old", "new_string": "new", "expected_replacements": -1}
            ],
        )
        assert (
            "Error: Parameter 'expected_replacements' in edit at index 0 must be a non-negative number"
            in result
        )

    @pytest.mark.asyncio
    async def test_successful_multiple_edits(self, multi_edit_tool, mock_ctx, tmp_path):
        """Test successful application of multiple edits."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_content = """line 1
line 2
line 3
line 4"""
        test_file.write_text(test_content)

        # Temporarily patch the permission manager to allow the temp path
        original_is_path_allowed = multi_edit_tool.permission_manager.is_path_allowed
        multi_edit_tool.permission_manager.is_path_allowed = (
            lambda path: str(tmp_path) in path
        )

        try:
            result = await multi_edit_tool.call(
                mock_ctx,
                file_path=str(test_file),
                edits=[
                    {"old_string": "line 1", "new_string": "modified line 1"},
                    {"old_string": "line 3", "new_string": "modified line 3"},
                ],
            )

            # Check that the operation was successful
            assert "Successfully applied 2 edits" in result
            assert "2 total replacements" in result

            # Verify the file content was updated correctly
            updated_content = test_file.read_text()
            assert "modified line 1" in updated_content
            assert "modified line 3" in updated_content
            assert "line 2" in updated_content  # unchanged
            assert "line 4" in updated_content  # unchanged
        finally:
            # Restore the original permission manager
            multi_edit_tool.permission_manager.is_path_allowed = (
                original_is_path_allowed
            )

    @pytest.mark.asyncio
    async def test_file_creation_with_multiple_edits(
        self, multi_edit_tool, mock_ctx, tmp_path
    ):
        """Test creating a new file with multiple edits."""
        # Test file that doesn't exist yet
        test_file = tmp_path / "new_file.txt"

        # Temporarily patch the permission manager to allow the temp path
        original_is_path_allowed = multi_edit_tool.permission_manager.is_path_allowed
        multi_edit_tool.permission_manager.is_path_allowed = (
            lambda path: str(tmp_path) in path
        )

        try:
            result = await multi_edit_tool.call(
                mock_ctx,
                file_path=str(test_file),
                edits=[
                    {"old_string": "", "new_string": "Initial content\nSecond line"},
                    {"old_string": "Second line", "new_string": "Modified second line"},
                ],
            )

            # Check that the operation was successful
            assert "Successfully created file" in result

            # Verify the file was created with correct content
            assert test_file.exists()
            content = test_file.read_text()
            assert "Initial content" in content
            assert "Modified second line" in content
        finally:
            # Restore the original permission manager
            multi_edit_tool.permission_manager.is_path_allowed = (
                original_is_path_allowed
            )

    @pytest.mark.asyncio
    async def test_edit_not_found(self, multi_edit_tool, mock_ctx, tmp_path):
        """Test handling when old_string is not found in file."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_content = "line 1\nline 2"
        test_file.write_text(test_content)

        # Temporarily patch the permission manager to allow the temp path
        original_is_path_allowed = multi_edit_tool.permission_manager.is_path_allowed
        multi_edit_tool.permission_manager.is_path_allowed = (
            lambda path: str(tmp_path) in path
        )

        try:
            result = await multi_edit_tool.call(
                mock_ctx,
                file_path=str(test_file),
                edits=[
                    {"old_string": "line 1", "new_string": "modified line 1"},
                    {"old_string": "nonexistent line", "new_string": "new content"},
                ],
            )

            # Check that the operation failed with appropriate error
            assert "Error: Edit 2: The specified old_string was not found" in result
        finally:
            # Restore the original permission manager
            multi_edit_tool.permission_manager.is_path_allowed = (
                original_is_path_allowed
            )

    @pytest.mark.asyncio
    async def test_expected_replacements_mismatch(
        self, multi_edit_tool, mock_ctx, tmp_path
    ):
        """Test handling when expected_replacements doesn't match actual occurrences."""
        # Create a test file with duplicate content
        test_file = tmp_path / "test.txt"
        test_content = "duplicate\nduplicate\nother line"
        test_file.write_text(test_content)

        # Temporarily patch the permission manager to allow the temp path
        original_is_path_allowed = multi_edit_tool.permission_manager.is_path_allowed
        multi_edit_tool.permission_manager.is_path_allowed = (
            lambda path: str(tmp_path) in path
        )

        try:
            result = await multi_edit_tool.call(
                mock_ctx,
                file_path=str(test_file),
                edits=[
                    {
                        "old_string": "duplicate",
                        "new_string": "modified",
                        "expected_replacements": 1,
                    }
                ],
            )

            # Check that the operation failed with appropriate error
            assert (
                "Error: Edit 1: Found 2 occurrences of the specified old_string, but expected 1"
                in result
            )
        finally:
            # Restore the original permission manager
            multi_edit_tool.permission_manager.is_path_allowed = (
                original_is_path_allowed
            )
