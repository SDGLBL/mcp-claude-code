"""Bash session management using tmux for persistent shell environments.

This module provides the BashSession class which creates and manages persistent
shell sessions using tmux, inspired by OpenHands' BashSession implementation.
"""

import os
import re
import time
import uuid
from enum import Enum
from typing import Any

import bashlex  # type: ignore
import libtmux

from mcp_claude_code.tools.shell.base import CommandResult


def split_bash_commands(commands: str) -> list[str]:
    """Split bash commands using bashlex parser.

    Args:
        commands: The command string to split

    Returns:
        List of individual commands
    """
    if not commands.strip():
        return [""]
    try:
        parsed = bashlex.parse(commands)
    except (bashlex.errors.ParsingError, NotImplementedError, TypeError):
        # If parsing fails, return the original commands
        return [commands]

    result: list[str] = []
    last_end = 0

    for node in parsed:
        start, end = node.pos

        # Include any text between the last command and this one
        if start > last_end:
            between = commands[last_end:start]
            if result:
                result[-1] += between.rstrip()
            elif between.strip():
                result.append(between.rstrip())

        # Extract the command, preserving original formatting
        command = commands[start:end].rstrip()
        result.append(command)

        last_end = end

    # Add any remaining text after the last command to the last command
    remaining = commands[last_end:].rstrip()
    if last_end < len(commands) and result:
        result[-1] += remaining
    elif last_end < len(commands):
        if remaining:
            result.append(remaining)
    return result


def escape_bash_special_chars(command: str) -> str:
    """Escape characters that have different interpretations in bash vs python.

    Args:
        command: The command to escape

    Returns:
        Escaped command string
    """
    if command.strip() == "":
        return ""

    try:
        parts = []
        last_pos = 0

        def visit_node(node: Any) -> None:
            nonlocal last_pos
            if (
                node.kind == "redirect"
                and hasattr(node, "heredoc")
                and node.heredoc is not None
            ):
                # We're entering a heredoc - preserve everything as-is until we see EOF
                between = command[last_pos : node.pos[0]]
                parts.append(between)
                # Add the heredoc start marker
                parts.append(command[node.pos[0] : node.heredoc.pos[0]])
                # Add the heredoc content as-is
                parts.append(command[node.heredoc.pos[0] : node.heredoc.pos[1]])
                last_pos = node.pos[1]
                return

            if node.kind == "word":
                # Get the raw text between the last position and current word
                between = command[last_pos : node.pos[0]]
                word_text = command[node.pos[0] : node.pos[1]]

                # Add the between text, escaping special characters
                between = re.sub(r"\\([;&|><])", r"\\\\\1", between)
                parts.append(between)

                # Check if word_text is a quoted string or command substitution
                if (
                    (word_text.startswith('"') and word_text.endswith('"'))
                    or (word_text.startswith("'") and word_text.endswith("'"))
                    or (word_text.startswith("$(") and word_text.endswith(")"))
                    or (word_text.startswith("`") and word_text.endswith("`"))
                ):
                    # Preserve quoted strings, command substitutions, and heredoc content as-is
                    parts.append(word_text)
                else:
                    # Escape special chars in unquoted text
                    word_text = re.sub(r"\\([;&|><])", r"\\\\\1", word_text)
                    parts.append(word_text)

                last_pos = node.pos[1]
                return

            # Visit child nodes
            if hasattr(node, "parts"):
                for part in node.parts:
                    visit_node(part)

        # Process all nodes in the AST
        nodes = list(bashlex.parse(command))
        for node in nodes:
            between = command[last_pos : node.pos[0]]
            between = re.sub(r"\\([;&|><])", r"\\\\\1", between)
            parts.append(between)
            last_pos = node.pos[0]
            visit_node(node)

        # Handle any remaining text after the last word
        remaining = command[last_pos:]
        parts.append(remaining)
        return "".join(parts)
    except (bashlex.errors.ParsingError, NotImplementedError, TypeError):
        return command


class BashCommandStatus(Enum):
    """Status of bash command execution."""

    CONTINUE = "continue"
    COMPLETED = "completed"
    NO_CHANGE_TIMEOUT = "no_change_timeout"
    HARD_TIMEOUT = "hard_timeout"


class CmdOutputMetadata:
    """Metadata captured from command execution."""

    def __init__(
        self,
        exit_code: int = -1,
        pid: int = -1,
        username: str | None = None,
        hostname: str | None = None,
        working_dir: str | None = None,
        py_interpreter_path: str | None = None,
        prefix: str = "",
        suffix: str = "",
    ):
        self.exit_code = exit_code
        self.pid = pid
        self.username = username
        self.hostname = hostname
        self.working_dir = working_dir
        self.py_interpreter_path = py_interpreter_path
        self.prefix = prefix
        self.suffix = suffix


def _remove_command_prefix(command_output: str, command: str) -> str:
    """Remove the command prefix from output."""
    return command_output.lstrip().removeprefix(command.lstrip()).lstrip()


class BashSession:
    """Persistent bash session using tmux.

    This class provides a persistent shell environment where commands maintain
    shared history, environment variables, and working directory state.
    """

    POLL_INTERVAL = 0.5
    HISTORY_LIMIT = 10_000
    PS1 = r"\u@\h:\w\$ "  # Simple PS1 for now

    def __init__(
        self,
        work_dir: str,
        username: str | None = None,
        no_change_timeout_seconds: int = 30,
        max_memory_mb: int | None = None,
    ):
        """Initialize a bash session.

        Args:
            work_dir: Working directory for the session
            username: Username to run commands as
            no_change_timeout_seconds: Timeout for commands with no output changes
            max_memory_mb: Memory limit (not implemented yet)
        """
        self.NO_CHANGE_TIMEOUT_SECONDS = no_change_timeout_seconds
        self.work_dir = work_dir
        self.username = username
        self._initialized = False
        self.max_memory_mb = max_memory_mb

        # Session state
        self.prev_status: BashCommandStatus | None = None
        self.prev_output: str = ""
        self._closed: bool = False
        self._cwd = os.path.abspath(work_dir)

        # tmux components
        self.server: libtmux.Server | None = None
        self.session: libtmux.Session | None = None
        self.window: libtmux.Window | None = None
        self.pane: libtmux.Pane | None = None

    def initialize(self) -> None:
        """Initialize the tmux session."""
        if self._initialized:
            return

        self.server = libtmux.Server()
        _shell_command = "/bin/bash"

        if self.username in ["root", "openhands"]:
            # This starts a non-login (new) shell for the given user
            _shell_command = f"su {self.username} -"

        window_command = _shell_command
        session_name = f"mcp-claude-code-{self.username or 'default'}-{uuid.uuid4()}"

        self.session = self.server.new_session(
            session_name=session_name,
            start_directory=self.work_dir,
            kill_session=True,
            x=1000,
            y=1000,
        )

        # Set history limit to a large number to avoid losing history
        self.session.set_option("history-limit", str(self.HISTORY_LIMIT), global_=True)
        self.session.history_limit = self.HISTORY_LIMIT

        # We need to create a new pane because the initial pane's history limit is (default) 2000
        _initial_window = self.session.active_window
        self.window = self.session.new_window(
            window_name="bash",
            window_shell=window_command,
            start_directory=self.work_dir,
        )
        self.pane = self.window.active_pane
        _initial_window.kill_window()

        # Configure bash to use simple PS1
        self.pane.send_keys(f'export PS1="{self.PS1}"; export PS2=""')
        time.sleep(0.1)  # Wait for command to take effect
        self._clear_screen()

        self._initialized = True

    def __del__(self) -> None:
        """Ensure the session is closed when the object is destroyed."""
        self.close()

    def _get_pane_content(self) -> str:
        """Capture the current pane content."""
        if not self.pane:
            return ""

        content = "\n".join(
            map(
                lambda line: line.rstrip(),
                self.pane.cmd("capture-pane", "-J", "-pS", "-").stdout,
            )
        )
        return content

    def close(self) -> None:
        """Clean up the session."""
        if self._closed or not self.session:
            return
        try:
            self.session.kill_session()
        except Exception:
            pass  # Ignore cleanup errors
        self._closed = True

    @property
    def cwd(self) -> str:
        """Get current working directory."""
        return self._cwd

    def _is_special_key(self, command: str) -> bool:
        """Check if the command is a special key."""
        _command = command.strip()
        return _command.startswith("C-") and len(_command) == 3

    def _clear_screen(self) -> None:
        """Clear the tmux pane screen and history."""
        if not self.pane:
            return
        self.pane.send_keys("C-l", enter=False)
        time.sleep(0.1)
        self.pane.cmd("clear-history")

    def execute(
        self,
        command: str,
        is_input: bool = False,
        blocking: bool = False,
        timeout: float | None = None,
    ) -> CommandResult:
        """Execute a command in the bash session.

        Args:
            command: Command to execute
            is_input: Whether this is input to a running process
            blocking: Whether to run in blocking mode
            timeout: Hard timeout for command execution

        Returns:
            CommandResult with execution results
        """
        if not self._initialized:
            self.initialize()

        # Strip the command of any leading/trailing whitespace
        command = command.strip()

        # Check if the command is a single command or multiple commands
        splited_commands = split_bash_commands(command)
        if len(splited_commands) > 1:
            return CommandResult(
                return_code=1,
                error_message=(
                    f"ERROR: Cannot execute multiple commands at once.\n"
                    f"Please run each command separately OR chain them into a single command via && or ;\n"
                    f"Provided commands:\n{'\n'.join(f'({i + 1}) {cmd}' for i, cmd in enumerate(splited_commands))}"
                ),
            )

        # Get initial state before sending command
        initial_pane_output = self._get_pane_content()
        start_time = time.time()
        last_change_time = start_time
        last_pane_output = initial_pane_output

        # Send command/inputs to the pane
        if command != "":
            is_special_key = self._is_special_key(command)
            if is_input:
                self.pane.send_keys(command, enter=not is_special_key)
            else:
                # Escape command for bash
                command_escaped = escape_bash_special_chars(command)
                self.pane.send_keys(command_escaped, enter=not is_special_key)

        # Wait for completion with simple polling
        while True:
            time.sleep(self.POLL_INTERVAL)
            cur_pane_output = self._get_pane_content()

            if cur_pane_output != last_pane_output:
                last_pane_output = cur_pane_output
                last_change_time = time.time()

            # Check if command completed (simple heuristic: output ends with prompt)
            # Look for the PS1 prompt pattern or a simple $ prompt
            if (
                cur_pane_output.rstrip().endswith("$ ")
                or cur_pane_output.rstrip().endswith("$")
                or "@" in cur_pane_output
                and cur_pane_output.rstrip().endswith("$ ")
            ):
                # Extract command output (everything before the final prompt)
                lines = cur_pane_output.strip().split("\n")
                if len(lines) > 1:
                    # Remove the last line (prompt) and join the rest
                    output = "\n".join(lines[:-1])
                    # Remove the command itself from the beginning
                    output = _remove_command_prefix(output, command)
                else:
                    output = ""

                return CommandResult(
                    return_code=0,  # Assume success for now
                    stdout=output.strip(),
                    stderr="",
                )

            # Check for no-change timeout
            time_since_last_change = time.time() - last_change_time
            if (
                not blocking
                and time_since_last_change >= self.NO_CHANGE_TIMEOUT_SECONDS
            ):
                # Extract current output
                lines = cur_pane_output.strip().split("\n")
                output = "\n".join(lines)
                output = _remove_command_prefix(output, command)

                return CommandResult(
                    return_code=-1,
                    stdout=output.strip(),
                    stderr="",
                    error_message=f"Command timed out after {self.NO_CHANGE_TIMEOUT_SECONDS} seconds with no output changes",
                )

            # Check for hard timeout
            if timeout and (time.time() - start_time) >= timeout:
                lines = cur_pane_output.strip().split("\n")
                output = "\n".join(lines)
                output = _remove_command_prefix(output, command)

                return CommandResult(
                    return_code=-1,
                    stdout=output.strip(),
                    stderr="",
                    error_message=f"Command timed out after {timeout} seconds",
                )
