"""Read tool implementation.

This module provides the ReadTool for reading the contents of files.
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
        description="The absolute path to the file to read",
    ),
]

Offset = Annotated[
    int,
    Field(
        description="The line number to start reading from. Only provide if the file is too large to read at once",
        default=0,
    ),
]

Limit = Annotated[
    int,
    Field(
        description="The number of lines to read. Only provide if the file is too large to read at once",
        default=2000,
    ),
]


class ReadToolParams(TypedDict):
    """Parameters for the ReadTool.

    Attributes:
        file_path: The absolute path to the file to read
        offset: The line number to start reading from. Only provide if the file is too large to read at once
        limit: The number of lines to read. Only provide if the file is too large to read at once
    """

    file_path: FilePath
    offset: Offset
    limit: Limit


@final
class ReadTool(FilesystemBaseTool):
    """Tool for reading file contents."""

    # Default values for truncation
    DEFAULT_LINE_LIMIT = 2000
    MAX_LINE_LENGTH = 2000
    LINE_TRUNCATION_INDICATOR = "... [line truncated]"

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "read"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Reads a file from the local filesystem. You can access any file directly by using this tool.
Assume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to 2000 lines starting from the beginning of the file
- You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters
- Any lines longer than 2000 characters will be truncated
- Results are returned using cat -n format, with line numbers starting at 1
- For Jupyter notebooks (.ipynb files), use the notebook_read instead
- When reading multiple files, you MUST use the batch tool to read them all at once"""

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[ReadToolParams],
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
        file_path = params.get("file_path")
        offset = params.get("offset", 0)
        limit = params.get("limit", self.DEFAULT_LINE_LIMIT)

        # Validate required parameters for direct calls (not through MCP framework)
        if not file_path:
            await tool_ctx.error("Parameter 'file_path' is required but was None")
            return "Error: Parameter 'file_path' is required but was None"

        await tool_ctx.info(
            f"Reading file: {file_path} (offset: {offset}, limit: {limit})"
        )

        # Check if path is allowed
        if not self.is_path_allowed(file_path):
            await tool_ctx.error(
                f"Access denied - path outside allowed directories: {file_path}"
            )
            return (
                f"Error: Access denied - path outside allowed directories: {file_path}"
            )

        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                await tool_ctx.error(f"File does not exist: {file_path}")
                return f"Error: File does not exist: {file_path}"

            if not file_path_obj.is_file():
                await tool_ctx.error(f"Path is not a file: {file_path}")
                return f"Error: Path is not a file: {file_path}"

            # Read the file
            try:
                # Read and process the file with line numbers and truncation
                lines = []
                current_line = 0
                truncated_lines = 0

                # Try with utf-8 encoding first
                try:
                    with open(file_path_obj, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f):
                            # Skip lines before offset
                            if i < offset:
                                continue

                            # Stop after reading 'limit' lines
                            if current_line >= limit:
                                truncated_lines = True
                                break

                            current_line += 1

                            # Truncate long lines
                            if len(line) > self.MAX_LINE_LENGTH:
                                line = (
                                    line[: self.MAX_LINE_LENGTH]
                                    + self.LINE_TRUNCATION_INDICATOR
                                )

                            # Add line with line number (1-based)
                            lines.append(f"{i + 1:6d}  {line.rstrip()}")

                except UnicodeDecodeError:
                    # Try with latin-1 encoding
                    try:
                        lines = []
                        current_line = 0
                        truncated_lines = 0

                        with open(file_path_obj, "r", encoding="latin-1") as f:
                            for i, line in enumerate(f):
                                # Skip lines before offset
                                if i < offset:
                                    continue

                                # Stop after reading 'limit' lines
                                if current_line >= limit:
                                    truncated_lines = True
                                    break

                                current_line += 1

                                # Truncate long lines
                                if len(line) > self.MAX_LINE_LENGTH:
                                    line = (
                                        line[: self.MAX_LINE_LENGTH]
                                        + self.LINE_TRUNCATION_INDICATOR
                                    )

                                # Add line with line number (1-based)
                                lines.append(f"{i + 1:6d}  {line.rstrip()}")

                        await tool_ctx.warning(
                            f"File read with latin-1 encoding: {file_path}"
                        )

                    except Exception:
                        await tool_ctx.error(f"Cannot read binary file: {file_path}")
                        return f"Error: Cannot read binary file: {file_path}"

                # Format the result
                result = "\n".join(lines)

                # Add truncation message if necessary
                if truncated_lines:
                    result += f"\n... (output truncated, showing {limit} of {limit + truncated_lines}+ lines)"

                await tool_ctx.info(f"Successfully read file: {file_path}")
                return result

            except Exception as e:
                await tool_ctx.error(f"Error reading file: {str(e)}")
                return f"Error: {str(e)}"

        except Exception as e:
            await tool_ctx.error(f"Error reading file: {str(e)}")
            return f"Error: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self

        @mcp_server.tool(name=self.name, description=self.description)
        async def read(
            ctx: MCPContext,
            file_path: FilePath,
            offset: Offset,
            limit: Limit,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(
                ctx, file_path=file_path, offset=offset, limit=limit
            )
