"""Jupyter notebook operations tools for MCP Claude Code.

This module provides tools for reading and editing Jupyter notebook (.ipynb) files.
It supports reading notebook cells with their outputs and modifying notebook contents.
"""

import json
import re
from pathlib import Path
from typing import Any, final, Literal

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.common.context import DocumentContext, create_tool_context
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.common.validation import validate_path_parameter


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


# Type definitions for Jupyter notebooks based on the nbformat spec
CellType = Literal["code", "markdown"]
OutputType = Literal["stream", "display_data", "execute_result", "error"]
EditMode = Literal["replace", "insert", "delete"]


# Define a structure for notebook cell outputs
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
        output_type: OutputType,
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
        cell_type: CellType,
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


@final
class JupyterNotebookTools:
    """Tools for working with Jupyter notebooks."""

    def __init__(
        self, document_context: DocumentContext, permission_manager: PermissionManager
    ) -> None:
        """Initialize notebook tools.

        Args:
            document_context: Document context for tracking file contents
            permission_manager: Permission manager for access control
        """
        self.document_context: DocumentContext = document_context
        self.permission_manager: PermissionManager = permission_manager

    def register_tools(self, mcp_server: FastMCP) -> None:
        """Register jupyter notebook tools with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """

        @mcp_server.tool()
        async def read_notebook(path: str, ctx: MCPContext) -> str:
            """Extract and read source code from all cells in a Jupyter notebook.

            Reads a Jupyter notebook (.ipynb file) and returns all of the cells with
            their outputs. Jupyter notebooks are interactive documents that combine
            code, text, and visualizations, commonly used for data analysis and
            scientific computing.

            Args:
                path: Absolute path to the notebook file (must be absolute, not relative)

            Returns:
                Formatted content of all notebook cells with their outputs
            """
            tool_ctx = create_tool_context(ctx)
            tool_ctx.set_tool_info("read_notebook")

            # Validate path parameter
            path_validation = validate_path_parameter(path)
            if path_validation.is_error:
                await tool_ctx.error(path_validation.error_message)
                return f"Error: {path_validation.error_message}"

            await tool_ctx.info(f"Reading notebook: {path}")

            # Check if path is allowed to be read
            if not self.permission_manager.is_path_allowed(path):
                await tool_ctx.error(
                    f"Access denied - path outside allowed directories: {path}"
                )
                return (
                    f"Error: Access denied - path outside allowed directories: {path}"
                )

            try:
                file_path = Path(path)

                if not file_path.exists():
                    await tool_ctx.error(f"File does not exist: {path}")
                    return f"Error: File does not exist: {path}"

                if not file_path.is_file():
                    await tool_ctx.error(f"Path is not a file: {path}")
                    return f"Error: Path is not a file: {path}"

                # Check file extension
                if file_path.suffix.lower() != ".ipynb":
                    await tool_ctx.error(f"File is not a Jupyter notebook: {path}")
                    return f"Error: File is not a Jupyter notebook: {path}"

                # Read and parse the notebook
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        notebook = json.loads(content)
                except json.JSONDecodeError:
                    await tool_ctx.error(f"Invalid notebook format: {path}")
                    return f"Error: Invalid notebook format: {path}"
                except UnicodeDecodeError:
                    await tool_ctx.error(f"Cannot read notebook file: {path}")
                    return f"Error: Cannot read notebook file: {path}"

                # Add to document context
                self.document_context.add_document(path, content)

                # Process notebook cells
                # Get notebook language
                language = (
                    notebook.get("metadata", {})
                    .get("language_info", {})
                    .get("name", "python")
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
                                    NotebookCellOutput(
                                        output_type="error", text=error_text
                                    )
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

                # Format the notebook content as a readable string
                result = []
                for cell in processed_cells:
                    # Format the cell header
                    cell_header = f"Cell [{cell.cell_index}] {cell.cell_type}"
                    if cell.execution_count is not None:
                        cell_header += f" (execution_count: {cell.execution_count})"
                    if cell.cell_type == "code" and cell.language != "python":
                        cell_header += f" [{cell.language}]"

                    # Add cell to result
                    result.append(f"{cell_header}:")
                    result.append(
                        f"```{cell.language if cell.cell_type == 'code' else ''}"
                    )
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
                                result.append(
                                    f"[Image output: {output.image.media_type}]"
                                )

                    result.append("")  # Empty line between cells

                await tool_ctx.info(
                    f"Successfully read notebook: {path} ({len(processed_cells)} cells)"
                )
                return "\n".join(result)
            except Exception as e:
                await tool_ctx.error(f"Error reading notebook: {str(e)}")
                return f"Error reading notebook: {str(e)}"

        @mcp_server.tool()
        async def edit_notebook(
            path: str,
            cell_number: int,
            new_source: str,
            ctx: MCPContext,
            cell_type: CellType | None = None,
            edit_mode: EditMode = "replace",
        ) -> str:
            """Edit a specific cell in a Jupyter notebook.

            Enables editing, inserting, or deleting cells in a Jupyter notebook (.ipynb file).
            In replace mode, the specified cell's source is updated with the new content.
            In insert mode, a new cell is added at the specified index.
            In delete mode, the specified cell is removed.

            Args:
                path: Absolute path to the notebook file (must be absolute, not relative)
                cell_number: Zero-based index of the cell to edit
                new_source: New source code or text for the cell (ignored in delete mode)
                cell_type: Type of cell (code or markdown), default is to keep existing type
                edit_mode: Type of edit operation (replace, insert, delete), default is replace

            Returns:
                Result of the edit operation with details on changes made
            """
            tool_ctx = create_tool_context(ctx)
            tool_ctx.set_tool_info("edit_notebook")

            # Validate path parameter
            path_validation = validate_path_parameter(path)
            if path_validation.is_error:
                await tool_ctx.error(path_validation.error_message)
                return f"Error: {path_validation.error_message}"

            # Validate cell_number
            if cell_number < 0:
                await tool_ctx.error("Cell number must be non-negative")
                return "Error: Cell number must be non-negative"

            # Validate edit_mode
            if edit_mode not in ["replace", "insert", "delete"]:
                await tool_ctx.error("Edit mode must be replace, insert, or delete")
                return "Error: Edit mode must be replace, insert, or delete"

            # In insert mode, cell_type is required
            if edit_mode == "insert" and cell_type is None:
                await tool_ctx.error("Cell type is required when using insert mode")
                return "Error: Cell type is required when using insert mode"

            # Don't validate new_source for delete mode
            if edit_mode != "delete" and not new_source:
                await tool_ctx.error(
                    "New source is required for replace or insert operations"
                )
                return "Error: New source is required for replace or insert operations"

            await tool_ctx.info(
                f"Editing notebook: {path} (cell: {cell_number}, mode: {edit_mode})"
            )

            # Check if path is allowed
            if not self.permission_manager.is_path_allowed(path):
                await tool_ctx.error(
                    f"Access denied - path outside allowed directories: {path}"
                )
                return (
                    f"Error: Access denied - path outside allowed directories: {path}"
                )

            try:
                file_path = Path(path)

                if not file_path.exists():
                    await tool_ctx.error(f"File does not exist: {path}")
                    return f"Error: File does not exist: {path}"

                if not file_path.is_file():
                    await tool_ctx.error(f"Path is not a file: {path}")
                    return f"Error: Path is not a file: {path}"

                # Check file extension
                if file_path.suffix.lower() != ".ipynb":
                    await tool_ctx.error(f"File is not a Jupyter notebook: {path}")
                    return f"Error: File is not a Jupyter notebook: {path}"

                # Read and parse the notebook
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        notebook = json.loads(content)
                except json.JSONDecodeError:
                    await tool_ctx.error(f"Invalid notebook format: {path}")
                    return f"Error: Invalid notebook format: {path}"
                except UnicodeDecodeError:
                    await tool_ctx.error(f"Cannot read notebook file: {path}")
                    return f"Error: Cannot read notebook file: {path}"

                # Check cell_number is valid
                cells = notebook.get("cells", [])

                if edit_mode == "insert":
                    if cell_number > len(cells):
                        await tool_ctx.error(
                            f"Cell number {cell_number} is out of bounds for insert (max: {len(cells)})"
                        )
                        return f"Error: Cell number {cell_number} is out of bounds for insert (max: {len(cells)})"
                else:  # replace or delete
                    if cell_number >= len(cells):
                        await tool_ctx.error(
                            f"Cell number {cell_number} is out of bounds (max: {len(cells) - 1})"
                        )
                        return f"Error: Cell number {cell_number} is out of bounds (max: {len(cells) - 1})"

                # Get notebook language (needed for context but not directly used in this block)
                _ = (
                    notebook.get("metadata", {})
                    .get("language_info", {})
                    .get("name", "python")
                )

                # Perform the requested operation
                if edit_mode == "replace":
                    # Get the target cell
                    target_cell = cells[cell_number]

                    # Store previous contents for reporting
                    old_type = target_cell.get("cell_type", "code")
                    old_source = target_cell.get("source", "")
                    if isinstance(old_source, list):
                        old_source = "".join(old_source)

                    # Update source
                    target_cell["source"] = new_source

                    # Update type if specified
                    if cell_type is not None:
                        target_cell["cell_type"] = cell_type

                    # If changing to markdown, remove code-specific fields
                    if cell_type == "markdown":
                        if "outputs" in target_cell:
                            del target_cell["outputs"]
                        if "execution_count" in target_cell:
                            del target_cell["execution_count"]

                    # If code cell, reset execution
                    if target_cell["cell_type"] == "code":
                        target_cell["outputs"] = []
                        target_cell["execution_count"] = None

                    change_description = f"Replaced cell {cell_number}"
                    if cell_type is not None and cell_type != old_type:
                        change_description += (
                            f" (changed type from {old_type} to {cell_type})"
                        )

                elif edit_mode == "insert":
                    # Create new cell
                    new_cell: dict[str, Any] = {
                        "cell_type": cell_type,
                        "source": new_source,
                        "metadata": {},
                    }

                    # Add code-specific fields
                    if cell_type == "code":
                        new_cell["outputs"] = []
                        new_cell["execution_count"] = None

                    # Insert the cell
                    cells.insert(cell_number, new_cell)
                    change_description = (
                        f"Inserted new {cell_type} cell at position {cell_number}"
                    )

                else:  # delete
                    # Store deleted cell info for reporting
                    deleted_cell = cells[cell_number]
                    deleted_type = deleted_cell.get("cell_type", "code")

                    # Remove the cell
                    del cells[cell_number]
                    change_description = (
                        f"Deleted {deleted_type} cell at position {cell_number}"
                    )

                # Write the updated notebook back to file
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(notebook, f, indent=1)

                # Update document context
                updated_content = json.dumps(notebook, indent=1)
                self.document_context.update_document(path, updated_content)

                await tool_ctx.info(
                    f"Successfully edited notebook: {path} - {change_description}"
                )
                return f"Successfully edited notebook: {path} - {change_description}"
            except Exception as e:
                await tool_ctx.error(f"Error editing notebook: {str(e)}")
                return f"Error editing notebook: {str(e)}"
