"""Write file tool implementation.

This module provides the Write tool for creating or overwriting files.
"""

from pathlib import Path
from typing import Annotated, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool

FilePath = Annotated[
    str,
    Field(
        description="The absolute path to the file to write (must be absolute, not relative)",
        min_length=1,
    ),
]

Content = Annotated[
    str,
    Field(
        description="The content to write to the file",
        min_length=1,
    ),
]


class WriteToolParams(TypedDict):
    """Parameters for the Write tool.

    Attributes:
        file_path: The absolute path to the file to write (must be absolute, not relative)
        content: The content to write to the file
    """

    file_path: FilePath
    content: Content


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
        return """Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one at the provided path.
- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User."""

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[WriteToolParams],
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
        file_path: FilePath = params["file_path"]
        content: Content = params["content"]

        # Validate parameters
        path_validation = self.validate_path(file_path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

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

        @mcp_server.tool(name=self.name, description=self.description)
        async def write(
            ctx: MCPContext,
            file_path: FilePath,
            content: Content,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(ctx, file_path=file_path, content=content)
