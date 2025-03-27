"""Read notebook tool implementation.

This module provides the ReadNotebookTool for reading Jupyter notebook files.
"""

import json
from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.jupyter.base import JupyterBaseTool


@final
class ReadNotebookTool(JupyterBaseTool):
    """Tool for reading Jupyter notebook files."""
    
    @property
    @override 
    def name(self) -> str:
        """Get the tool name.
        
        Returns:
            Tool name
        """
        return "read_notebook"
        
    @property
    @override 
    def description(self) -> str:
        """Get the tool description.
        
        Returns:
            Tool description
        """
        return """Extract and read source code from all cells in a Jupyter notebook.

Reads a Jupyter notebook (.ipynb file) and returns all of the cells with 
their outputs. Jupyter notebooks are interactive documents that combine 
code, text, and visualizations, commonly used for data analysis and 
scientific computing."""
        
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
                    "description": "path to the Jupyter notebook file"
                }
            },
            "required": ["path"],
            "type": "object"
        }
        
    @property
    @override 
    def required(self) -> list[str]:
        """Get the list of required parameter names.
        
        Returns:
            List of required parameter names
        """
        return ["path"]
        
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

        if not path:
            await tool_ctx.error("Missing required parameter: path")
            return "Error: Missing required parameter: path"
        
        # Validate path parameter
        path_validation = self.validate_path(path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        await tool_ctx.info(f"Reading notebook: {path}")

        # Check if path is allowed
        if not self.is_path_allowed(path):
            await tool_ctx.error(
                f"Access denied - path outside allowed directories: {path}"
            )
            return f"Error: Access denied - path outside allowed directories: {path}"

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
                # This will read the file, so we don't need to read it separately
                _, processed_cells = await self.parse_notebook(file_path)
                
                # Add to document context
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.document_context.add_document(path, content)
                
                # Format the notebook content as a readable string
                result = self.format_notebook_cells(processed_cells)

                await tool_ctx.info(f"Successfully read notebook: {path} ({len(processed_cells)} cells)")
                return result
            except json.JSONDecodeError:
                await tool_ctx.error(f"Invalid notebook format: {path}")
                return f"Error: Invalid notebook format: {path}"
            except UnicodeDecodeError:
                await tool_ctx.error(f"Cannot read notebook file: {path}")
                return f"Error: Cannot read notebook file: {path}"
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
        
        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def read_notebook(path: str, ctx: MCPContext) -> str:
            return await tool_self.call(ctx, path=path)
