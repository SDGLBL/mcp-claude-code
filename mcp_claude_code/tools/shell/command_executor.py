"""Command executor tools for MCP Claude Code.

This module provides tools for executing shell commands and scripts with
comprehensive error handling, permissions checking, and progress tracking.
"""

import asyncio
import base64
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Awaitable, Callable
from typing import Dict, Optional, final

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.common.context import create_tool_context
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.shell.base import CommandResult


@final
class CommandExecutor:
    """Command executor tools for MCP Claude Code.

    This class provides tools for executing shell commands and scripts with
    comprehensive error handling, permissions checking, and progress tracking.
    """

    def __init__(
        self, permission_manager: PermissionManager, verbose: bool = False
    ) -> None:
        """Initialize command execution.

        Args:
            permission_manager: Permission manager for access control
            verbose: Enable verbose logging
        """
        self.permission_manager: PermissionManager = permission_manager
        self.verbose: bool = verbose

        # Excluded commands or patterns
        self.excluded_commands: list[str] = ["rm"]

        # Map of supported interpreters with special handling
        self.special_interpreters: Dict[
            str,
            Callable[
                [str, str, str], dict[str, str]
            ] | Awaitable[CommandResult],
        ] = {
            "fish": self._handle_fish_script,
        }

    def _get_shell_by_type(self, shell_type: str) -> tuple[str, str]:
        """Get shell information for a specified shell type.
        
        Args:
            shell_type: The shell name to use (e.g., "bash", "cmd", "powershell")
            
        Returns:
            Tuple of (shell_basename, shell_path)
        """
        shell_path = shutil.which(shell_type)
        if shell_path is None:
            # Shell not found, fall back to default
            self._log(f"Requested shell '{shell_type}' not found, using system default")
            return self._get_system_shell()
        
        if sys.platform == "win32":
            shell_path = shell_path.lower()
        
        shell_basename = os.path.basename(shell_path).lower()
        return shell_basename, shell_path

    def _get_system_shell(self, shell_type: str | None = None) -> tuple[str, str]:
        """Get the system's default shell based on the platform.
        
        Args:
            shell_type: Optional specific shell to use instead of system default
            
        Returns:
            Tuple of (shell_basename, shell_path)
        """
        # If a specific shell is requested, use that
        if shell_type is not None:
            return self._get_shell_by_type(shell_type)
            
        # Otherwise use system default
        if sys.platform == "win32":
            # On Windows, default to Command Prompt
            comspec = os.environ.get("COMSPEC", "cmd.exe").lower()
            return "cmd", comspec
        else:
            # Unix systems
            user_shell = os.environ.get("SHELL", "/bin/bash")
            return os.path.basename(user_shell).lower(), user_shell
        
    def _format_win32_shell_command(self, shell_basename, user_shell, command, use_login_shell=True):
        """Format a command for execution with the appropriate Windows shell.

        Args:
            shell_basename: The basename of the shell
            user_shell: The full path to the shell
            command: The command to execute
            use_login_shell: Whether to use login shell settings
            
        Returns:
            Formatted shell command string
        """
        formatted_command = ""

        if shell_basename in ["wsl", "wsl.exe"]:
            # For WSL, handle commands with shell operators differently
            if any(char in command for char in ";&|<>(){}[]$\"'`"):
                # For commands with special characters, use a more reliable approach
                # with bash -c and double quotes around the entire command
                escaped_command = command.replace('"', '\\"')
                if use_login_shell:
                    formatted_command = f'{user_shell} bash -l -c "{escaped_command}"'
                else:
                    formatted_command = f'{user_shell} bash -c "{escaped_command}"'
            else:
                # # For simple commands without special characters
                # # Still respect login shell preference
                # if use_login_shell:
                #     formatted_command = f"{user_shell} bash -l -c \"{command}\""
                # else:
                formatted_command = f"{user_shell} {command}"

        elif shell_basename in ["powershell", "powershell.exe", "pwsh", "pwsh.exe"]:
            # For PowerShell, escape double quotes with backslash most robust
            escaped_command = command.replace('"', '\\"')
            formatted_command = f'"{user_shell}" -Command "{escaped_command}"'

        else:
            # For CMD, use the /c parameter and wrap in double quotes
            # CMD doesn't have an explicit login shell concept
            formatted_command = f'"{user_shell}" /c "{command}"'

        self._log("Win32 Shell Results", {
            "shell_basename": shell_basename,
            "user_shell": user_shell,
            "command": command,
            "use_login_shell": use_login_shell,
            "formatted_command": formatted_command,
        })

        return formatted_command

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
                print(f"DEBUG: {message}: {data_str}", file=sys.stderr)
            except Exception:
                print(f"DEBUG: {message}: {data}", file=sys.stderr)
        else:
            print(f"DEBUG: {message}", file=sys.stderr)

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
        cwd: str | None = None,
        shell_type: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = 60.0,
        use_login_shell: bool = True,
    ) -> CommandResult:
        """Execute a shell command with safety checks.

        Args:
            command: The command to execute
            cwd: Optional working directory
            env: Optional environment variables
            timeout: Optional timeout in seconds
            use_login_shell: Whether to use login shell. default true (loads ~/.zshrc, ~/.bashrc, etc.)
            shell_type: Optional shell to use (e.g., "cmd", "powershell", "wsl", "bash")

        Returns:
            CommandResult containing execution results
        """
        self._log(f"Executing command: {command}")

        # Check if the command is allowed
        if not self.is_command_allowed(command):
            return CommandResult(
                return_code=1, error_message=f"Command not allowed: {command}"
            )

        # Check working directory permissions if specified
        if cwd:
            if not os.path.isdir(cwd):
                return CommandResult(
                    return_code=1,
                    error_message=f"Working directory does not exist: {cwd}",
                )

            if not self.permission_manager.is_path_allowed(cwd):
                return CommandResult(
                    return_code=1, error_message=f"Working directory not allowed: {cwd}"
                )

        # Set up environment
        command_env: dict[str, str] = os.environ.copy()
        if env:
            command_env.update(env)

        try:
            # Get shell information
            shell_basename, user_shell = self._get_system_shell(shell_type)
            
            if sys.platform == "win32":
                # On Windows, always use shell execution
                self._log(f"Using shell on Windows: {user_shell} ({shell_basename})")
                
                # Format command using helper method
                shell_cmd = self._format_win32_shell_command(
                    shell_basename, user_shell, command, use_login_shell
                )

                # Use shell for command execution
                process = await asyncio.create_subprocess_shell(
                    shell_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=command_env,
                )
            else:
                # Unix systems - original logic
                shell_operators = ["&&", "||", "|", ";", ">", "<", "$(", "`", "$"]
                needs_shell = any(op in command for op in shell_operators)

                if needs_shell or use_login_shell:
                    # Determine which shell to use
                    shell_cmd = command

                    if use_login_shell:
                        self._log(f"Using login shell: {user_shell} ({shell_basename})")

                        # Wrap command with appropriate shell invocation
                        if shell_basename == "zsh":
                            shell_cmd = f"{user_shell} -l -c '{command}'"
                        elif shell_basename == "bash":
                            shell_cmd = f"{user_shell} -l -c '{command}'"
                        elif shell_basename == "fish":
                            shell_cmd = f"{user_shell} -l -c '{command}'"
                        else:
                            # Default fallback
                            shell_cmd = f"{user_shell} -c '{command}'"
                    else:
                        self._log(
                            f"Using shell for command with shell operators: {command}"
                        )

                    # Use shell for command execution
                    process = await asyncio.create_subprocess_shell(
                        shell_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                        env=command_env,
                    )
                else:
                    # Split the command into arguments for regular commands
                    args: list[str] = shlex.split(command)

                    # Create and run the process without shell
                    process = await asyncio.create_subprocess_exec(
                        *args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                        env=command_env,
                    )

            # Wait for the process to complete with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                return CommandResult(
                    return_code=process.returncode or 0,
                    stdout=stdout_bytes.decode("utf-8", errors="replace"),
                    stderr=stderr_bytes.decode("utf-8", errors="replace"),
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                try:
                    process.kill()
                except ProcessLookupError:
                    pass  # Process already terminated

                return CommandResult(
                    return_code=-1,
                    error_message=f"Command timed out after {timeout} seconds: {command}",
                )
        except Exception as e:
            self._log(f"Command execution error: {str(e)}")
            return CommandResult(
                return_code=1, error_message=f"Error executing command: {str(e)}"
            )

    async def execute_script(
        self,
        script: str,
        interpreter: str = "bash",
        cwd: str | None = None,
        shell_type: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = 60.0,
        use_login_shell: bool = True
    ) -> CommandResult:
        """Execute a script with the specified interpreter.

        Args:
            script: The script content to execute
            interpreter: The interpreter to use (bash, python, etc.)
            cwd: Optional working directory
            shell_type: Optional shell to use (e.g., "cmd", "powershell", "wsl", "bash")
            env: Optional environment variables
            timeout: Optional timeout in seconds
            use_login_shell: Whether to use login shell (loads ~/.zshrc, ~/.bashrc, etc.)

        Returns:
            CommandResult containing execution results
        """
        self._log(f"Executing script with interpreter: {interpreter}")

        # Check working directory permissions if specified
        if cwd:
            if not os.path.isdir(cwd):
                return CommandResult(
                    return_code=1,
                    error_message=f"Working directory does not exist: {cwd}",
                )

            if not self.permission_manager.is_path_allowed(cwd):
                return CommandResult(
                    return_code=1, error_message=f"Working directory not allowed: {cwd}"
                )

        # Check if we need special handling for this interpreter
        interpreter_name = interpreter.split()[0].lower()
        if interpreter_name in self.special_interpreters:
            self._log(f"Using special handler for interpreter: {interpreter_name}")
            special_handler = self.special_interpreters[interpreter_name]
            return await special_handler(interpreter, script, cwd, env, timeout)

        # Regular execution
        return await self._execute_script_with_stdin(
            interpreter, script, cwd, shell_type, env, timeout, use_login_shell
        )

    async def _execute_script_with_stdin(
        self,
        interpreter: str,
        script: str,
        cwd: str | None = None,
        shell_type: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = 60.0,
        use_login_shell: bool = True
    ) -> CommandResult:
        """Execute a script by passing it to stdin of the interpreter.

        Args:
            interpreter: The interpreter command
            script: The script content
            cwd: Optional working directory
            shell_type: Optional shell to use (e.g., "cmd", "powershell", "wsl", "bash")
            env: Optional environment variables
            timeout: Optional timeout in seconds
            use_login_shell: Whether to use login shell (loads ~/.zshrc, ~/.bashrc, etc.)

        Returns:
            CommandResult containing execution results
        """
        # Set up environment
        command_env: dict[str, str] = os.environ.copy()
        if env:
            command_env.update(env)

        try:
            # Get shell information
            shell_basename, user_shell = self._get_system_shell(shell_type)
            
            if sys.platform == "win32":
                # On Windows, always use shell
                self._log(f"Using shell on Windows for interpreter: {user_shell}")
                
                # Format command using helper method for the interpreter
                shell_cmd = self._format_win32_shell_command(
                    shell_basename, user_shell, interpreter, use_login_shell
                )
                
                # Create and run the process with shell
                process = await asyncio.create_subprocess_shell(
                    shell_cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=command_env,
                )
            else:
                # Unix systems - original logic
                if use_login_shell:
                    self._log(f"Using login shell for interpreter: {user_shell}")

                    # Create command that pipes script to interpreter through login shell
                    shell_cmd = f"{user_shell} -l -c '{interpreter}'"

                    # Create and run the process with shell
                    process = await asyncio.create_subprocess_shell(
                        shell_cmd,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                        env=command_env,
                    )
                else:
                    # Parse the interpreter command to get arguments
                    interpreter_parts = shlex.split(interpreter)

                    # Create and run the process normally
                    process = await asyncio.create_subprocess_exec(
                        *interpreter_parts,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                        env=command_env,
                    )

            # Wait for the process to complete with timeout
            try:
                script_bytes: bytes = script.encode("utf-8")
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(script_bytes), timeout=timeout
                )

                return CommandResult(
                    return_code=process.returncode or 0,
                    stdout=stdout_bytes.decode("utf-8", errors="replace"),
                    stderr=stderr_bytes.decode("utf-8", errors="replace"),
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                try:
                    process.kill()
                except ProcessLookupError:
                    pass  # Process already terminated

                return CommandResult(
                    return_code=-1,
                    error_message=f"Script execution timed out after {timeout} seconds",
                )
        except Exception as e:
            self._log(f"Script execution error: {str(e)}")
            return CommandResult(
                return_code=1, error_message=f"Error executing script: {str(e)}"
            )

    async def _handle_fish_script(
        self,
        interpreter: str,
        script: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = 60.0,
    ) -> CommandResult:
        """Special handler for Fish shell scripts.

        The Fish shell has issues with piped input in some contexts, so we use
        a workaround that base64 encodes the script and decodes it in the pipeline.

        Args:
            interpreter: The fish interpreter command
            script: The fish script content
            cwd: Optional working directory
            env: Optional environment variables
            timeout: Optional timeout in seconds

        Returns:
            CommandResult containing execution results
        """
        self._log("Using Fish shell workaround")

        # Set up environment
        command_env: dict[str, str] = os.environ.copy()
        if env:
            command_env.update(env)

        try:
            # Base64 encode the script to avoid stdin issues with Fish
            base64_script = base64.b64encode(script.encode("utf-8")).decode("utf-8")

            # Create a command that decodes the script and pipes it to fish
            command = f'{interpreter} -c "echo {base64_script} | base64 -d | fish"'
            self._log(f"Fish command: {command}")

            # Create and run the process
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=command_env,
            )

            # Wait for the process to complete with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                return CommandResult(
                    return_code=process.returncode or 0,
                    stdout=stdout_bytes.decode("utf-8", errors="replace"),
                    stderr=stderr_bytes.decode("utf-8", errors="replace"),
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                try:
                    process.kill()
                except ProcessLookupError:
                    pass  # Process already terminated

                return CommandResult(
                    return_code=-1,
                    error_message=f"Fish script execution timed out after {timeout} seconds",
                )
        except Exception as e:
            self._log(f"Fish script execution error: {str(e)}")
            return CommandResult(
                return_code=1, error_message=f"Error executing Fish script: {str(e)}"
            )

    async def execute_script_from_file(
        self,
        script: str,
        language: str,
        cwd: str | None = None,
        shell_type: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = 60.0,
        args: list[str] | None = None,
        use_login_shell: bool = True,
    ) -> CommandResult:
        """Execute a script by writing it to a temporary file and executing it.

        This is useful for languages where the script is too complex or long
        to pass via stdin, or for languages that have limitations with stdin.

        Args:
            script: The script content
            language: The script language (determines file extension and interpreter)
            cwd: Optional working directory
            shell_type: Optional shell to use (e.g., "cmd", "powershell", "wsl", "bash")
            env: Optional environment variables
            timeout: Optional timeout in seconds
            args: Optional command-line arguments
            use_login_shell: Whether to use login shell. default true (loads ~/.zshrc, ~/.bashrc, etc.)

        Returns:
            CommandResult containing execution results
        """
        # Get language info from the centralized language map
        language_map = self._get_language_map()
        
        # Check if the language is supported
        if language not in language_map:
            return CommandResult(
                return_code=1,
                error_message=f"Unsupported language: {language}. Supported languages: {', '.join(language_map.keys())}",
            )

        # Get language info
        language_info = language_map[language]
        extension = language_info["extension"]
        
        # Get interpreter command with full path if possible
        command, language_args = self._get_interpreter_path(language, shell_type)

        self._log(f"Interpreter path: {command} :: {language_args}")

        # Set up environment
        command_env: dict[str, str] = os.environ.copy()
        if env:
            command_env.update(env)

        # Create a temporary file for the script
        with tempfile.NamedTemporaryFile(
            suffix=extension, mode="w", delete=False
        ) as temp:
            temp_path = temp.name
            _ = temp.write(script)  # Explicitly ignore the return value

        try:
            # Normalize path for the current OS
            temp_path = os.path.normpath(temp_path)
            original_temp_path = temp_path

            if sys.platform == "win32":
                # Windows always uses shell
                shell_basename, user_shell = self._get_system_shell(shell_type)

                # Convert Windows path to WSL path if using WSL
                if shell_basename in ["wsl", "wsl.exe"]:

                    match = re.match(r"([a-zA-Z]):\\(.*)", temp_path)
                    if match:
                        drive, path = match.groups()
                        wsl_path = f"/mnt/{drive.lower()}/{path.replace('\\', '/')}"
                    else:
                        wsl_path = temp_path.replace("\\", "/")
                        self._log(f"WSL path conversion may be incomplete: {wsl_path}")

                    self._log(f"Converted Windows path '{temp_path}' to WSL path '{wsl_path}'")
                    temp_path = wsl_path
                
                # Build the command including args
                cmd = f"{command} {temp_path}"
                if language_args:
                    cmd = f"{command} {' '.join(language_args)} {temp_path}"
                if args:
                    cmd += " " + " ".join(args)
                
                # Format command using helper method
                shell_cmd = self._format_win32_shell_command(
                    shell_basename, user_shell, cmd, use_login_shell
                )
                
                self._log(f"Executing script from file on Windows with shell: {shell_cmd}")
                
                # Create and run the process with shell
                process = await asyncio.create_subprocess_shell(
                    shell_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=command_env,
                )
            else:
                # Unix systems - original logic
                if use_login_shell:
                    # Get the user's login shell
                    shell_basename, user_shell = self._get_system_shell(shell_type)

                    # Build the command including args
                    cmd = f"{command} {temp_path}"
                    if language_args:
                        cmd = f"{command} {' '.join(language_args)} {temp_path}"
                    if args:
                        cmd += " " + " ".join(args)

                    # Create command that runs script through login shell
                    shell_cmd = f"{user_shell} -l -c '{cmd}'"

                    self._log(f"Executing script from file with login shell: {shell_cmd}")

                    # Create and run the process with shell
                    process = await asyncio.create_subprocess_shell(
                        shell_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                        env=command_env,
                    )
                else:
                    # Build command arguments
                    cmd_args = [command] + language_args + [temp_path]
                    if args:
                        cmd_args.extend(args)

                    self._log(f"Executing script from file with: {' '.join(cmd_args)}")

                    # Create and run the process normally
                    process = await asyncio.create_subprocess_exec(
                        *cmd_args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                        env=command_env,
                    )

            # Wait for the process to complete with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                return CommandResult(
                    return_code=process.returncode or 0,
                    stdout=stdout_bytes.decode("utf-8", errors="replace"),
                    stderr=stderr_bytes.decode("utf-8", errors="replace"),
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                try:
                    process.kill()
                except ProcessLookupError:
                    pass  # Process already terminated

                return CommandResult(
                    return_code=-1,
                    error_message=f"Script execution timed out after {timeout} seconds",
                )
        except Exception as e:
            self._log(f"Script file execution error: {str(e)}")
            return CommandResult(
                return_code=1, error_message=f"Error executing script: {str(e)}"
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(original_temp_path)
            except Exception as e:
                self._log(f"Error cleaning up temporary file: {str(e)}")

    def _get_language_map(self) -> dict[str, dict[str, str | list[str]]]:
        """Get the mapping of languages to interpreter information.
        
        This is a single source of truth for language mappings used by
        both execute_script_from_file and get_available_languages.
        
        Returns:
            Dictionary mapping language names to interpreter information
        """
        return {
            "python": {
                "command": "python",
                "extension": ".py",
                "alternatives": ["python3"]  # Alternative command names to try
            },
            "javascript": {
                "command": "node",
                "extension": ".js",
                "alternatives": ["nodejs"]
            },
            "typescript": {
                "command": "ts-node",
                "extension": ".ts",
            },
            "bash": {
                "command": "bash",
                "extension": ".sh",
            },
            "fish": {
                "command": "fish",
                "extension": ".fish",
            },
            "ruby": {
                "command": "ruby",
                "extension": ".rb",
            },
            "php": {
                "command": "php",
                "extension": ".php",
            },
            "perl": {
                "command": "perl",
                "extension": ".pl",
            },
            "r": {
                "command": "Rscript",
                "extension": ".R",
                "alternatives": ["R"]
            },
            # Windows-specific languages
            "batch": {
                "command": "cmd.exe",
                "extension": ".bat",
                "args": ["/c"],
            },
            "powershell": {
                "command": "powershell.exe",
                "extension": ".ps1",
                "args": ["-ExecutionPolicy", "Bypass", "-File"],
                "alternatives": ["pwsh.exe", "pwsh"]
            },
        }
    
    def _get_interpreter_path(self, language: str, shell_type: str | None = None) -> tuple[str, list[str]]:
        """Get the full path to the interpreter for the given language.
        
        Attempts to find the full path to the interpreter command, but only for
        Windows shell types (cmd, powershell). For WSL, just returns the command name.
        
        Args:
            language: The language name (e.g., "python", "javascript")
            shell_type: Optional shell type (e.g., "wsl", "cmd", "powershell")
            
        Returns:
            Tuple of (interpreter_command, args) where:
              - interpreter_command is either the full path to the interpreter or the command name
              - args is a list of additional arguments to pass to the interpreter
        """
        language_map = self._get_language_map()
        
        if language not in language_map:
            # Return the language name itself as a fallback
            return language, []
            
        language_info = language_map[language]
        command = language_info["command"]
        args = language_info.get("args", [])
        alternatives = language_info.get("alternatives", [])
        
        # Special handling for WSL - use command name directly (not Windows paths)
        if shell_type and shell_type.lower() in ["wsl", "wsl.exe"]:
            # For Python specifically, use python3 in WSL environments
            if language.lower() == "python":
                return "python3", args
            # For other languages, just use the command name
            return command, args
            
        # For Windows shell types, try to find the full path
        if sys.platform == "win32" and (not shell_type or shell_type.lower() in ["cmd", "powershell", "cmd.exe", "powershell.exe"]):
            try:
                # Try to find the full path to the command
                full_path = shutil.which(command)
                if full_path:
                    self._log(f"Found full path for {language} interpreter: {full_path}")
                    return full_path, args
                    
                # If primary command not found, try alternatives
                for alt_command in alternatives:
                    alt_path = shutil.which(alt_command)
                    if alt_path:
                        self._log(f"Found alternative path for {language} interpreter: {alt_path}")
                        return alt_path, args
            except Exception as e:
                self._log(f"Error finding path for {language} interpreter: {str(e)}")
        
        # If we can't find the full path or it's not appropriate, return the command name
        self._log(f"Using command name for {language} interpreter: {command}")
        return command, args

    def get_available_languages(self) -> list[str]:
        """Get a list of available script languages.

        Returns:
            List of supported language names
        """
        # Use the centralized language map
        return list(self._get_language_map().keys())

    # Legacy method to keep backwards compatibility with tests
    def register_tools(self, mcp_server: FastMCP) -> None:
        """Register command execution tools with the MCP server.
        
        Legacy method for backwards compatibility with existing tests.
        New code should use the modular tool classes instead.

        Args:
            mcp_server: The FastMCP server instance
        """
        # Run Command Tool - keep original method names for test compatibility
        @mcp_server.tool()
        async def run_command(
            command: str,
            cwd: str,
            ctx: MCPContext,
            shell_type: str | None = None,
            use_login_shell: bool = True
        ) -> str:
            tool_ctx = create_tool_context(ctx)
            tool_ctx.set_tool_info("run_command")
            await tool_ctx.info(f"Executing command: {command}")

            # Run validations and execute
            result = await self.execute_command(
                command, 
                cwd, 
                shell_type=shell_type,
                timeout=30.0, 
                use_login_shell=use_login_shell
            )
            
            if result.is_success:
                return result.stdout
            else:
                return result.format_output()
                
        # Run Script Tool
        @mcp_server.tool()
        async def run_script(
            script: str,
            cwd: str,
            ctx: MCPContext,
            shell_type: str | None = None,
            interpreter: str = "bash",
            use_login_shell: bool = True
        ) -> str:
            tool_ctx = create_tool_context(ctx)
            tool_ctx.set_tool_info("run_script")
            
            # Execute the script
            result = await self.execute_script(
                script=script,
                interpreter=interpreter,
                cwd=cwd,
                shell_type=shell_type,
                timeout=30.0,
                use_login_shell=use_login_shell,
            )
            if result.is_success:
                return result.stdout
            else:
                return result.format_output()

        # Script tool for executing scripts in various languages
        @mcp_server.tool()
        async def script_tool(
            language: str,
            script: str,
            cwd: str,
            ctx: MCPContext,
            shell_type: str | None = None,
            args: list[str] | None = None,
            use_login_shell: bool = True
        ) -> str:
            tool_ctx = create_tool_context(ctx)
            tool_ctx.set_tool_info("script_tool")
            
            # Execute the script
            result = await self.execute_script_from_file(
                script=script,
                language=language,
                cwd=cwd,
                shell_type=shell_type,
                timeout=30.0,
                args=args,
                use_login_shell=use_login_shell
            )
            
            if result.is_success:
                return result.stdout
            else:
                return result.format_output()
