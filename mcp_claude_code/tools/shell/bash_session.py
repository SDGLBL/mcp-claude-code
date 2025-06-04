"""Bash session management using tmux for persistent shell environments.

This module provides the BashSession class which creates and manages persistent
shell sessions using tmux, inspired by OpenHands' BashSession implementation.
"""

import os
import re
import time
import uuid
from typing import Any, final

import bashlex  # type: ignore
import libtmux

from mcp_claude_code.tools.shell.base import (
    BashCommandStatus,
    CommandResult,
)


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


def _remove_command_prefix(command_output: str, command: str) -> str:
    """Remove the command prefix from output."""
    return command_output.lstrip().removeprefix(command.lstrip()).lstrip()


@final
class BashSession:
    """Persistent bash session using tmux.

    This class provides a persistent shell environment where commands maintain
    shared history, environment variables, and working directory state.
    """

    HISTORY_LIMIT = 10_000
    # Use simple PS1 for now to avoid shell compatibility issues
    PS1 = "$ "  # Simple PS1 for better compatibility

    def __init__(
        self,
        id: str,
        work_dir: str,
        username: str | None = None,
        no_change_timeout_seconds: int = 30,
        max_memory_mb: int | None = None,
        poll_interval: float = 0.5,
    ):
        """Initialize a bash session.

        Args:
            work_dir: Working directory for the session
            username: Username to run commands as
            no_change_timeout_seconds: Timeout for commands with no output changes
            max_memory_mb: Memory limit (not implemented yet)
            poll_interval: Interval between polls in seconds (default 0.5, use 0.1 for tests)
        """
        self.POLL_INTERVAL = poll_interval
        self.NO_CHANGE_TIMEOUT_SECONDS = no_change_timeout_seconds
        self.id = id
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
        # Use the user's current shell, fallback to /bin/bash
        user_shell = os.environ.get("SHELL", "/bin/bash")
        _shell_command = user_shell

        if self.username in ["root"]:
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
        self.session.history_limit = str(self.HISTORY_LIMIT)

        # We need to create a new pane because the initial pane's history limit is (default) 2000
        _initial_window = self.session.active_window
        self.window = self.session.new_window(
            window_name="bash",
            window_shell=window_command,
            start_directory=self.work_dir,
        )
        self.pane = self.window.active_pane
        _initial_window.kill_window()

        assert self.pane

        # Configure bash to use simple PS1 and disable PS2
        # Use a simpler PS1 that works reliably across different shells
        self.pane.send_keys('export PS1="$ "')
        # Set PS2 to empty
        self.pane.send_keys('export PS2=""')
        # For zsh, also set PROMPT and disable themes
        self.pane.send_keys('export PROMPT="$ "')
        self.pane.send_keys("unset ZSH_THEME")
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

        # If the previous command is not completed, check if we can proceed
        if self.prev_status not in {
            BashCommandStatus.CONTINUE,
            BashCommandStatus.NO_CHANGE_TIMEOUT,
            BashCommandStatus.HARD_TIMEOUT,
        }:
            if is_input:
                return CommandResult(
                    return_code=1,
                    error_message="ERROR: No previous running command to interact with.",
                    command=command,
                    status=BashCommandStatus.COMPLETED,
                    session_id=self.id,
                )
            if command == "":
                return CommandResult(
                    return_code=1,
                    error_message="ERROR: No previous running command to retrieve logs from.",
                    command=command,
                    status=BashCommandStatus.COMPLETED,
                    session_id=self.id,
                )

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
                command=command,
                status=BashCommandStatus.COMPLETED,
                session_id=self.id,
            )

        # Get initial state before sending command
        initial_pane_output = self._get_pane_content()

        start_time = time.time()
        last_change_time = start_time
        last_pane_output = initial_pane_output

        assert self.pane

        # When prev command is still running and we're trying to send a new command
        if (
            self.prev_status
            in {
                BashCommandStatus.HARD_TIMEOUT,
                BashCommandStatus.NO_CHANGE_TIMEOUT,
            }
            and not is_input
            and command != ""
        ):
            return self._handle_command_conflict(command, last_pane_output)

        # Send actual command/inputs to the pane
        if command != "":
            is_special_key = self._is_special_key(command)
            if is_input:
                self.pane.send_keys(command, enter=not is_special_key)
            else:
                # Escape command for bash
                command_escaped = escape_bash_special_chars(command)
                self.pane.send_keys(command_escaped, enter=not is_special_key)

        # Loop until the command completes or times out
        while True:
            time.sleep(self.POLL_INTERVAL)
            cur_pane_output = self._get_pane_content()

            if cur_pane_output != last_pane_output:
                last_pane_output = cur_pane_output
                last_change_time = time.time()

            # 1) Execution completed: Use broader prompt detection
            # Check for various prompt patterns that might be used
            prompt_patterns = [
                "$ ",  # bash default
                "$",  # bash without space
                "% ",  # zsh default
                "%",  # zsh without space
                "❯ ",  # oh-my-zsh
                "❯",  # oh-my-zsh without space
                "> ",  # generic
                ">",  # generic without space
            ]
            output_ends_with_prompt = any(
                cur_pane_output.rstrip().endswith(pattern)
                for pattern in prompt_patterns
            )

            # Also check for username@hostname pattern (common in many shells)
            has_user_host_pattern = "@" in cur_pane_output and any(
                cur_pane_output.rstrip().endswith(indicator)
                for indicator in prompt_patterns
            )

            if output_ends_with_prompt or has_user_host_pattern:
                return self._fallback_completion_detection(command, cur_pane_output)

            # 2) No-change timeout (only if not blocking)
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
                    error_message=f"no new output after {self.NO_CHANGE_TIMEOUT_SECONDS} seconds",
                    command=command,
                    status=BashCommandStatus.NO_CHANGE_TIMEOUT,
                    session_id=self.id,
                )

            # 3) Hard timeout
            elapsed_time = time.time() - start_time
            if timeout and elapsed_time >= timeout:
                lines = cur_pane_output.strip().split("\n")
                output = "\n".join(lines)
                output = _remove_command_prefix(output, command)

                return CommandResult(
                    return_code=-1,
                    stdout=output.strip(),
                    stderr="",
                    error_message=f"Command timed out after {timeout} seconds",
                    command=command,
                    status=BashCommandStatus.HARD_TIMEOUT,
                    session_id=self.id,
                )

    def _handle_command_conflict(self, command: str, pane_output: str) -> CommandResult:
        """Handle conflicts when trying to send a new command while previous is running."""
        # Extract current output directly
        lines = pane_output.strip().split("\n")
        raw_command_output = "\n".join(lines)
        raw_command_output = _remove_command_prefix(raw_command_output, command)

        command_output = self._get_command_output(
            command,
            raw_command_output,
            continue_prefix="[Below is the output of the previous command.]\n",
        )

        # Add suffix message about command conflict
        command_output += (
            f'\n[Your command "{command}" is NOT executed. '
            f"The previous command is still running - You CANNOT send new commands until the previous command is completed. "
            "By setting `is_input` to `true`, you can interact with the current process: "
            "You may wait longer to see additional output of the previous command by sending empty command '', "
            "send other commands to interact with the current process, "
            'or send keys ("C-c", "C-z", "C-d") to interrupt/kill the previous command before sending your new command.]'
        )

        return CommandResult(
            return_code=1,
            stdout=command_output,
            command=command,
            status=BashCommandStatus.CONTINUE,
            session_id=self.id,
        )

    def _handle_nochange_timeout_command(
        self, command: str, pane_content: str
    ) -> CommandResult:
        """Handle a command that timed out due to no output changes."""
        self.prev_status = BashCommandStatus.NO_CHANGE_TIMEOUT

        # Extract current output directly
        lines = pane_content.strip().split("\n")
        raw_command_output = "\n".join(lines)
        raw_command_output = _remove_command_prefix(raw_command_output, command)

        command_output = self._get_command_output(
            command,
            raw_command_output,
            continue_prefix="[Below is the output of the previous command.]\n",
        )

        # Add timeout message
        command_output += (
            f"\n[The command has no new output after {self.NO_CHANGE_TIMEOUT_SECONDS} seconds. "
            "You may wait longer to see additional output by sending empty command '', "
            "send other commands to interact with the current process, "
            "or send keys to interrupt/kill the command.]"
        )

        return CommandResult(
            return_code=-1,
            stdout=command_output,
            command=command,
            status=BashCommandStatus.NO_CHANGE_TIMEOUT,
            session_id=self.id,
        )

    def _handle_hard_timeout_command(
        self, command: str, pane_content: str, timeout: float
    ) -> CommandResult:
        """Handle a command that hit the hard timeout."""
        self.prev_status = BashCommandStatus.HARD_TIMEOUT

        # Extract current output directly
        lines = pane_content.strip().split("\n")
        raw_command_output = "\n".join(lines)
        raw_command_output = _remove_command_prefix(raw_command_output, command)

        command_output = self._get_command_output(
            command,
            raw_command_output,
            continue_prefix="[Below is the output of the previous command.]\n",
        )

        # Add timeout message
        command_output += (
            f"\n[The command timed out after {timeout} seconds. "
            "You may wait longer to see additional output by sending empty command '', "
            "send other commands to interact with the current process, "
            "or send keys to interrupt/kill the command.]"
        )

        return CommandResult(
            return_code=-1,
            stdout=command_output,
            command=command,
            status=BashCommandStatus.HARD_TIMEOUT,
            session_id=self.id,
        )

    def _fallback_completion_detection(
        self, command: str, pane_content: str
    ) -> CommandResult:
        """Fallback completion detection when PS1 metadata is not available."""
        # Use the old logic as fallback
        self.pane.send_keys("echo EXIT_CODE:$?", enter=True)
        time.sleep(0.1)

        exit_code_output = self._get_pane_content()
        exit_code = 0
        for line in exit_code_output.split("\n"):
            if line.strip().startswith("EXIT_CODE:"):
                try:
                    exit_code = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    exit_code = 0
                break

        # Improved output extraction for complex shells like oh-my-zsh
        output = self._extract_clean_output(pane_content, command)

        self.prev_status = BashCommandStatus.COMPLETED  # Set prev_status
        self.prev_output = ""  # Reset previous command output

        # Clear screen and history to prevent output accumulation
        self._ready_for_next_command()

        return CommandResult(
            return_code=exit_code,
            stdout=output.strip(),
            stderr="",
            command=command,
            status=BashCommandStatus.COMPLETED,
            session_id=self.id,
        )

    def _get_command_output(
        self,
        command: str,
        raw_command_output: str,
        continue_prefix: str = "",
    ) -> str:
        """Get the command output with the previous command output removed."""
        # Remove the previous command output from the new output if any
        if self.prev_output:
            command_output = raw_command_output.removeprefix(self.prev_output)
            # Add continue prefix if we're continuing from previous output
            if continue_prefix:
                command_output = continue_prefix + command_output
        else:
            command_output = raw_command_output

        self.prev_output = raw_command_output  # Update current command output
        command_output = _remove_command_prefix(command_output, command)
        return command_output.rstrip()

    def _ready_for_next_command(self) -> None:
        """Reset the content buffer for a new command."""
        self._clear_screen()

    def _extract_clean_output(self, pane_content: str, command: str) -> str:
        """Extract clean command output from pane content, handling complex shells like oh-my-zsh."""
        lines = pane_content.split("\n")

        # Find lines that contain the actual command execution
        command_line_indices = []
        for i, line in enumerate(lines):
            # Look for lines that contain the command (after prompt symbols)
            stripped_line = line.strip()
            # Check if line contains the command after removing common prompt symbols
            clean_line = stripped_line
            for prompt_symbol in ["❯", "$", "%", ">"]:
                if clean_line.startswith(prompt_symbol):
                    clean_line = clean_line[len(prompt_symbol) :].strip()
                    break

            if clean_line == command.strip():
                command_line_indices.append(i)

        if not command_line_indices:
            # Fallback to simple extraction if we can't find the command
            return self._simple_output_extraction(lines, command)

        # Take the output after the last command line
        last_command_index = command_line_indices[-1]
        output_lines = []
        decorative_line_count = 0
        max_decorative_lines = 2  # Allow a few decorative lines before stopping

        # Look for output lines immediately after the command
        for i in range(last_command_index + 1, len(lines)):
            line = lines[i]
            stripped_line = line.strip()

            # Stop if we hit a new prompt line
            if self._is_prompt_line(stripped_line):
                break

            # Handle decorative lines more intelligently
            if self._is_decorative_line(stripped_line):
                decorative_line_count += 1
                # If we haven't found any output yet, or we've seen too many decorative lines, stop
                if not output_lines or decorative_line_count > max_decorative_lines:
                    if output_lines:  # We have some output, stop here
                        break
                    else:  # No output yet, but too many decorative lines, give up
                        continue
                else:
                    # We have some output and this is an occasional decorative line, include it
                    output_lines.append(line.rstrip())
                    continue
            else:
                # Reset decorative line count when we see non-decorative content
                decorative_line_count = 0

            # Skip empty lines at the beginning only
            if not output_lines and not stripped_line:
                continue

            # Add the line to output (preserve original formatting)
            output_lines.append(line.rstrip())

        return "\n".join(output_lines).rstrip()

    def _simple_output_extraction(self, lines: list[str], command: str) -> str:
        """Simple fallback output extraction."""
        if len(lines) > 1:
            output = "\n".join(lines[:-1])
            return _remove_command_prefix(output, command)
        return ""

    def _is_prompt_line(self, line: str) -> bool:
        """Check if a line looks like a shell prompt."""
        stripped = line.strip()

        # Check for common prompt patterns
        prompt_indicators = ["❯", "$", "%", ">"]
        for indicator in prompt_indicators:
            if stripped.startswith(indicator) and len(stripped) > len(indicator):
                return True

        # Check for user@host patterns
        if "@" in stripped and any(stripped.endswith(ind) for ind in prompt_indicators):
            return True

        return False

    def _is_decorative_line(self, line: str) -> bool:
        """Check if a line is decorative (like oh-my-zsh decorations)."""
        stripped = line.strip()

        # Check for lines that are mostly special characters or dots
        if len(stripped) > 20:  # Long lines are likely decorative
            special_chars = sum(1 for c in stripped if c in "·─═━┌┐└┘├┤┬┴┼▄▀█░▒▓")
            if special_chars > len(stripped) * 0.5:  # More than 50% special chars
                return True

        # Check for lines containing time stamps or status info
        if "at " in stripped and ("AM" in stripped or "PM" in stripped):
            return True

        # Check for virtual environment deactivation messages
        if "Deactivating:" in line or "_default_venv:" in line:
            return True

        return False
