"""Edit notebook tool implementation.

This module provides the notebook_edit tool for editing Jupyter notebook files.
Converted to FastMCP v2 function-based pattern.
"""

import json
from pathlib import Path
from typing import Any, Literal

from fastmcp import Context as MCPContext

from mcp_claude_code.tools.common.base import is_path_allowed
from mcp_claude_code.tools.common.context import create_tool_context


async def notebook_edit(
    notebook_path: str,
    cell_number: int,
    new_source: str,
    ctx: MCPContext,
    cell_type: Literal["code", "markdown"] | None = None,
    edit_mode: Literal["replace", "insert", "delete"] = "replace",
) -> str:
    """Completely replaces the contents of a specific cell in a Jupyter notebook (.ipynb file) with new source.

    Jupyter notebooks are interactive documents that combine code, text, and visualizations,
    commonly used for data analysis and scientific computing. The notebook_path parameter
    must be an absolute path, not a relative path. The cell_number is 0-indexed.
    Use edit_mode=insert to add a new cell at the index specified by cell_number.
    Use edit_mode=delete to delete the cell at the index specified by cell_number.

    Args:
        notebook_path: The absolute path to the Jupyter notebook file to edit (must be absolute, not relative)
        cell_number: The index of the cell to edit (0-based)
        new_source: The new source for the cell
        ctx: MCP context
        cell_type: The type of the cell (code or markdown). If not specified, it defaults to the current cell type. If using edit_mode=insert, this is required.
        edit_mode: The type of edit to make (replace, insert, delete). Defaults to replace.

    Returns:
        Success message with details of the edit operation

    Raises:
        ValueError: If parameters are invalid or the file is not a notebook
        FileNotFoundError: If the notebook file does not exist
        PermissionError: If access to the file is denied
    """
    # Create tool context
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("notebook_edit")

    # Validate cell_number
    if cell_number < 0:
        raise ValueError("Cell number must be non-negative")

    # In insert mode, cell_type is required
    if edit_mode == "insert" and cell_type is None:
        raise ValueError("Cell type is required when using insert mode")

    # Don't validate new_source for delete mode
    if edit_mode != "delete" and not new_source:
        raise ValueError("New source is required for replace or insert operations")

    # Validate and resolve path
    path = Path(notebook_path).resolve()

    # Check permissions
    if not is_path_allowed(path, tool_ctx):
        raise PermissionError(f"Access denied to path: {path}")

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"Notebook file not found: {path}")

    # Check if it's a file (not directory)
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Ensure it's a notebook file
    if path.suffix != ".ipynb":
        raise ValueError(f"File must be a Jupyter notebook (.ipynb): {path}")

    await tool_ctx.info(
        f"Editing notebook: {notebook_path} (cell: {cell_number}, mode: {edit_mode})"
    )

    try:
        # Read and parse the notebook
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            notebook = json.loads(content)

        # Check cell_number is valid
        cells = notebook.get("cells", [])

        if edit_mode == "insert":
            if cell_number > len(cells):
                raise ValueError(
                    f"Cell number {cell_number} is out of bounds for insert (max: {len(cells)})"
                )
        else:  # replace or delete
            if cell_number >= len(cells):
                raise ValueError(
                    f"Cell number {cell_number} is out of bounds (max: {len(cells) - 1})"
                )

        # Perform the requested operation
        if edit_mode == "replace":
            # Get the target cell
            target_cell = cells[cell_number]

            # Store previous contents for reporting
            old_type = target_cell.get("cell_type", "code")
            old_source = target_cell.get("source", "")

            # Fix for old_source which might be a list of strings
            if isinstance(old_source, list):
                old_source = "".join([str(item) for item in old_source])

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
                change_description += f" (changed type from {old_type} to {cell_type})"

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
        with open(path, "w", encoding="utf-8") as f:
            json.dump(notebook, f, indent=1)

        # Update document context
        updated_content = json.dumps(notebook, indent=1)
        tool_ctx.document_context.update_file_content(str(path), updated_content)

        success_message = (
            f"Successfully edited notebook: {notebook_path} - {change_description}"
        )
        await tool_ctx.info(success_message)
        return success_message

    except json.JSONDecodeError as e:
        await tool_ctx.log_error(f"Invalid JSON in notebook file: {e}")
        raise ValueError(f"Invalid JSON in notebook file: {e}")
    except Exception as e:
        await tool_ctx.log_error(f"Failed to edit notebook: {e}")
        raise
