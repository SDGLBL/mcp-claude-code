"""Read files tool implementation.

This module provides the ReadFilesTool for reading the contents of files.
"""

from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool


@final
class ReadFilesTool(FilesystemBaseTool):
    """Tool for reading file contents."""
    
    @property
    @override
    def name(self) -> str:
        """Get the tool name.
        
        Returns:
            Tool name
        """
        return "read_files"
        
    @property
    @override
    def description(self) -> str:
        """Get the tool description.
        
        Returns:
            Tool description
        """
        return """Read the contents of one or multiple files.

Can read a single file or multiple files simultaneously. When reading multiple files,
each file's content is returned with its path as a reference. Failed reads for
individual files won't stop the entire operation. Only works within allowed directories."""
        
    @property
    @override
    def parameters(self) -> dict[str, Any]:
        """Get the parameter specifications for the tool.
        
        Returns:
            Parameter specifications
        """
        return {
            "properties": {
                "paths": {
                    "anyOf": [
                        {"items": {"type": "string"}, "type": "array"},
                        {"type": "string"}
                    ],
                    "description": "absolute paths to the file or files to read"
                }
            },
            "required": ["paths"],
            "type": "object"
        }
        
    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.
        
        Returns:
            List of required parameter names
        """
        return ["paths"]
        
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
        paths = params.get("paths")
        
        # Validate the 'paths' parameter
        if not paths:
            await tool_ctx.error("Parameter 'paths' is required but was None")
            return "Error: Parameter 'paths' is required but was None"

        # Convert single path to list if necessary
        path_list: list[str] = [paths] if isinstance(paths, str) else paths

        # Handle empty list case
        if not path_list:
            await tool_ctx.warning("No files specified to read")
            return "Error: No files specified to read"

        # For a single file with direct string return
        single_file_mode = isinstance(paths, str)

        await tool_ctx.info(f"Reading {len(path_list)} file(s)")

        results: list[str] = []

        # Read each file
        for i, path in enumerate(path_list):
            # Report progress
            await tool_ctx.report_progress(i, len(path_list))

            # Check if path is allowed
            if not self.is_path_allowed(path):
                await tool_ctx.error(
                    f"Access denied - path outside allowed directories: {path}"
                )
                results.append(
                    f"{path}: Error - Access denied - path outside allowed directories"
                )
                continue

            try:
                file_path = Path(path)

                if not file_path.exists():
                    await tool_ctx.error(f"File does not exist: {path}")
                    results.append(f"{path}: Error - File does not exist")
                    continue

                if not file_path.is_file():
                    await tool_ctx.error(f"Path is not a file: {path}")
                    results.append(f"{path}: Error - Path is not a file")
                    continue

                # Read the file
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Add to document context
                    self.document_context.add_document(path, content)

                    results.append(f"{path}:\n{content}")
                except UnicodeDecodeError:
                    try:
                        with open(file_path, "r", encoding="latin-1") as f:
                            content = f.read()
                        await tool_ctx.warning(
                            f"File read with latin-1 encoding: {path}"
                        )
                        results.append(f"{path} (latin-1 encoding):\n{content}")
                    except Exception:
                        await tool_ctx.error(f"Cannot read binary file: {path}")
                        results.append(f"{path}: Error - Cannot read binary file")
            except Exception as e:
                await tool_ctx.error(f"Error reading file: {str(e)}")
                results.append(f"{path}: Error - {str(e)}")

        # Final progress report
        await tool_ctx.report_progress(len(path_list), len(path_list))

        await tool_ctx.info(f"Read {len(path_list)} file(s)")

        # For single file mode with direct string input, return just the content
        # if successful, otherwise return the error
        if single_file_mode and len(results) == 1:
            result_text = results[0]
            # If it's a successful read (doesn't contain "Error - ")
            if not result_text.split(":", 1)[1].strip().startswith("Error - "):
                # Just return the content part (after the first colon and newline)
                return result_text.split(":", 1)[1].strip()
            else:
                # Return just the error message
                return "Error: " + result_text.split("Error - ", 1)[1]

        # For multiple files or failed single file read, return all results
        return "\n\n---\n\n".join(results)
        
    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this tool with the MCP server.
        
        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.
        
        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure
        
        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def read_files(ctx: MCPContext, paths: list[str] | str) -> str:
            return await tool_self.call(ctx, paths=paths)
