"""Tests for Jupyter base functionality and package initialization."""

import json
import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from mcp_claude_code.tools.common.permissions import PermissionManager

from mcp_claude_code.tools.jupyter import (
    get_jupyter_tools,
    get_read_only_jupyter_tools,
    register_jupyter_tools,
)
from mcp_claude_code.tools.jupyter.base import (
    NotebookCellOutput,
    NotebookCellSource,
    NotebookOutputImage,
    clean_ansi_escapes,
)
from mcp_claude_code.tools.jupyter.notebook_edit import NoteBookEditTool
from mcp_claude_code.tools.jupyter.notebook_read import NotebookReadTool


class TestJupyterPackage:
    """Test the Jupyter package initialization and tool creation."""

    def test_get_read_only_jupyter_tools(
        self,
        permission_manager: "PermissionManager",
    ):
        """Test getting read-only Jupyter tools."""
        tools = get_read_only_jupyter_tools(permission_manager)

        assert len(tools) == 1
        assert isinstance(tools[0], NotebookReadTool)

    def test_get_jupyter_tools(
        self,
        permission_manager: "PermissionManager",
    ):
        """Test getting all Jupyter tools."""
        tools = get_jupyter_tools(permission_manager)

        assert len(tools) == 2
        tool_types = [type(tool) for tool in tools]
        assert NotebookReadTool in tool_types
        assert NoteBookEditTool in tool_types

    def test_register_jupyter_tools(
        self,
        permission_manager: "PermissionManager",
    ):
        """Test registering Jupyter tools with MCP server."""
        # Mock MCP server
        mock_server = MagicMock()

        tools = register_jupyter_tools(mock_server, permission_manager)

        assert len(tools) == 2
        tool_types = [type(tool) for tool in tools]
        assert NotebookReadTool in tool_types
        assert NoteBookEditTool in tool_types


class TestNotebookDataClasses:
    """Test the notebook data classes and helper functions."""

    def test_notebook_output_image(self):
        """Test NotebookOutputImage class."""
        image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQIHWNk"
        media_type = "image/png"

        image = NotebookOutputImage(image_data, media_type)

        assert image.image_data == image_data
        assert image.media_type == media_type

    def test_notebook_cell_output_text(self):
        """Test NotebookCellOutput with text output."""
        output_type = "stream"
        text = "Hello, World!"

        output = NotebookCellOutput(output_type, text=text)

        assert output.output_type == output_type
        assert output.text == text
        assert output.image is None

    def test_notebook_cell_output_image(self):
        """Test NotebookCellOutput with image output."""
        output_type = "display_data"
        image = NotebookOutputImage("base64data", "image/png")

        output = NotebookCellOutput(output_type, image=image)

        assert output.output_type == output_type
        assert output.text is None
        assert output.image == image

    def test_notebook_cell_output_both(self):
        """Test NotebookCellOutput with both text and image."""
        output_type = "execute_result"
        text = "Result text"
        image = NotebookOutputImage("base64data", "image/jpeg")

        output = NotebookCellOutput(output_type, text=text, image=image)

        assert output.output_type == output_type
        assert output.text == text
        assert output.image == image

    def test_notebook_cell_source_code(self):
        """Test NotebookCellSource for code cell."""
        cell_index = 0
        cell_type = "code"
        source = "print('Hello')"
        language = "python"
        execution_count = 1
        outputs = [NotebookCellOutput("stream", text="Hello\n")]

        cell = NotebookCellSource(
            cell_index, cell_type, source, language, execution_count, outputs
        )

        assert cell.cell_index == cell_index
        assert cell.cell_type == cell_type
        assert cell.source == source
        assert cell.language == language
        assert cell.execution_count == execution_count
        assert cell.outputs == outputs

    def test_notebook_cell_source_markdown(self):
        """Test NotebookCellSource for markdown cell."""
        cell_index = 1
        cell_type = "markdown"
        source = "# Header"
        language = "python"

        cell = NotebookCellSource(cell_index, cell_type, source, language)

        assert cell.cell_index == cell_index
        assert cell.cell_type == cell_type
        assert cell.source == source
        assert cell.language == language
        assert cell.execution_count is None
        assert cell.outputs == []

    def test_notebook_cell_source_default_outputs(self):
        """Test NotebookCellSource with default outputs."""
        cell = NotebookCellSource(0, "code", "test", "python")

        assert cell.outputs == []

    def test_clean_ansi_escapes(self):
        """Test cleaning ANSI escape sequences."""
        # Text with ANSI escape sequences
        text_with_ansi = "\u001b[0;31mRed text\u001b[0m\u001b[1mBold text\u001b[0m"
        expected = "Red textBold text"

        result = clean_ansi_escapes(text_with_ansi)

        assert result == expected

    def test_clean_ansi_escapes_no_ansi(self):
        """Test cleaning text without ANSI escape sequences."""
        text_without_ansi = "Regular text"

        result = clean_ansi_escapes(text_without_ansi)

        assert result == text_without_ansi

    def test_clean_ansi_escapes_empty(self):
        """Test cleaning empty text."""
        result = clean_ansi_escapes("")

        assert result == ""


class TestJupyterBaseFunctionality:
    """Test the base Jupyter functionality."""

    @pytest.fixture
    def test_notebook_for_parsing(self, temp_dir: str):
        """Create a test notebook for parsing."""
        notebook_path = os.path.join(temp_dir, "parse_test.ipynb")
        notebook_content = {
            "nbformat": 4,
            "nbformat_minor": 2,
            "metadata": {"language_info": {"name": "python"}},
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["import pandas as pd\n", "print('Hello')"],
                    "metadata": {},
                    "outputs": [
                        {
                            "output_type": "stream",
                            "name": "stdout",
                            "text": ["Hello\n"],
                        },
                        {
                            "output_type": "execute_result",
                            "execution_count": 1,
                            "data": {"text/plain": "42"},
                        },
                        {
                            "output_type": "display_data",
                            "data": {
                                "image/png": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQIHWNk",
                                "text/plain": "Figure",
                            },
                        },
                        {
                            "output_type": "error",
                            "ename": "ValueError",
                            "evalue": "Test error",
                            "traceback": [
                                "\u001b[0;31m---------------------------------------------------------------------------\u001b[0m",
                                "\u001b[0;31mValueError\u001b[0m: Test error",
                            ],
                        },
                    ],
                    "execution_count": 1,
                },
                {
                    "cell_type": "markdown",
                    "source": "# Test Header\n\nSome markdown content.",
                    "metadata": {},
                },
                {
                    "cell_type": "raw",  # This should be skipped
                    "source": "Raw cell content",
                    "metadata": {},
                },
            ],
        }

        with open(notebook_path, "w", encoding="utf-8") as f:
            json.dump(notebook_content, f, indent=2)

        return notebook_path

    @pytest.mark.asyncio
    async def test_parse_notebook(
        self,
        test_notebook_for_parsing: str,
        permission_manager: "PermissionManager",
    ):
        """Test parsing a notebook file."""
        # Create a tool instance to test the base functionality
        tool = NotebookReadTool(permission_manager)

        from pathlib import Path

        notebook_data, processed_cells = await tool.parse_notebook(
            Path(test_notebook_for_parsing)
        )

        # Verify notebook data
        assert "nbformat" in notebook_data
        assert notebook_data["nbformat"] == 4

        # Verify processed cells (should only include code and markdown, not raw)
        assert len(processed_cells) == 2

        # Check first cell (code)
        code_cell = processed_cells[0]
        assert code_cell.cell_index == 0
        assert code_cell.cell_type == "code"
        assert "import pandas as pd" in code_cell.source
        assert "print('Hello')" in code_cell.source
        assert code_cell.language == "python"
        assert code_cell.execution_count == 1
        assert (
            len(code_cell.outputs) == 4
        )  # stream, execute_result, display_data, error

        # Check outputs
        stream_output = code_cell.outputs[0]
        assert stream_output.output_type == "stream"
        assert stream_output.text == "Hello\n"

        execute_result_output = code_cell.outputs[1]
        assert execute_result_output.output_type == "execute_result"
        assert execute_result_output.text == "42"

        display_data_output = code_cell.outputs[2]
        assert display_data_output.output_type == "display_data"
        assert display_data_output.text == "Figure"
        assert display_data_output.image is not None
        assert display_data_output.image.media_type == "image/png"

        error_output = code_cell.outputs[3]
        assert error_output.output_type == "error"
        assert "ValueError: Test error" in error_output.text
        # ANSI escapes should be cleaned
        assert "\u001b[0;31m" not in error_output.text

        # Check second cell (markdown)
        markdown_cell = processed_cells[1]
        assert markdown_cell.cell_index == 1
        assert markdown_cell.cell_type == "markdown"
        assert "# Test Header" in markdown_cell.source
        assert markdown_cell.execution_count is None
        assert len(markdown_cell.outputs) == 0

    def test_format_notebook_cells(
        self,
        permission_manager: "PermissionManager",
    ):
        """Test formatting notebook cells for display."""
        # Create a tool instance to test the base functionality
        tool = NotebookReadTool(permission_manager)

        # Create test cells
        cells = [
            NotebookCellSource(
                cell_index=0,
                cell_type="code",
                source="print('Hello')",
                language="python",
                execution_count=1,
                outputs=[
                    NotebookCellOutput("stream", text="Hello\n"),
                    NotebookCellOutput("error", text="ValueError: Test error"),
                ],
            ),
            NotebookCellSource(
                cell_index=1, cell_type="markdown", source="# Header", language="python"
            ),
        ]

        result = tool.format_notebook_cells(cells)

        # Verify format
        assert "Cell [0] code (execution_count: 1):" in result
        assert "```python" in result
        assert "print('Hello')" in result
        assert "Outputs:" in result
        assert "Output:" in result
        assert "Error:" in result
        assert "Hello\n" in result
        assert "ValueError: Test error" in result

        assert "Cell [1] markdown:" in result
        assert "# Header" in result

    def test_format_notebook_cells_with_image(
        self,
        permission_manager: "PermissionManager",
    ):
        """Test formatting notebook cells with image outputs."""
        # Create a tool instance to test the base functionality
        tool = NotebookReadTool(permission_manager)

        # Create test cell with image output
        image = NotebookOutputImage("base64data", "image/png")
        cells = [
            NotebookCellSource(
                cell_index=0,
                cell_type="code",
                source="plt.plot([1, 2, 3])",
                language="python",
                execution_count=1,
                outputs=[
                    NotebookCellOutput("display_data", text="Figure", image=image)
                ],
            )
        ]

        result = tool.format_notebook_cells(cells)

        # Verify format includes image info
        assert "[Image output: image/png]" in result
        assert "Figure" in result

    def test_format_notebook_cells_non_python(
        self,
        permission_manager: "PermissionManager",
    ):
        """Test formatting notebook cells for non-Python language."""
        # Create a tool instance to test the base functionality
        tool = NotebookReadTool(permission_manager)

        # Create test cell with R language
        cells = [
            NotebookCellSource(
                cell_index=0,
                cell_type="code",
                source="print('Hello from R')",
                language="r",
                execution_count=1,
            )
        ]

        result = tool.format_notebook_cells(cells)

        # Verify format includes language info
        assert "Cell [0] code (execution_count: 1) [r]:" in result
        assert "```r" in result
