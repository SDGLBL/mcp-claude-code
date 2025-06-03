"""Edit notebook tool implementation.

This module provides the NoteBookEditTool for editing Jupyter notebook files.
"""

import json
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.jupyter.base import JupyterBaseTool

NotebookPath = Annotated[
    str,
    Field(
        description="The absolute path to the Jupyter notebook file to edit (must be absolute, not relative)",
    ),
]

CellNumber = Annotated[
    int,
    Field(
        description="The index of the cell to edit (0-based)",
        ge=0,
    ),
]

NewSource = Annotated[
    str,
    Field(
        description="The new source for the cell",
        default="",
    ),
]

CellType = Annotated[
    Literal["code", "markdown"],
    Field(
        description="The of the cell (code or markdown). If not specified, it defaults to the current cell type. If using edit_mode=insert, this is required.",
        default="code",
    ),
]

EditMode = Annotated[
    Literal["replace", "insert", "delete"],
    Field(
        description="The of edit to make (replace, insert, delete). Defaults to replace.",
        default="replace",
    ),
]


class NotebookEditToolParams(TypedDict):
    """Parameters for the NotebookEditTool.

    Attributes:
        notebook_path: The absolute path to the Jupyter notebook file to edit (must be absolute, not relative)
        cell_number: The index of the cell to edit (0-based)
        new_source: The new source for the cell
        cell_type: The of the cell (code or markdown). If not specified, it defaults to the current cell type. If using edit_mode=insert, this is required.
        edit_mode: The of edit to make (replace, insert, delete). Defaults to replace.
    """

    notebook_path: NotebookPath
    cell_number: CellNumber
    new_source: NewSource
    cell_type: CellType
    edit_mode: EditMode


@final
class NoteBookEditTool(JupyterBaseTool):
    """Tool for editing Jupyter notebook files."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "notebook_edit"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return "Completely replaces the contents of a specific cell in a Jupyter notebook (.ipynb file) with new source. Jupyter notebooks are interactive documents that combine code, text, and visualizations, commonly used for data analysis and scientific computing. The notebook_path parameter must be an absolute path, not a relative path. The cell_number is 0-indexed. Use edit_mode=insert to add a new cell at the index specified by cell_number. Use edit_mode=delete to delete the cell at the index specified by cell_number."

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[NotebookEditToolParams],
    ) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = self.create_tool_context(ctx)
        self.set_tool_context_info(tool_ctx)

        # Extract parameters
        notebook_path = params.get("notebook_path")
        cell_number = params.get("cell_number")
        new_source = params.get("new_source")
        cell_type = params.get("cell_type")
        edit_mode = params.get("edit_mode", "replace")

        path_validation = self.validate_path(notebook_path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

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
            f"Editing notebook: {notebook_path} (cell: {cell_number}, mode: {edit_mode})"
        )

        # Check if path is allowed
        if not self.is_path_allowed(notebook_path):
            await tool_ctx.error(
                f"Access denied - path outside allowed directories: {notebook_path}"
            )
            return f"Error: Access denied - path outside allowed directories: {notebook_path}"

        try:
            file_path = Path(notebook_path)

            if not file_path.exists():
                await tool_ctx.error(f"File does not exist: {notebook_path}")
                return f"Error: File does not exist: {notebook_path}"

            if not file_path.is_file():
                await tool_ctx.error(f"Path is not a file: {notebook_path}")
                return f"Error: Path is not a file: {notebook_path}"

            # Check file extension
            if file_path.suffix.lower() != ".ipynb":
                await tool_ctx.error(f"File is not a Jupyter notebook: {notebook_path}")
                return f"Error: File is not a Jupyter notebook: {notebook_path}"

            # Read and parse the notebook
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    notebook = json.loads(content)
            except json.JSONDecodeError:
                await tool_ctx.error(f"Invalid notebook format: {notebook_path}")
                return f"Error: Invalid notebook format: {notebook_path}"
            except UnicodeDecodeError:
                await tool_ctx.error(f"Cannot read notebook file: {notebook_path}")
                return f"Error: Cannot read notebook file: {notebook_path}"

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

            await tool_ctx.info(
                f"Successfully edited notebook: {notebook_path} - {change_description}"
            )
            return (
                f"Successfully edited notebook: {notebook_path} - {change_description}"
            )
        except Exception as e:
            await tool_ctx.error(f"Error editing notebook: {str(e)}")
            return f"Error editing notebook: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this edit notebook tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.description)
        async def notebook_edit(
            notebook_path: NotebookPath,
            cell_number: CellNumber,
            new_source: NewSource,
            cell_type: CellType,
            edit_mode: EditMode,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(
                ctx,
                notebook_path=notebook_path,
                cell_number=cell_number,
                new_source=new_source,
                cell_type=cell_type,
                edit_mode=edit_mode,
            )
