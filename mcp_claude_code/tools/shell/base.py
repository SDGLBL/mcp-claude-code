"""Base classes for shell tools.

This module provides abstract base classes and utilities for shell tools,
including command execution, script running, and process management.
"""

from abc import ABC, abstractmethod
from typing import Any, final
from typing_extensions import override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.permissions import PermissionManager


@final
class CommandResult:
    """Represents the result of a command execution."""

    def __init__(
        self,
        return_code: int = 0,
        stdout: str = "",
        stderr: str = "",
        error_message: str | None = None,
    ):
        """Initialize a command result.

        Args:
            return_code: The command's return code (0 for success)
            stdout: Standard output from the command
            stderr: Standard error from the command
            error_message: Optional error message for failure cases
        """
        self.return_code: int = return_code
        self.stdout: str = stdout
        self.stderr: str = stderr
        self.error_message: str | None = error_message

    @property
    def is_success(self) -> bool:
        """Check if the command executed successfully.

        Returns:
            True if the command succeeded, False otherwise
        """
        return self.return_code == 0

    def format_output(self, include_exit_code: bool = True) -> str:
        """Format the command output as a string.

        Args:
            include_exit_code: Whether to include the exit code in the output

        Returns:
            Formatted output string
        """
        result_parts: list[str] = []

        # Add error message if present
        if self.error_message:
            result_parts.append(f"Error: {self.error_message}")

        # Add exit code if requested and not zero (for non-errors)
        if include_exit_code and (self.return_code != 0 or not self.error_message):
            result_parts.append(f"Exit code: {self.return_code}")

        # Add stdout if present
        if self.stdout:
            result_parts.append(f"STDOUT:\n{self.stdout}")

        # Add stderr if present
        if self.stderr:
            result_parts.append(f"STDERR:\n{self.stderr}")

        # Join with newlines
        return "\n\n".join(result_parts)


class ShellBaseTool(BaseTool, ABC):
    """Base class for shell-related tools.

    Provides common functionality for executing commands and scripts,
    including permissions checking.
    """

    def __init__(self, permission_manager: PermissionManager) -> None:
        """Initialize the shell base tool.

        Args:
            permission_manager: Permission manager for access control
        """
        self.permission_manager: PermissionManager = permission_manager

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed according to permission settings.

        Args:
            path: Path to check

        Returns:
            True if the path is allowed, False otherwise
        """
        return self.permission_manager.is_path_allowed(path)

    @abstractmethod
    async def prepare_tool_context(self, ctx: MCPContext) -> Any:
        """Create and prepare the tool context.

        Args:
            ctx: MCP context

        Returns:
            Prepared tool context
        """
        pass

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this shell tool with the MCP server.

        This provides a default implementation that derived classes should override
        with more specific parameter definitions. This implementation uses generic
        **kwargs which doesn't provide proper parameter definitions to MCP.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        # Each derived class should override this with a more specific signature
        # that explicitly defines the parameters expected by the tool
        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def generic_wrapper(**kwargs: Any) -> str:
            """Generic wrapper for shell tool.

            This wrapper should be overridden by derived classes to provide
            explicit parameter definitions.

            Returns:
                Tool execution result
            """
            # Extract context from kwargs
            ctx = kwargs.pop("ctx")
            # Call the actual tool implementation
            return await tool_self.call(ctx, **kwargs)
