"""Write file tool implementation.

This module provides the Write tool for creating or overwriting files.
"""

from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool


@final
class Write(FilesystemBaseTool):
    """Tool for writing file contents."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "write"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Write a file to the local filesystem. Overwrites the existing file if there is one.

Before using this tool:

1. Use the ReadFile tool to understand the file's contents and context

2. Directory Verification (only applicable when creating new files):
   - Use the LS tool to verify the parent directory exists and is the correct location"""

    @property
    @override
    def parameters(self) -> dict[str, Any]:
        """Get the parameter specifications for the tool.

        Returns:
            Parameter specifications
        """
        return {
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to write (must be absolute, not relative)",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["file_path", "content"],
            "type": "object",
            "additionalProperties": False,
        }

    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.

        Returns:
            List of required parameter names
        """
        return ["file_path", "content"]

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
        file_path = params.get("file_path")
        content = params.get("content")

        if not file_path:
            await tool_ctx.error("Parameter 'file_path' is required but was None")
            return "Error: Parameter 'file_path' is required but was None"

        if file_path.strip() == "":
            await tool_ctx.error("Parameter 'file_path' cannot be empty")
            return "Error: Parameter 'file_path' cannot be empty"

        # Validate parameters
        path_validation = self.validate_path(file_path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        if not content:
            await tool_ctx.error("Parameter 'content' is required but was None")
            return "Error: Parameter 'content' is required but was None"

        await tool_ctx.info(f"Writing file: {file_path}")

        # Check if file is allowed to be written
        allowed, error_msg = await self.check_path_allowed(file_path, tool_ctx)
        if not allowed:
            return error_msg

        # Additional check already verified by is_path_allowed above
        await tool_ctx.info(f"Writing file: {file_path}")

        try:
            path_obj = Path(file_path)

            # Check if parent directory is allowed
            parent_dir = str(path_obj.parent)
            if not self.is_path_allowed(parent_dir):
                await tool_ctx.error(f"Parent directory not allowed: {parent_dir}")
                return f"Error: Parent directory not allowed: {parent_dir}"

            # Create parent directories if they don't exist
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            with open(path_obj, "w", encoding="utf-8") as f:
                f.write(content)

            # Add to document context
            self.document_context.add_document(file_path, content)

            await tool_ctx.info(
                f"Successfully wrote file: {file_path} ({len(content)} bytes)"
            )
            return f"Successfully wrote file: {file_path} ({len(content)} bytes)"
        except Exception as e:
            await tool_ctx.error(f"Error writing file: {str(e)}")
            return f"Error writing file: {str(e)}"

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
        async def write(file_path: str, content: str, ctx: MCPContext) -> str:
            return await tool_self.call(ctx, file_path=file_path, content=content)

