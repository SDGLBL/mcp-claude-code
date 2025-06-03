"""Tests for Jupyter notebook tools."""

import json
import os
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_claude_code.tools.jupyter.base import JupyterBaseTool

if TYPE_CHECKING:
    from mcp_claude_code.tools.common.permissions import PermissionManager

from mcp_claude_code.tools.jupyter.notebook_edit import NoteBookEditTool
from mcp_claude_code.tools.jupyter.notebook_read import NotebookReadTool


class TestNotebookReadTool:
    """Test the NotebookReadTool class."""

    @pytest.fixture
    def notebook_read_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create a NotebookReadTool instance for testing."""
        return NotebookReadTool(permission_manager)

    @pytest.fixture
    def setup_allowed_path(
        self,
        permission_manager: "PermissionManager",
        temp_dir: str,
    ):
        """Set up an allowed path for testing."""
        permission_manager.add_allowed_path(temp_dir)
        return temp_dir

    @pytest.fixture
    def test_notebook_simple(self, setup_allowed_path: str):
        """Create a simple test notebook file."""
        notebook_path = os.path.join(setup_allowed_path, "test_notebook.ipynb")
        notebook_content = {
            "nbformat": 4,
            "nbformat_minor": 2,
            "metadata": {"language_info": {"name": "python"}},
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('Hello, World!')"],
                    "metadata": {},
                    "outputs": [
                        {
                            "output_type": "stream",
                            "name": "stdout",
                            "text": ["Hello, World!\n"],
                        }
                    ],
                    "execution_count": 1,
                },
                {
                    "cell_type": "markdown",
                    "source": [
                        "# This is a markdown cell\n",
                        "With some **bold** text.",
                    ],
                    "metadata": {},
                },
            ],
        }

        with open(notebook_path, "w", encoding="utf-8") as f:
            json.dump(notebook_content, f, indent=2)

        return notebook_path

    @pytest.fixture
    def test_notebook_complex(self, setup_allowed_path: str):
        """Create a more complex test notebook file."""
        notebook_path = os.path.join(setup_allowed_path, "complex_notebook.ipynb")
        notebook_content = {
            "nbformat": 4,
            "nbformat_minor": 2,
            "metadata": {"language_info": {"name": "python"}},
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["import pandas as pd\n", "import numpy as np"],
                    "metadata": {},
                    "outputs": [],
                    "execution_count": 1,
                },
                {
                    "cell_type": "code",
                    "source": ["data = np.array([1, 2, 3, 4, 5])\n", "print(data)"],
                    "metadata": {},
                    "outputs": [
                        {
                            "output_type": "stream",
                            "name": "stdout",
                            "text": ["[1 2 3 4 5]\n"],
                        }
                    ],
                    "execution_count": 2,
                },
                {
                    "cell_type": "code",
                    "source": ["raise ValueError('Test error')"],
                    "metadata": {},
                    "outputs": [
                        {
                            "output_type": "error",
                            "ename": "ValueError",
                            "evalue": "Test error",
                            "traceback": [
                                "\u001b[0;31m---------------------------------------------------------------------------\u001b[0m",
                                "\u001b[0;31mValueError\u001b[0m                                Traceback (most recent call last)",
                                "\u001b[0;32m<ipython-input-3-1c4d3e0f4a52>\u001b[0m in \u001b[0;36m<module>\u001b[0;34m\u001b[0m",
                                "\u001b[0;32m      1\u001b[0m \u001b[0;32mraise\u001b[0m \u001b[0mValueError\u001b[0m\u001b[0;34m(\u001b[0m\u001b[0;34m'Test error'\u001b[0m\u001b[0;34m)\u001b[0m",
                                "\u001b[0;31mValueError\u001b[0m: Test error",
                            ],
                        }
                    ],
                    "execution_count": 3,
                },
                {
                    "cell_type": "markdown",
                    "source": [
                        "## Data Analysis\n",
                        "\n",
                        "This is a markdown cell with analysis notes.",
                    ],
                    "metadata": {},
                },
            ],
        }

        with open(notebook_path, "w", encoding="utf-8") as f:
            json.dump(notebook_content, f, indent=2)

        return notebook_path

    @pytest.mark.asyncio
    async def test_read_simple_notebook(
        self,
        notebook_read_tool: NotebookReadTool,
        test_notebook_simple: str,
        mcp_context: MagicMock,
    ):
        """Test reading a simple notebook file."""
        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_read_tool.call(
                    mcp_context, notebook_path=test_notebook_simple
                )

        # Verify result contains expected content
        assert "Hello, World!" in result
        assert "Cell [0] code" in result
        assert "Cell [1] markdown" in result
        assert "This is a markdown cell" in result
        assert "execution_count: 1" in result
        assert "Output:" in result

    @pytest.mark.asyncio
    async def test_read_complex_notebook(
        self,
        notebook_read_tool: NotebookReadTool,
        test_notebook_complex: str,
        mcp_context: MagicMock,
    ):
        """Test reading a complex notebook with various cell types and outputs."""
        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_read_tool.call(
                    mcp_context, notebook_path=test_notebook_complex
                )

        # Verify result contains expected content
        assert "import pandas as pd" in result
        assert "import numpy as np" in result
        assert "[1 2 3 4 5]" in result
        assert "ValueError: Test error" in result
        assert "Data Analysis" in result
        assert "Error:" in result
        assert "execution_count: 1" in result
        assert "execution_count: 2" in result
        assert "execution_count: 3" in result

    @pytest.mark.asyncio
    async def test_read_notebook_file_not_found(
        self,
        notebook_read_tool: NotebookReadTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test reading a notebook file that doesn't exist."""
        non_existent_path = os.path.join(setup_allowed_path, "non_existent.ipynb")

        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_read_tool.call(
                    mcp_context, notebook_path=non_existent_path
                )

        # Verify error message
        assert "Error: File does not exist" in result

    @pytest.mark.asyncio
    async def test_read_notebook_invalid_extension(
        self,
        notebook_read_tool: NotebookReadTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test reading a file that is not a notebook."""
        txt_file_path = os.path.join(setup_allowed_path, "not_a_notebook.txt")
        with open(txt_file_path, "w") as f:
            f.write("This is not a notebook")

        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_read_tool.call(
                    mcp_context, notebook_path=txt_file_path
                )

        # Verify error message
        assert "Error: File is not a Jupyter notebook" in result

    @pytest.mark.asyncio
    async def test_read_notebook_invalid_json(
        self,
        notebook_read_tool: NotebookReadTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test reading a notebook file with invalid JSON."""
        invalid_notebook_path = os.path.join(setup_allowed_path, "invalid.ipynb")
        with open(invalid_notebook_path, "w") as f:
            f.write("This is not valid JSON content")

        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_read_tool.call(
                    mcp_context, notebook_path=invalid_notebook_path
                )

        # Verify error message
        assert "Error: Invalid notebook format" in result

    @pytest.mark.asyncio
    async def test_read_notebook_not_allowed_path(
        self,
        notebook_read_tool: NotebookReadTool,
        mcp_context: MagicMock,
    ):
        """Test reading a notebook file from a path that is not allowed."""
        # Path outside of allowed paths
        path = "/not/allowed/notebook.ipynb"

        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_read_tool.call(mcp_context, notebook_path=path)

        # Verify result
        assert "Error: Access denied" in result


class TestNoteBookEditTool:
    """Test the NoteBookEditTool class."""

    @pytest.fixture
    def notebook_edit_tool(
        self,
        permission_manager: "PermissionManager",
    ):
        """Create a NoteBookEditTool instance for testing."""
        return NoteBookEditTool(permission_manager)

    @pytest.fixture
    def setup_allowed_path(
        self,
        permission_manager: "PermissionManager",
        temp_dir: str,
    ):
        """Set up an allowed path for testing."""
        permission_manager.add_allowed_path(temp_dir)
        return temp_dir

    @pytest.fixture
    def test_notebook_editable(self, setup_allowed_path: str):
        """Create a test notebook file for editing."""
        notebook_path = os.path.join(setup_allowed_path, "editable_notebook.ipynb")
        notebook_content = {
            "nbformat": 4,
            "nbformat_minor": 2,
            "metadata": {"language_info": {"name": "python"}},
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('Original cell')"],
                    "metadata": {},
                    "outputs": [
                        {
                            "output_type": "stream",
                            "name": "stdout",
                            "text": ["Original cell\n"],
                        }
                    ],
                    "execution_count": 1,
                },
                {
                    "cell_type": "markdown",
                    "source": ["# Original markdown"],
                    "metadata": {},
                },
            ],
        }

        with open(notebook_path, "w", encoding="utf-8") as f:
            json.dump(notebook_content, f, indent=2)

        return notebook_path

    @pytest.mark.asyncio
    async def test_edit_notebook_replace_cell(
        self,
        notebook_edit_tool: NoteBookEditTool,
        test_notebook_editable: str,
        mcp_context: MagicMock,
    ):
        """Test replacing a cell in a notebook."""
        # Mock context calls
        tool_ctx = AsyncMock()

        new_source = "print('Modified cell')"

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=test_notebook_editable,
                    cell_number=0,
                    new_source=new_source,
                    edit_mode="replace",
                )

        # Verify success message
        assert "Successfully edited notebook" in result
        assert "Replaced cell 0" in result

        # Verify the file was modified
        with open(test_notebook_editable, "r", encoding="utf-8") as f:
            notebook = json.load(f)
            assert notebook["cells"][0]["source"] == new_source
            assert notebook["cells"][0]["cell_type"] == "code"  # Should remain code
            assert notebook["cells"][0]["outputs"] == []  # Outputs should be reset

    @pytest.mark.asyncio
    async def test_edit_notebook_replace_with_type_change(
        self,
        notebook_edit_tool: NoteBookEditTool,
        test_notebook_editable: str,
        mcp_context: MagicMock,
    ):
        """Test replacing a cell and changing its type."""
        # Mock context calls
        tool_ctx = AsyncMock()

        new_source = "# New markdown content"

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=test_notebook_editable,
                    cell_number=0,
                    new_source=new_source,
                    cell_type="markdown",
                    edit_mode="replace",
                )

        # Verify success message
        assert "Successfully edited notebook" in result
        assert "changed type from code to markdown" in result

        # Verify the file was modified
        with open(test_notebook_editable, "r", encoding="utf-8") as f:
            notebook = json.load(f)
            assert notebook["cells"][0]["source"] == new_source
            assert notebook["cells"][0]["cell_type"] == "markdown"
            # Should not have code-specific fields
            assert "outputs" not in notebook["cells"][0]
            assert "execution_count" not in notebook["cells"][0]

    @pytest.mark.asyncio
    async def test_edit_notebook_insert_cell(
        self,
        notebook_edit_tool: NoteBookEditTool,
        test_notebook_editable: str,
        mcp_context: MagicMock,
    ):
        """Test inserting a new cell in a notebook."""
        # Mock context calls
        tool_ctx = AsyncMock()

        new_source = "print('Inserted cell')"

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=test_notebook_editable,
                    cell_number=1,
                    new_source=new_source,
                    cell_type="code",
                    edit_mode="insert",
                )

        # Verify success message
        assert "Successfully edited notebook" in result
        assert "Inserted new code cell at position 1" in result

        # Verify the file was modified
        with open(test_notebook_editable, "r", encoding="utf-8") as f:
            notebook = json.load(f)
            assert len(notebook["cells"]) == 3  # Should have 3 cells now
            assert notebook["cells"][1]["source"] == new_source
            assert notebook["cells"][1]["cell_type"] == "code"
            assert notebook["cells"][1]["outputs"] == []
            assert notebook["cells"][1]["execution_count"] is None

    @pytest.mark.asyncio
    async def test_edit_notebook_insert_markdown_cell(
        self,
        notebook_edit_tool: NoteBookEditTool,
        test_notebook_editable: str,
        mcp_context: MagicMock,
    ):
        """Test inserting a markdown cell in a notebook."""
        # Mock context calls
        tool_ctx = AsyncMock()

        new_source = "## Inserted markdown header"

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=test_notebook_editable,
                    cell_number=0,
                    new_source=new_source,
                    cell_type="markdown",
                    edit_mode="insert",
                )

        # Verify success message
        assert "Successfully edited notebook" in result
        assert "Inserted new markdown cell at position 0" in result

        # Verify the file was modified
        with open(test_notebook_editable, "r", encoding="utf-8") as f:
            notebook = json.load(f)
            assert len(notebook["cells"]) == 3  # Should have 3 cells now
            assert notebook["cells"][0]["source"] == new_source
            assert notebook["cells"][0]["cell_type"] == "markdown"
            # Should not have code-specific fields
            assert "outputs" not in notebook["cells"][0]
            assert "execution_count" not in notebook["cells"][0]

    @pytest.mark.asyncio
    async def test_edit_notebook_delete_cell(
        self,
        notebook_edit_tool: NoteBookEditTool,
        test_notebook_editable: str,
        mcp_context: MagicMock,
    ):
        """Test deleting a cell from a notebook."""
        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=test_notebook_editable,
                    cell_number=0,
                    new_source="",  # Not used for delete
                    edit_mode="delete",
                )

        # Verify success message
        assert "Successfully edited notebook" in result
        assert "Deleted code cell at position 0" in result

        # Verify the file was modified
        with open(test_notebook_editable, "r", encoding="utf-8") as f:
            notebook = json.load(f)
            assert len(notebook["cells"]) == 1  # Should have 1 cell now
            # The remaining cell should be the markdown cell
            assert notebook["cells"][0]["cell_type"] == "markdown"
            source = notebook["cells"][0]["source"]
            if isinstance(source, list):
                source = "".join(source)
            assert "Original markdown" in source

    @pytest.mark.asyncio
    async def test_edit_notebook_invalid_cell_number(
        self,
        notebook_edit_tool: NoteBookEditTool,
        test_notebook_editable: str,
        mcp_context: MagicMock,
    ):
        """Test editing with an invalid cell number."""
        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=test_notebook_editable,
                    cell_number=10,  # Out of bounds
                    new_source="test",
                    edit_mode="replace",
                )

        # Verify error message
        assert "Error: Cell number 10 is out of bounds" in result

    @pytest.mark.asyncio
    async def test_edit_notebook_insert_without_cell_type(
        self,
        notebook_edit_tool: NoteBookEditTool,
        test_notebook_editable: str,
        mcp_context: MagicMock,
    ):
        """Test inserting without specifying cell type."""
        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=test_notebook_editable,
                    cell_number=0,
                    new_source="test",
                    edit_mode="insert",
                )

        # Verify error message
        assert "Error: Cell type is required when using insert mode" in result

    @pytest.mark.asyncio
    async def test_edit_notebook_invalid_edit_mode(
        self,
        notebook_edit_tool: NoteBookEditTool,
        test_notebook_editable: str,
        mcp_context: MagicMock,
    ):
        """Test editing with invalid edit mode."""
        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=test_notebook_editable,
                    cell_number=0,
                    new_source="test",
                    edit_mode="invalid_mode",
                )

        # Verify error message
        assert "Error: Edit mode must be replace, insert, or delete" in result

    @pytest.mark.asyncio
    async def test_edit_notebook_file_not_found(
        self,
        notebook_edit_tool: NoteBookEditTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test editing a notebook file that doesn't exist."""
        non_existent_path = os.path.join(setup_allowed_path, "non_existent.ipynb")

        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=non_existent_path,
                    cell_number=0,
                    new_source="test",
                )

        # Verify error message
        assert "Error: File does not exist" in result

    @pytest.mark.asyncio
    async def test_edit_notebook_not_allowed_path(
        self,
        notebook_edit_tool: NoteBookEditTool,
        mcp_context: MagicMock,
    ):
        """Test editing a notebook file from a path that is not allowed."""
        # Path outside of allowed paths
        path = "/not/allowed/notebook.ipynb"

        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=path,
                    cell_number=0,
                    new_source="test",
                )

        # Verify result
        assert "Error: Access denied" in result

    @pytest.mark.asyncio
    async def test_edit_notebook_invalid_json(
        self,
        notebook_edit_tool: NoteBookEditTool,
        setup_allowed_path: str,
        mcp_context: MagicMock,
    ):
        """Test editing a notebook file with invalid JSON."""
        invalid_notebook_path = os.path.join(setup_allowed_path, "invalid.ipynb")
        with open(invalid_notebook_path, "w") as f:
            f.write("This is not valid JSON content")

        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=invalid_notebook_path,
                    cell_number=0,
                    new_source="test",
                )

        # Verify error message
        assert "Error: Invalid notebook format" in result

    @pytest.mark.asyncio
    async def test_edit_notebook_insert_out_of_bounds(
        self,
        notebook_edit_tool: NoteBookEditTool,
        test_notebook_editable: str,
        mcp_context: MagicMock,
    ):
        """Test inserting at a position that's out of bounds."""
        # Mock context calls
        tool_ctx = AsyncMock()

        # Mock the base class methods
        with patch.object(JupyterBaseTool, "set_tool_context_info"):
            with patch.object(
                JupyterBaseTool, "create_tool_context", return_value=tool_ctx
            ):
                result = await notebook_edit_tool.call(
                    mcp_context,
                    notebook_path=test_notebook_editable,
                    cell_number=10,  # Out of bounds for insert
                    new_source="test",
                    cell_type="code",
                    edit_mode="insert",
                )

        # Verify error message
        assert "Error: Cell number 10 is out of bounds for insert" in result
