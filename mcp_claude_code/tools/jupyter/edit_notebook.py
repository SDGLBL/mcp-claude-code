"""Edit notebook tool implementation.

This module provides the EditNotebookTool for editing Jupyter notebook files.
"""

import json
from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.jupyter.base import JupyterBaseTool


@final
class EditNotebookTool(JupyterBaseTool):
    """Tool for editing Jupyter notebook files."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "edit_notebook"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Edit a specific cell in a Jupyter notebook.

Enables editing, inserting, or deleting cells in a Jupyter notebook (.ipynb file).
In replace mode, the specified cell's source is updated with the new content.
In insert mode, a new cell is added at the specified index.
In delete mode, the specified cell is removed."""

    @property
    @override
    def parameters(self) -> dict[str, Any]:
        """Get the parameter specifications for the tool.

        Returns:
            Parameter specifications
        """
        return {
            "properties": {
                "path": {
                    "type": "string",
                    "description": "path to the Jupyter notebook file",
                },
                "cell_number": {
                    "type": "integer",
                    "description": "index of the cell to edit",
                },
                "new_source": {
                    "type": "string",
                    "description": "new source code or markdown content",
                },
                "cell_type": {
                    "anyOf": [
                        {"enum": ["code", "markdown"], "type": "string"},
                        {"type": "null"},
                    ],
                    "default": None,
                    "description": "type of the new cell (code or markdown)",
                },
                "edit_mode": {
                    "default": "replace",
                    "enum": ["replace", "insert", "delete"],
                    "type": "string",
                    "description": "edit mode: replace, insert, or delete",
                },
            },
            "required": ["path", "cell_number", "new_source"],
            "title": "edit_notebookArguments",
            "type": "object",
        }

    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.

        Returns:
            List of required parameter names
        """
        return ["path", "cell_number", "new_source"]

    @override
    async def call(self, ctx: MCPContext, **params: Any) -> str:
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
        path = params.get("path")
        cell_number = params.get("cell_number")
        new_source = params.get("new_source")
        cell_type = params.get("cell_type")
        edit_mode = params.get("edit_mode", "replace")

        # Validate path parameter - ensure it's not None and convert to string
        if path is None:
            await tool_ctx.error("Path parameter is required")
            return "Error: Path parameter is required"

        path_str = str(path)
        path_validation = self.validate_path(path_str)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        # Validate cell_number
        if cell_number is None or cell_number < 0:
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
            f"Editing notebook: {path_str} (cell: {cell_number}, mode: {edit_mode})"
        )

        # Check if path is allowed
        if not self.is_path_allowed(path_str):
            await tool_ctx.error(
                f"Access denied - path outside allowed directories: {path_str}"
            )
            return (
                f"Error: Access denied - path outside allowed directories: {path_str}"
            )

        try:
            file_path = Path(path_str)

            if not file_path.exists():
                await tool_ctx.error(f"File does not exist: {path_str}")
                return f"Error: File does not exist: {path_str}"

            if not file_path.is_file():
                await tool_ctx.error(f"Path is not a file: {path_str}")
                return f"Error: Path is not a file: {path_str}"

            # Check file extension
            if file_path.suffix.lower() != ".ipynb":
                await tool_ctx.error(f"File is not a Jupyter notebook: {path_str}")
                return f"Error: File is not a Jupyter notebook: {path_str}"

            # Read and parse the notebook
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    notebook = json.loads(content)
            except json.JSONDecodeError:
                await tool_ctx.error(f"Invalid notebook format: {path_str}")
                return f"Error: Invalid notebook format: {path_str}"
            except UnicodeDecodeError:
                await tool_ctx.error(f"Cannot read notebook file: {path_str}")
                return f"Error: Cannot read notebook file: {path_str}"

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

            # Update document context
            updated_content = json.dumps(notebook, indent=1)
            self.document_context.update_document(path_str, updated_content)

            await tool_ctx.info(
                f"Successfully edited notebook: {path_str} - {change_description}"
            )
            return f"Successfully edited notebook: {path_str} - {change_description}"
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

        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def edit_notebook(
            ctx: MCPContext,
            path: str,
            cell_number: int,
            new_source: str,
            cell_type: str | None = None,
            edit_mode: str = "replace",
        ) -> str:
            return await tool_self.call(
                ctx,
                path=path,
                cell_number=cell_number,
                new_source=new_source,
                cell_type=cell_type,
                edit_mode=edit_mode,
            )
