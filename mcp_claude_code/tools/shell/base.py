"""Base classes for shell tools.

This module provides abstract base classes and utilities for shell tools,
including command execution, script running, and process management.
"""

import json
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Self, final

from fastmcp import Context as MCPContext
from pydantic import BaseModel

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.permissions import PermissionManager


class BashCommandStatus(Enum):
    """Status of bash command execution."""

    CONTINUE = "continue"
    COMPLETED = "completed"
    NO_CHANGE_TIMEOUT = "no_change_timeout"
    HARD_TIMEOUT = "hard_timeout"


# PS1 metadata constants
CMD_OUTPUT_PS1_BEGIN = "\n###PS1JSON###\n"
CMD_OUTPUT_PS1_END = "\n###PS1END###"
CMD_OUTPUT_METADATA_PS1_REGEX = re.compile(
    f"^{CMD_OUTPUT_PS1_BEGIN.strip()}(.*?){CMD_OUTPUT_PS1_END.strip()}",
    re.DOTALL | re.MULTILINE,
)


class CmdOutputMetadata(BaseModel):
    """Rich metadata captured from PS1 prompts and command execution."""

    exit_code: int = -1
    pid: int = -1
    username: str | None = None
    hostname: str | None = None
    working_dir: str | None = None
    py_interpreter_path: str | None = None
    prefix: str = ""  # Prefix to add to command output
    suffix: str = ""  # Suffix to add to command output

    @classmethod
    def to_ps1_prompt(cls) -> str:
        """Convert the required metadata into a PS1 prompt."""
        prompt = CMD_OUTPUT_PS1_BEGIN
        json_str = json.dumps(
            {
                "pid": "$!",
                "exit_code": "$?",
                "username": r"\u",
                "hostname": r"\h",
                "working_dir": r"$(pwd)",
                "py_interpreter_path": r'$(which python 2>/dev/null || echo "")',
            },
            indent=2,
        )
        # Make sure we escape double quotes in the JSON string
        # So that PS1 will keep them as part of the output
        prompt += json_str.replace('"', r"\"")
        prompt += CMD_OUTPUT_PS1_END + "\n"  # Ensure there's a newline at the end
        return prompt

    @classmethod
    def matches_ps1_metadata(cls, string: str) -> list[re.Match[str]]:
        """Find all PS1 metadata matches in a string."""
        matches = []
        for match in CMD_OUTPUT_METADATA_PS1_REGEX.finditer(string):
            try:
                json.loads(match.group(1).strip())  # Try to parse as JSON
                matches.append(match)
            except json.JSONDecodeError:
                continue  # Skip if not valid JSON
        return matches

    @classmethod
    def from_ps1_match(cls, match: re.Match[str]) -> Self:
        """Extract the required metadata from a PS1 prompt."""
        metadata = json.loads(match.group(1))
        # Create a copy of metadata to avoid modifying the original
        processed = metadata.copy()
        # Convert numeric fields
        if "pid" in metadata:
            try:
                processed["pid"] = int(float(str(metadata["pid"])))
            except (ValueError, TypeError):
                processed["pid"] = -1
        if "exit_code" in metadata:
            try:
                processed["exit_code"] = int(float(str(metadata["exit_code"])))
            except (ValueError, TypeError):
                processed["exit_code"] = -1
        return cls(**processed)


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
        metadata: CmdOutputMetadata | None = None,
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
            metadata: Rich metadata from command execution
            status: Command execution status
            command: The original command that was executed
        """
        self.return_code: int = return_code
        self.stdout: str = stdout
        self.stderr: str = stderr
        self.error_message: str | None = error_message
        self.session_id: str | None = session_id
        self.metadata: CmdOutputMetadata = metadata or CmdOutputMetadata()
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
        """Format the command output as a string with rich metadata.

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

        # Add working directory if available
        if self.metadata.working_dir:
            result_parts.append(f"Working directory: {self.metadata.working_dir}")

        # Add Python interpreter if available
        if self.metadata.py_interpreter_path:
            result_parts.append(
                f"Python interpreter: {self.metadata.py_interpreter_path}"
            )

        # Format the main output with prefix and suffix
        output_content = self.stdout
        if self.metadata.prefix:
            output_content = self.metadata.prefix + output_content
        if self.metadata.suffix:
            output_content = output_content + self.metadata.suffix

        # Add stdout if present
        if output_content:
            result_parts.append(f"STDOUT:\n{output_content}")

        # Add stderr if present
        if self.stderr:
            result_parts.append(f"STDERR:\n{self.stderr}")

        # Join with newlines
        return "\n\n".join(result_parts)

    def to_agent_observation(self) -> str:
        """Format the result for agent consumption (similar to OpenHands)."""
        content = self.stdout
        if self.metadata.prefix:
            content = self.metadata.prefix + content
        if self.metadata.suffix:
            content = content + self.metadata.suffix

        additional_info: list[str] = []
        if self.metadata.working_dir:
            additional_info.append(
                f"[Current working directory: {self.metadata.working_dir}]"
            )
        if self.metadata.py_interpreter_path:
            additional_info.append(
                f"[Python interpreter: {self.metadata.py_interpreter_path}]"
            )
        if self.metadata.exit_code != -1:
            additional_info.append(
                f"[Command finished with exit code {self.metadata.exit_code}]"
            )
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
