"""Read notebook tool implementation.

This module provides the NotebookReadTool for reading Jupyter notebook files.
"""

import json
from pathlib import Path
from typing import Annotated, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.jupyter.base import JupyterBaseTool

NotebookPath = Annotated[
    str,
    Field(
        description="The absolute path to the Jupyter notebook file to read (must be absolute, not relative)",
    ),
]


class NotebookReadToolParams(TypedDict):
    """Parameters for the NotebookReadTool.

    Attributes:
        notebook_path: The absolute path to the Jupyter notebook file to read (must be absolute, not relative)
    """

    notebook_path: NotebookPath


@final
class NotebookReadTool(JupyterBaseTool):
    """Tool for reading Jupyter notebook files."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "notebook_read"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return "Reads a Jupyter notebook (.ipynb file) and returns all of the cells with their outputs. Jupyter notebooks are interactive documents that combine code, text, and visualizations, commonly used for data analysis and scientific computing. The notebook_path parameter must be an absolute path, not a relative path."

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[NotebookReadToolParams],
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
        notebook_path: NotebookPath = params["notebook_path"]

        # Validate path parameter
        path_validation = self.validate_path(notebook_path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        await tool_ctx.info(f"Reading notebook: {notebook_path}")

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
                # This will read the file, so we don't need to read it separately
                _, processed_cells = await self.parse_notebook(file_path)

                # Format the notebook content as a readable string
                result = self.format_notebook_cells(processed_cells)

                await tool_ctx.info(
                    f"Successfully read notebook: {notebook_path} ({len(processed_cells)} cells)"
                )
                return result
            except json.JSONDecodeError:
                await tool_ctx.error(f"Invalid notebook format: {notebook_path}")
                return f"Error: Invalid notebook format: {notebook_path}"
            except UnicodeDecodeError:
                await tool_ctx.error(f"Cannot read notebook file: {notebook_path}")
                return f"Error: Cannot read notebook file: {notebook_path}"
        except Exception as e:
            await tool_ctx.error(f"Error reading notebook: {str(e)}")
            return f"Error reading notebook: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this read notebook tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """

        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.description)
        async def notebook_read(
            ctx: MCPContext,
            notebook_path: NotebookPath,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(ctx, notebook_path=notebook_path)
