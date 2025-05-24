"""Tests for the Jupyter notebook operations module."""

import json
import os
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from mcp_claude_code.tools.common.context import DocumentContext
    from mcp_claude_code.tools.common.permissions import PermissionManager

from mcp_claude_code.tools.jupyter.notebook_operations import JupyterNotebookTools


class TestJupyterNotebookTools:
    """Test the JupyterNotebookTools class."""

    @pytest.fixture
    def jupyter_tools(
        self,
        document_context: "DocumentContext",
        permission_manager: "PermissionManager",
    ):
        """Create a JupyterNotebookTools instance for testing."""
        return JupyterNotebookTools(document_context, permission_manager)

    @pytest.fixture
    def sample_notebook_path(
        self, temp_dir: str, permission_manager: "PermissionManager"
    ):
        """Create a sample Jupyter notebook for testing."""
        # Add the temp directory to allowed paths
        permission_manager.add_allowed_path(temp_dir)
        notebook_path = os.path.join(temp_dir, "test_notebook.ipynb")

        # Create a simple notebook structure
        notebook = {
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3 (ipykernel)",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {
                    "codemirror_mode": {"name": "ipython", "version": 3},
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.11.11",
                },
            },
            "nbformat": 4,
            "nbformat_minor": 5,
            "cells": [
                {
                    "cell_type": "markdown",
                    "id": "markdown-cell-id",
                    "metadata": {},
                    "source": "# Test Notebook\n\nThis is a test markdown cell.",
                },
                {
                    "cell_type": "code",
                    "execution_count": 1,
                    "id": "code-cell-id-1",
                    "metadata": {},
                    "source": "# This is a code cell\nprint('Hello, world!')",
                    "outputs": [
                        {
                            "name": "stdout",
                            "output_type": "stream",
                            "text": "Hello, world!\n",
                        }
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": 2,
                    "id": "code-cell-id-2",
                    "metadata": {},
                    "source": "# Cell with error\n1/0",
                    "outputs": [
                        {
                            "ename": "ZeroDivisionError",
                            "evalue": "division by zero",
                            "output_type": "error",
                            "traceback": [
                                "\u001b[0;31m---------------------------------------------------------------------------\u001b[0m",
                                "\u001b[0;31mZeroDivisionError\u001b[0m                         Traceback (most recent call last)",
                                "Cell \u001b[0;32mIn[2], line 1\u001b[0m\n\u001b[0;32m----> 1\u001b[0m \u001b[38;5;241;43m1\u001b[39;49m\u001b[38;5;241;43m/\u001b[39;49m\u001b[38;5;241;43m0\u001b[39;49m\n",
                                "\u001b[0;31mZeroDivisionError\u001b[0m: division by zero",
                            ],
                        }
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "id": "empty-cell-id",
                    "metadata": {},
                    "source": "",
                    "outputs": [],
                },
            ],
        }

        # Write the notebook to file
        with open(notebook_path, "w") as f:
            json.dump(notebook, f, indent=2)

        return notebook_path

    def test_initialization(
        self,
        document_context: "DocumentContext",
        permission_manager: "PermissionManager",
    ):
        """Test initializing JupyterNotebookTools."""
        jupyter_tools = JupyterNotebookTools(document_context, permission_manager)

        assert jupyter_tools.document_context is document_context
        assert jupyter_tools.permission_manager is permission_manager

    def test_register_tools(self, jupyter_tools: JupyterNotebookTools):
        """Test registering tools with MCP server."""
        mock_server = MagicMock()
        mock_server.tool = MagicMock(return_value=lambda x: x)

        jupyter_tools.register_tools(mock_server)

        # Verify that tool decorators were called
        assert mock_server.tool.call_count > 0

    @pytest.mark.asyncio
    async def test_read_notebook(
        self,
        jupyter_tools: JupyterNotebookTools,
        sample_notebook_path: str,
        mcp_context: MagicMock,
    ):
        """Test reading a Jupyter notebook."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the read_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted read_notebook function
            result = await tools["read_notebook"](sample_notebook_path, mcp_context)

            # Verify result
            assert "Test Notebook" in result
            assert "Hello, world!" in result
            assert "ZeroDivisionError" in result
            tool_ctx.info.assert_called()

    @pytest.mark.asyncio
    async def test_read_notebook_not_allowed(
        self,
        jupyter_tools: JupyterNotebookTools,
        mcp_context: MagicMock,
    ):
        """Test reading a notebook that is not allowed."""
        # Path outside of allowed paths
        path = "/not/allowed/notebook.ipynb"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the read_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted read_notebook function
            result = await tools["read_notebook"](path, mcp_context)

            # Verify result
            assert "Error: Access denied" in result
            tool_ctx.error.assert_called()

    @pytest.mark.asyncio
    async def test_read_notebook_invalid_extension(
        self,
        jupyter_tools: JupyterNotebookTools,
        temp_dir: str,
        mcp_context: MagicMock,
    ):
        """Test reading a file that is not a Jupyter notebook."""
        # Create a non-notebook file
        text_file_path = os.path.join(temp_dir, "test.txt")
        with open(text_file_path, "w") as f:
            f.write("This is not a notebook.")

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the read_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted read_notebook function
            result = await tools["read_notebook"](text_file_path, mcp_context)

            # Verify result
            assert "Error: File is not a Jupyter notebook" in result
            tool_ctx.error.assert_called()

    @pytest.mark.asyncio
    async def test_read_notebook_nonexistent_file(
        self,
        jupyter_tools: JupyterNotebookTools,
        temp_dir: str,
        mcp_context: MagicMock,
    ):
        """Test reading a nonexistent notebook file."""
        # Path to a nonexistent file
        nonexistent_path = os.path.join(temp_dir, "nonexistent.ipynb")

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the read_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted read_notebook function
            result = await tools["read_notebook"](nonexistent_path, mcp_context)

            # Verify result
            assert "Error: File does not exist" in result
            tool_ctx.error.assert_called()

    @pytest.mark.asyncio
    async def test_read_notebook_invalid_json(
        self,
        jupyter_tools: JupyterNotebookTools,
        temp_dir: str,
        mcp_context: MagicMock,
    ):
        """Test reading an invalid JSON notebook."""
        # Create an invalid JSON notebook
        invalid_path = os.path.join(temp_dir, "invalid.ipynb")
        with open(invalid_path, "w") as f:
            f.write("This is not valid JSON for a notebook.")

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the read_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted read_notebook function
            result = await tools["read_notebook"](invalid_path, mcp_context)

            # Verify result
            assert "Error: Invalid notebook format" in result
            tool_ctx.error.assert_called()

    @pytest.mark.asyncio
    async def test_edit_notebook_replace(
        self,
        jupyter_tools: JupyterNotebookTools,
        sample_notebook_path: str,
        mcp_context: MagicMock,
    ):
        """Test replacing a cell in a Jupyter notebook."""
        new_content = "# Updated cell\nprint('Updated content')"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the edit_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted edit_notebook function to replace the second cell (index 1)
            result = await tools["edit_notebook"](
                sample_notebook_path, 1, new_content, mcp_context, None, "replace"
            )

            # Verify result
            assert "Successfully edited notebook" in result
            assert "Replaced cell 1" in result
            tool_ctx.info.assert_called()

            # Verify the notebook was updated
            with open(sample_notebook_path, "r") as f:
                notebook = json.load(f)
                assert notebook["cells"][1]["source"] == new_content
                # Verify execution count was reset
                assert notebook["cells"][1]["execution_count"] is None
                # Verify outputs were cleared
                assert notebook["cells"][1]["outputs"] == []

    @pytest.mark.asyncio
    async def test_edit_notebook_insert(
        self,
        jupyter_tools: JupyterNotebookTools,
        sample_notebook_path: str,
        mcp_context: MagicMock,
    ):
        """Test inserting a cell in a Jupyter notebook."""
        new_content = "# New inserted cell\nprint('Inserted content')"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the edit_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Get the original number of cells
            with open(sample_notebook_path, "r") as f:
                notebook = json.load(f)
                original_cell_count = len(notebook["cells"])

            # Use the extracted edit_notebook function to insert a new cell at index 1
            result = await tools["edit_notebook"](
                sample_notebook_path, 1, new_content, mcp_context, "code", "insert"
            )

            # Verify result
            assert "Successfully edited notebook" in result
            assert "Inserted new code cell at position 1" in result
            tool_ctx.info.assert_called()

            # Verify the notebook was updated
            with open(sample_notebook_path, "r") as f:
                notebook = json.load(f)
                # Check cell count increased by 1
                assert len(notebook["cells"]) == original_cell_count + 1
                # Check the new cell was inserted at index 1
                assert notebook["cells"][1]["source"] == new_content
                assert notebook["cells"][1]["cell_type"] == "code"
                # Verify execution count is None
                assert notebook["cells"][1]["execution_count"] is None
                # Verify outputs are empty
                assert notebook["cells"][1]["outputs"] == []

    @pytest.mark.asyncio
    async def test_edit_notebook_delete(
        self,
        jupyter_tools: JupyterNotebookTools,
        sample_notebook_path: str,
        mcp_context: MagicMock,
    ):
        """Test deleting a cell in a Jupyter notebook."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the edit_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Get the original number of cells
            with open(sample_notebook_path, "r") as f:
                notebook = json.load(f)
                original_cell_count = len(notebook["cells"])

            # Use the extracted edit_notebook function to delete cell at index 1
            result = await tools["edit_notebook"](
                sample_notebook_path, 1, "", mcp_context, None, "delete"
            )

            # Verify result
            assert "Successfully edited notebook" in result
            assert "Deleted code cell at position 1" in result
            tool_ctx.info.assert_called()

            # Verify the notebook was updated
            with open(sample_notebook_path, "r") as f:
                notebook = json.load(f)
                # Check cell count decreased by 1
                assert len(notebook["cells"]) == original_cell_count - 1

    @pytest.mark.asyncio
    async def test_edit_notebook_change_type(
        self,
        jupyter_tools: JupyterNotebookTools,
        sample_notebook_path: str,
        mcp_context: MagicMock,
    ):
        """Test changing a cell's type in a Jupyter notebook."""
        new_content = "# This is now a markdown cell"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the edit_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted edit_notebook function to change a code cell to markdown
            result = await tools["edit_notebook"](
                sample_notebook_path, 1, new_content, mcp_context, "markdown", "replace"
            )

            # Verify result
            assert "Successfully edited notebook" in result
            assert "Replaced cell 1" in result
            assert "changed type from code to markdown" in result
            tool_ctx.info.assert_called()

            # Verify the notebook was updated
            with open(sample_notebook_path, "r") as f:
                notebook = json.load(f)
                assert notebook["cells"][1]["source"] == new_content
                assert notebook["cells"][1]["cell_type"] == "markdown"
                # Verify code-specific fields were removed
                assert "execution_count" not in notebook["cells"][1]
                assert "outputs" not in notebook["cells"][1]

    @pytest.mark.asyncio
    async def test_edit_notebook_invalid_cell_number(
        self,
        jupyter_tools: JupyterNotebookTools,
        sample_notebook_path: str,
        mcp_context: MagicMock,
    ):
        """Test editing a notebook with an invalid cell number."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the edit_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Get the number of cells
            with open(sample_notebook_path, "r") as f:
                notebook = json.load(f)
                cell_count = len(notebook["cells"])

            # Use the extracted edit_notebook function with an out-of-bounds cell number
            result = await tools["edit_notebook"](
                sample_notebook_path,
                cell_count + 1,
                "Invalid cell",
                mcp_context,
                None,
                "replace",
            )

            # Verify result
            assert "Error: Cell number" in result
            assert "is out of bounds" in result
            tool_ctx.error.assert_called()

    @pytest.mark.asyncio
    async def test_edit_notebook_missing_cell_type_for_insert(
        self,
        jupyter_tools: JupyterNotebookTools,
        sample_notebook_path: str,
        mcp_context: MagicMock,
    ):
        """Test inserting a cell without specifying cell_type."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the edit_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted edit_notebook function with insert mode but no cell_type
            result = await tools["edit_notebook"](
                sample_notebook_path, 1, "New content", mcp_context, None, "insert"
            )

            # Verify result
            assert "Error: Cell type is required when using insert mode" in result
            tool_ctx.error.assert_called()

    @pytest.mark.asyncio
    async def test_edit_notebook_invalid_edit_mode(
        self,
        jupyter_tools: JupyterNotebookTools,
        sample_notebook_path: str,
        mcp_context: MagicMock,
    ):
        """Test editing a notebook with an invalid edit mode."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the edit_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted edit_notebook function with an invalid edit mode
            result = await tools["edit_notebook"](
                sample_notebook_path,
                1,
                "New content",
                mcp_context,
                "code",
                "invalid_mode",
            )

            # Verify result
            assert "Error: Edit mode must be replace, insert, or delete" in result
            tool_ctx.error.assert_called()

    @pytest.mark.asyncio
    async def test_edit_notebook_not_allowed(
        self,
        jupyter_tools: JupyterNotebookTools,
        mcp_context: MagicMock,
    ):
        """Test editing a notebook that is not allowed."""
        # Path outside of allowed paths
        path = "/not/allowed/notebook.ipynb"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the edit_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Use the extracted edit_notebook function
            result = await tools["edit_notebook"](
                path, 0, "New content", mcp_context, "code", "replace"
            )

            # Verify result
            assert "Error: Access denied" in result
            tool_ctx.error.assert_called()

    @pytest.mark.asyncio
    async def test_edit_notebook_insert_at_end(
        self,
        jupyter_tools: JupyterNotebookTools,
        sample_notebook_path: str,
        mcp_context: MagicMock,
    ):
        """Test inserting a cell at the end of a notebook."""
        new_content = "# New cell at end\nprint('Appended content')"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.jupyter.notebook_operations.create_tool_context",
            return_value=tool_ctx,
        ):
            # Extract the edit_notebook function
            mock_server = MagicMock()
            tools = {}

            def mock_decorator():
                def decorator(func):
                    tools[func.__name__] = func
                    return func

                return decorator

            mock_server.tool = mock_decorator
            jupyter_tools.register_tools(mock_server)

            # Get the original number of cells
            with open(sample_notebook_path, "r") as f:
                notebook = json.load(f)
                original_cell_count = len(notebook["cells"])

            # Use the extracted edit_notebook function to append a cell
            result = await tools["edit_notebook"](
                sample_notebook_path,
                original_cell_count,
                new_content,
                mcp_context,
                "code",
                "insert",
            )

            # Verify result
            assert "Successfully edited notebook" in result
            assert f"Inserted new code cell at position {original_cell_count}" in result
            tool_ctx.info.assert_called()

            # Verify the notebook was updated
            with open(sample_notebook_path, "r") as f:
                notebook = json.load(f)
                # Check cell count increased by 1
                assert len(notebook["cells"]) == original_cell_count + 1
                # Check the new cell was added at the end
                assert notebook["cells"][-1]["source"] == new_content
                assert notebook["cells"][-1]["cell_type"] == "code"
