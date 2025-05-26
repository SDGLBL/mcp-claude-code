"""Base functionality for filesystem tools.

This module provides common functionality for filesystem tools including path handling,
error formatting, and shared utilities for file operations.
"""

from abc import ABC
from pathlib import Path
from typing import Any

from fastmcp import Context as MCPContext

from mcp_claude_code.tools.common.base import FileSystemTool
from mcp_claude_code.tools.common.context import ToolContext, create_tool_context


class FilesystemBaseTool(FileSystemTool, ABC):
    """Enhanced base class for all filesystem tools.

    Provides additional utilities specific to filesystem operations beyond
    the base functionality in FileSystemTool.
    """

    async def check_path_allowed(
        self, path: str, tool_ctx: Any, error_prefix: str = "Error"
    ) -> tuple[bool, str]:
        """Check if a path is allowed and log an error if not.

        Args:
            path: Path to check
            tool_ctx: Tool context for logging
            error_prefix: Prefix for error messages

        Returns:
            tuple of (is_allowed, error_message)
        """
        if not self.is_path_allowed(path):
            message = f"Access denied - path outside allowed directories: {path}"
            await tool_ctx.error(message)
            return False, f"{error_prefix}: {message}"
        return True, ""

    async def check_path_exists(
        self, path: str, tool_ctx: Any, error_prefix: str = "Error"
    ) -> tuple[bool, str]:
        """Check if a path exists and log an error if not.

        Args:
            path: Path to check
            tool_ctx: Tool context for logging
            error_prefix: Prefix for error messages

        Returns:
            tuple of (exists, error_message)
        """
        file_path = Path(path)
        if not file_path.exists():
            message = f"Path does not exist: {path}"
            await tool_ctx.error(message)
            return False, f"{error_prefix}: {message}"
        return True, ""

    async def check_is_file(
        self, path: str, tool_ctx: Any, error_prefix: str = "Error"
    ) -> tuple[bool, str]:
        """Check if a path is a file and log an error if not.

        Args:
            path: Path to check
            tool_ctx: Tool context for logging
            error_prefix: Prefix for error messages

        Returns:
            tuple of (is_file, error_message)
        """
        file_path = Path(path)
        if not file_path.is_file():
            message = f"Path is not a file: {path}"
            await tool_ctx.error(message)
            return False, f"{error_prefix}: {message}"
        return True, ""

    async def check_is_directory(
        self, path: str, tool_ctx: Any, error_prefix: str = "Error"
    ) -> tuple[bool, str]:
        """Check if a path is a directory and log an error if not.

        Args:
            path: Path to check
            tool_ctx: Tool context for logging
            error_prefix: Prefix for error messages

        Returns:
            tuple of (is_directory, error_message)
        """
        dir_path = Path(path)
        if not dir_path.is_dir():
            message = f"Path is not a directory: {path}"
            await tool_ctx.error(message)
            return False, f"{error_prefix}: {message}"
        return True, ""

    def create_tool_context(self, ctx: MCPContext) -> ToolContext:
        """Create a tool context with the tool name.

        Args:
            ctx: MCP context

        Returns:
            Tool context
        """
        tool_ctx = create_tool_context(ctx)
        return tool_ctx

    def set_tool_context_info(self, tool_ctx: ToolContext) -> None:
        """Set the tool info on the context.

        Args:
            tool_ctx: Tool context
        """
        tool_ctx.set_tool_info(self.name)
