"""Get file info tool implementation.

This module provides the GetFileInfoTool for retrieving metadata about files and directories.
"""

import time
from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool


@final
class GetFileInfoTool(FilesystemBaseTool):
    """Tool for retrieving metadata about files and directories."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "get_file_info"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Retrieve detailed metadata about a file or directory.

Returns comprehensive information including size, creation time,
last modified time, permissions, and type. This tool is perfect for
understanding file characteristics without reading the actual content.
Only works within allowed directories."""

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
                    "description": "path to the file or directory to inspect",
                }
            },
            "required": ["path"],
            "type": "object",
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

        # Extract parameters
        path = params.get("path")

        if not path:
            await tool_ctx.error("Parameter 'path' is required but was None")
            return "Error: Parameter 'path' is required but was None"

        if path.strip() == "":
            await tool_ctx.error("Parameter 'path' cannot be empty")
            return "Error: Parameter 'path' cannot be empty"

        # Validate path parameter
        path_validation = self.validate_path(path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        await tool_ctx.info(f"Getting file info: {path}")

        # Check if path is allowed
        allowed, error_msg = await self.check_path_allowed(path, tool_ctx)
        if not allowed:
            return error_msg

        try:
            file_path = Path(path)

            # Check if path exists
            exists, error_msg = await self.check_path_exists(path, tool_ctx)
            if not exists:
                return error_msg

            # Get file stats
            stats = file_path.stat()

            # Format timestamps
            created_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(stats.st_ctime)
            )
            modified_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(stats.st_mtime)
            )
            accessed_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(stats.st_atime)
            )

            # Format permissions in octal
            permissions = oct(stats.st_mode)[-3:]

            # Build info dictionary
            file_info: dict[str, Any] = {
                "name": file_path.name,
                "type": "directory" if file_path.is_dir() else "file",
                "size": stats.st_size,
                "created": created_time,
                "modified": modified_time,
                "accessed": accessed_time,
                "permissions": permissions,
            }

            # Format the output
            result = [f"{key}: {value}" for key, value in file_info.items()]

            await tool_ctx.info(f"Retrieved info for {path}")
            return "\n".join(result)
        except Exception as e:
            await tool_ctx.error(f"Error getting file info: {str(e)}")
            return f"Error getting file info: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this get file info tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def get_file_info(path: str, ctx: MCPContext) -> str:
            return await tool_self.call(ctx, path=path)
