"""Base functionality for Jupyter notebook tools.

This module provides common functionality for Jupyter notebook tools, including notebook parsing,
cell processing, and output formatting.
"""

from abc import ABC
import json
import re
from pathlib import Path
from typing import Any, final

from fastmcp import Context as MCPContext

from mcp_claude_code.tools.common.base import FileSystemTool
from mcp_claude_code.tools.common.context import ToolContext, create_tool_context


# Pattern to match ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r"\x1B\[[0-9;]*[a-zA-Z]")


# Function to clean ANSI escape codes from text
def clean_ansi_escapes(text: str) -> str:
    """Remove ANSI escape sequences from text.

    Args:
        text: Text containing ANSI escape sequences

    Returns:
        Text with ANSI escape sequences removed
    """
    return ANSI_ESCAPE_PATTERN.sub("", text)


@final
class NotebookOutputImage:
    """Representation of an image output in a notebook cell."""

    def __init__(self, image_data: str, media_type: str):
        """Initialize a notebook output image.

        Args:
            image_data: Base64-encoded image data
            media_type: Media type of the image (e.g., "image/png")
        """
        self.image_data = image_data
        self.media_type = media_type


@final
class NotebookCellOutput:
    """Representation of an output from a notebook cell."""

    def __init__(
        self,
        output_type: str,
        text: str | None = None,
        image: NotebookOutputImage | None = None,
    ):
        """Initialize a notebook cell output.

        Args:
            output_type: Type of output
            text: Text output (if any)
            image: Image output (if any)
        """
        self.output_type = output_type
        self.text = text
        self.image = image


@final
class NotebookCellSource:
    """Representation of a source cell from a notebook."""

    def __init__(
        self,
        cell_index: int,
        cell_type: str,
        source: str,
        language: str,
        execution_count: int | None = None,
        outputs: list[NotebookCellOutput] | None = None,
    ):
        """Initialize a notebook cell source.

        Args:
            cell_index: Index of the cell in the notebook
            cell_type: Type of cell (code or markdown)
            source: Source code or text of the cell
            language: Programming language of the cell
            execution_count: Execution count of the cell (if any)
            outputs: Outputs from the cell (if any)
        """
        self.cell_index = cell_index
        self.cell_type = cell_type
        self.source = source
        self.language = language
        self.execution_count = execution_count
        self.outputs = outputs or []


class JupyterBaseTool(FileSystemTool, ABC):
    """Base class for Jupyter notebook tools.

    Provides common functionality for working with Jupyter notebooks, including
    parsing, cell extraction, and output formatting.
    """

    def create_tool_context(self, ctx: MCPContext) -> ToolContext:
        """Create a tool context with the tool name.

        Args:
            ctx: MCP context

        Returns:
            Tool context
        """
        tool_ctx = create_tool_context(ctx)
        return tool_ctx

    def set_tool_context_info(self, tool_ctx: ToolContext) -> None:
        """Set the tool info on the context.

        Args:
            tool_ctx: Tool context
        """
        tool_ctx.set_tool_info(self.name)

    async def parse_notebook(
        self, file_path: Path
    ) -> tuple[dict[str, Any], list[NotebookCellSource]]:
        """Parse a Jupyter notebook file.

        Args:
            file_path: Path to the notebook file

        Returns:
            Tuple of (notebook_data, processed_cells)
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            notebook = json.loads(content)

        # Get notebook language
        language = (
            notebook.get("metadata", {}).get("language_info", {}).get("name", "python")
        )
        cells = notebook.get("cells", [])
        processed_cells = []

        for i, cell in enumerate(cells):
            cell_type = cell.get("cell_type", "code")

            # Skip if not code or markdown
            if cell_type not in ["code", "markdown"]:
                continue

            # Get source
            source = cell.get("source", "")
            if isinstance(source, list):
                source = "".join(source)

            # Get execution count for code cells
            execution_count = None
            if cell_type == "code":
                execution_count = cell.get("execution_count")

            # Process outputs for code cells
            outputs = []
            if cell_type == "code" and "outputs" in cell:
                for output in cell["outputs"]:
                    output_type = output.get("output_type", "")

                    # Process different output types
                    if output_type == "stream":
                        text = output.get("text", "")
                        if isinstance(text, list):
                            text = "".join(text)
                        outputs.append(
                            NotebookCellOutput(output_type="stream", text=text)
                        )

                    elif output_type in ["execute_result", "display_data"]:
                        # Process text output
                        text = None
                        if "data" in output and "text/plain" in output["data"]:
                            text_data = output["data"]["text/plain"]
                            if isinstance(text_data, list):
                                text = "".join(text_data)
                            else:
                                text = text_data

                        # Process image output
                        image = None
                        if "data" in output:
                            if "image/png" in output["data"]:
                                image = NotebookOutputImage(
                                    image_data=output["data"]["image/png"],
                                    media_type="image/png",
                                )
                            elif "image/jpeg" in output["data"]:
                                image = NotebookOutputImage(
                                    image_data=output["data"]["image/jpeg"],
                                    media_type="image/jpeg",
                                )

                        outputs.append(
                            NotebookCellOutput(
                                output_type=output_type, text=text, image=image
                            )
                        )

                    elif output_type == "error":
                        # Format error traceback
                        ename = output.get("ename", "")
                        evalue = output.get("evalue", "")
                        traceback = output.get("traceback", [])

                        # Handle raw text strings and lists of strings
                        if isinstance(traceback, list):
                            # Clean ANSI escape codes and join the list but preserve the formatting
                            clean_traceback = [
                                clean_ansi_escapes(line) for line in traceback
                            ]
                            traceback_text = "\n".join(clean_traceback)
                        else:
                            traceback_text = clean_ansi_escapes(str(traceback))

                        error_text = f"{ename}: {evalue}\n{traceback_text}"
                        outputs.append(
                            NotebookCellOutput(output_type="error", text=error_text)
                        )

            # Create cell object
            processed_cell = NotebookCellSource(
                cell_index=i,
                cell_type=cell_type,
                source=source,
                language=language,
                execution_count=execution_count,
                outputs=outputs,
            )

            processed_cells.append(processed_cell)

        return notebook, processed_cells

    def format_notebook_cells(self, cells: list[NotebookCellSource]) -> str:
        """Format notebook cells as a readable string.

        Args:
            cells: List of processed notebook cells

        Returns:
            Formatted string representation of the cells
        """
        result = []
        for cell in cells:
            # Format the cell header
            cell_header = f"Cell [{cell.cell_index}] {cell.cell_type}"
            if cell.execution_count is not None:
                cell_header += f" (execution_count: {cell.execution_count})"
            if cell.cell_type == "code" and cell.language != "python":
                cell_header += f" [{cell.language}]"

            # Add cell to result
            result.append(f"{cell_header}:")
            result.append(f"```{cell.language if cell.cell_type == 'code' else ''}")
            result.append(cell.source)
            result.append("```")

            # Add outputs if any
            if cell.outputs:
                result.append("Outputs:")
                for output in cell.outputs:
                    if output.output_type == "error":
                        result.append("Error:")
                        result.append("```")
                        result.append(output.text)
                        result.append("```")
                    elif output.text:
                        result.append("Output:")
                        result.append("```")
                        result.append(output.text)
                        result.append("```")
                    if output.image:
                        result.append(f"[Image output: {output.image.media_type}]")

            result.append("")  # Empty line between cells

        return "\n".join(result)
