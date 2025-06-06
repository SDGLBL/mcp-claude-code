"""Bash session executor for MCP Claude Code.

This module provides a BashSessionExecutor class that replaces the old CommandExecutor
implementation with the new BashSession-based approach for better persistent execution.
"""

import asyncio
import os
import shlex
import subprocess
from typing import final

from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.shell.base import BashCommandStatus, CommandResult
from mcp_claude_code.tools.shell.session_manager import SessionManager


@final
class BashSessionExecutor:
    """Command executor using BashSession for persistent execution.

    This class provides the same interface as the old CommandExecutor but uses
    the new BashSession implementation for better persistent command execution.
    """

    def __init__(
        self,
        permission_manager: PermissionManager,
        verbose: bool = False,
        session_manager: SessionManager | None = None,
        fast_test_mode: bool = False,
    ) -> None:
        """Initialize bash session executor.

        Args:
            permission_manager: Permission manager for access control
            verbose: Enable verbose logging
            session_manager: Optional session manager for dependency injection.
                           If None, creates a new SessionManager instance.
            fast_test_mode: Enable fast test mode with reduced timeouts and polling intervals
        """
        self.permission_manager: PermissionManager = permission_manager
        self.verbose: bool = verbose
        self.fast_test_mode: bool = fast_test_mode

        # If no session manager is provided, create a non-singleton instance to avoid shared state
        self.session_manager: SessionManager = session_manager or SessionManager(
            use_singleton=False
        )

        # Excluded commands or patterns (for compatibility)
        self.excluded_commands: list[str] = ["rm"]

    def _log(self, message: str, data: object | None = None) -> None:
        """Log a message if verbose logging is enabled.

        Args:
            message: The message to log
            data: Optional data to include with the message
        """
        if not self.verbose:
            return

        if data is not None:
            try:
                import json

                if isinstance(data, (dict, list)):
                    data_str = json.dumps(data)
                else:
                    data_str = str(data)
                print(f"DEBUG: {message}: {data_str}")
            except Exception:
                print(f"DEBUG: {message}: {data}")
        else:
            print(f"DEBUG: {message}")

    def allow_command(self, command: str) -> None:
        """Allow a specific command that might otherwise be excluded.

        Args:
            command: The command to allow
        """
        if command in self.excluded_commands:
            self.excluded_commands.remove(command)

    def deny_command(self, command: str) -> None:
        """Deny a specific command, adding it to the excluded list.

        Args:
            command: The command to deny
        """
        if command not in self.excluded_commands:
            self.excluded_commands.append(command)

    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed based on exclusion lists.

        Args:
            command: The command to check

        Returns:
            True if the command is allowed, False otherwise
        """
        # Check for empty commands
        try:
            args: list[str] = shlex.split(command)
        except ValueError as e:
            self._log(f"Command parsing error: {e}")
            return False

        if not args:
            return False

        base_command: str = args[0]

        # Check if base command is in exclusion list
        if base_command in self.excluded_commands:
            self._log(f"Command rejected (in exclusion list): {base_command}")
            return False

        return True

    async def execute_command(
        self,
        command: str,
        env: dict[str, str] | None = None,
        timeout: float | None = 60.0,
        session_id: str = "",
        is_input: bool = False,
        blocking: bool = False,
    ) -> CommandResult:
        """Execute a shell command with safety checks.

        Args:
            command: The command to execute
            env: Optional environment variables
            timeout: Optional timeout in seconds
            session_id: Optional session ID for persistent execution
            is_input: Whether this is input to a running process
            blocking: Whether to run in blocking mode

        Returns:
            CommandResult containing execution results
        """
        self._log(
            f"Executing command: {command} (is_input={is_input}, blocking={blocking})"
        )

        # Check if the command is allowed (skip for input to running processes)
        if not is_input and not self.is_command_allowed(command):
            return CommandResult(
                return_code=1,
                error_message=f"Command not allowed: {command}",
                session_id=session_id,
                command=command,
            )

        # Handle subprocess mode when session_id is explicitly None
        if not session_id:
            return await self._execute_subprocess_mode(command, env, timeout)

        # Default working directory for new sessions only
        # Existing sessions maintain their current working directory
        # Users should use 'cd' commands to navigate within sessions
        default_work_dir = os.path.expanduser("~")

        # Generate default session ID if none provided
        effective_session_id = session_id
        if effective_session_id == "":
            import uuid

            effective_session_id = f"default_{uuid.uuid4().hex[:8]}"
            self._log(f"Generated default session ID: {effective_session_id}")

        # Use session-based execution
        try:
            # Get existing session or create new one
            session = self.session_manager.get_session(effective_session_id)
            if session is None:
                # Use faster timeouts and polling for tests
                if self.fast_test_mode:
                    timeout_seconds = (
                        10  # Faster timeout for tests but not too aggressive
                    )
                    poll_interval = 0.2  # Faster polling for tests but still reasonable
                else:
                    timeout_seconds = 30  # Default timeout
                    poll_interval = 0.5  # Default polling

                session = self.session_manager.get_or_create_session(
                    session_id=effective_session_id,
                    work_dir=default_work_dir,
                    no_change_timeout_seconds=timeout_seconds,
                    poll_interval=poll_interval,
                )

            # Set environment variables if provided (only for new commands, not input)
            if env and not is_input:
                for key, value in env.items():
                    env_result = session.execute(f'export {key}="{value}"')
                    if env_result.return_code != 0:
                        self._log(f"Failed to set environment variable {key}")

            # Execute the command with enhanced parameters
            result = session.execute(
                command=command, is_input=is_input, blocking=blocking, timeout=timeout
            )

            # Add session_id to the result
            result.session_id = effective_session_id
            return result
        except Exception as e:
            self._log(f"Session execution error: {str(e)}")
            return CommandResult(
                return_code=1,
                error_message=f"Error executing command in session: {str(e)}",
                session_id=effective_session_id,
                command=command,
            )

    async def _execute_subprocess_mode(
        self,
        command: str,
        env: dict[str, str] | None = None,
        timeout: float | None = 60.0,
    ) -> CommandResult:
        """Execute command in true subprocess mode with no persistence.

        Args:
            command: The command to execute
            env: Optional environment variables
            timeout: Optional timeout in seconds

        Returns:
            CommandResult containing execution results
        """
        self._log(f"Executing command in subprocess mode: {command}")

        # Prepare environment - start with current env and add any custom vars
        subprocess_env = os.environ.copy()
        if env:
            subprocess_env.update(env)

        try:
            # Use asyncio.create_subprocess_shell for async execution
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=subprocess_env,
                cwd=os.path.expanduser("~"),  # Start in home directory
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()
                return CommandResult(
                    return_code=-1,
                    stdout="",
                    stderr="",
                    error_message=f"Command timed out after {timeout} seconds",
                    session_id=None,
                    command=command,
                    status=BashCommandStatus.HARD_TIMEOUT,
                )

            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""

            return CommandResult(
                return_code=process.returncode or 0,
                stdout=stdout_str,
                stderr=stderr_str,
                session_id=None,
                command=command,
                status=BashCommandStatus.COMPLETED,
            )

        except Exception as e:
            self._log(f"Subprocess execution error: {str(e)}")
            return CommandResult(
                return_code=1,
                error_message=f"Error executing command in subprocess: {str(e)}",
                session_id=None,
                command=command,
                status=BashCommandStatus.COMPLETED,
            )
