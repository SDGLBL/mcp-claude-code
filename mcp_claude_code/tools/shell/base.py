"""Base classes for shell tools.

This module provides abstract base classes and utilities for shell tools,
including command execution, script running, and process management.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Self, final

from fastmcp import Context as MCPContext

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.permissions import PermissionManager


class BashCommandStatus(Enum):
    """Status of bash command execution."""

    CONTINUE = "continue"
    COMPLETED = "completed"
    NO_CHANGE_TIMEOUT = "no_change_timeout"
    HARD_TIMEOUT = "hard_timeout"


@final
class CommandResult:
    """Represents the result of a command execution with rich metadata."""

    def __init__(
        self,
        return_code: int = 0,
        stdout: str = "",
        stderr: str = "",
        error_message: str | None = None,
        session_id: str | None = None,
        status: BashCommandStatus = BashCommandStatus.COMPLETED,
        command: str = "",
    ):
        """Initialize a command result.

        Args:
            return_code: The command's return code (0 for success)
            stdout: Standard output from the command
            stderr: Standard error from the command
            error_message: Optional error message for failure cases
            session_id: Optional session ID used for the command execution
            status: Command execution status
            command: The original command that was executed
        """
        self.return_code: int = return_code
        self.stdout: str = stdout
        self.stderr: str = stderr
        self.error_message: str | None = error_message
        self.session_id: str | None = session_id
        self.status: BashCommandStatus = status
        self.command: str = command

    @property
    def is_success(self) -> bool:
        """Check if the command executed successfully.

        Returns:
            True if the command succeeded, False otherwise
        """
        return (
            self.return_code == 0
            and self.status == BashCommandStatus.COMPLETED
            and not self.error_message
        )

    @property
    def is_running(self) -> bool:
        """Check if the command is still running.

        Returns:
            True if the command is still running, False otherwise
        """
        return self.status in {
            BashCommandStatus.CONTINUE,
            BashCommandStatus.NO_CHANGE_TIMEOUT,
            BashCommandStatus.HARD_TIMEOUT,
        }

    @property
    def exit_code(self) -> int:
        """Get the exit code (alias for return_code for compatibility)."""
        return self.return_code

    @property
    def error(self) -> bool:
        """Check if there was an error."""
        return not self.is_success

    @property
    def message(self) -> str:
        """Get a human-readable message about the command result."""
        if self.error_message:
            return f"Command `{self.command}` failed: {self.error_message}"
        return f"Command `{self.command}` executed with exit code {self.return_code}."

    def format_output(self, include_exit_code: bool = True) -> str:
        """Format the command output as a string.

        Args:
            include_exit_code: Whether to include the exit code in the output

        Returns:
            Formatted output string
        """
        result_parts: list[str] = []

        # Add session ID if present
        if self.session_id:
            result_parts.append(f"Session ID: {self.session_id}")

        # Add command status
        if self.status != BashCommandStatus.COMPLETED:
            result_parts.append(f"Status: {self.status.value}")

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

    def to_agent_observation(self) -> str:
        """Format the result for agent consumption."""
        content = self.stdout

        additional_info: list[str] = []
        if self.session_id:
            additional_info.append(f"[Session ID: {self.session_id}]")

        if additional_info:
            content += "\n" + "\n".join(additional_info)

        return content


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
