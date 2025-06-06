"""Run command tool implementation.

This module provides the RunCommandTool for running shell commands.
"""

from typing import Annotated, Any, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.common.base import handle_connection_errors
from mcp_claude_code.tools.common.context import create_tool_context
from mcp_claude_code.tools.shell.base import ShellBaseTool
from mcp_claude_code.tools.shell.bash_session_executor import BashSessionExecutor

Command = Annotated[
    str,
    Field(
        description="The shell command to execute",
        min_length=1,
    ),
]


SessionID = Annotated[
    str,
    Field(
        description="Session ID for persistent shell sessions (generate using timestamp command).",
    ),
]

TimeOut = Annotated[
    int,
    Field(
        description="Timeout in seconds for session-based commands with no output changes (default: 30)",
        default=30,
    ),
]

IsInput = Annotated[
    bool,
    Field(
        description="Whether this is input to a running process rather than a new command (default: False)",
        default=False,
    ),
]

Blocking = Annotated[
    bool,
    Field(
        description="Whether to run in blocking mode, ignoring no-change timeout (default: False)",
        default=False,
    ),
]


class RunCommandToolParams(TypedDict):
    """Parameters for the RunCommandTool.

    Attributes:
        command: The shell command to execute
        session_id: Optional session ID for persistent shell sessions
        time_out: Timeout in seconds for session-based commands with no output changes
        is_input: Whether this is input to a running process rather than a new command
        blocking: Whether to run in blocking mode, ignoring no-change timeout
    """

    command: Command
    session_id: SessionID
    time_out: TimeOut
    is_input: IsInput
    blocking: Blocking


@final
class RunCommandTool(ShellBaseTool):
    """Tool for executing shell commands."""

    def __init__(
        self, permission_manager: Any, command_executor: BashSessionExecutor
    ) -> None:
        """Initialize the run command tool.

        Args:
            permission_manager: Permission manager for access control
            command_executor: Command executor for running commands
        """
        super().__init__(permission_manager)
        self.command_executor: BashSessionExecutor = command_executor

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "run_command"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Executes a given bash command in a persistent shell session with advanced interactive process handling, ensuring proper handling and security measures.

Before executing the command, please follow these steps:

1. Directory Verification:
   - If the command will create new directories or files, first use the directory_tree tool to verify the parent directory exists and is the correct location
   - For example, before running \"mkdir foo/bar\", first use directory_tree to check that \"foo\" exists and is the intended parent directory

2. Command Execution:
   - After ensuring proper quoting, execute the command.
   - Capture the output of the command.

Usage notes:
  - The command argument is required.
  - session_id: Optional string for persistent sessions (e.g., "my-session-123")
  - time_out: Timeout in seconds for commands with no output changes (default: 30)
  - is_input: Set to true when sending input to a running process rather than executing a new command
  - blocking: Set to true to ignore no-change timeout for long-running commands
  - It is very helpful if you write a clear, concise description of what this command does in 5-10 words.
  - If the output exceeds 30000 characters, output will be truncated before being returned to you.
  
Interactive Process Handling:
  - When a command is running and waiting for input, use is_input=true to send responses
  - Commands like vim, nano, python REPL, and other interactive programs require is_input=true for interaction
  - Use blocking=true for commands that legitimately take a long time without output
  - Send control sequences (\"C-c\", \"C-z\", \"C-d\") as commands with is_input=true to interrupt processes
  - The tool prevents sending new commands while a previous command is still running (use is_input=true to interact)
  
  VERY IMPORTANT: You MUST avoid using search commands like `grep`. Instead use grep, or dispatch_agent to search. You MUST avoid read tools like `cat`, `head`, `tail`, and `ls`, and use read and directory_tree to read files.
  - If you _still_ need to run `grep`, STOP. ALWAYS USE ripgrep at `rg` first, which all Claude Code users have pre-installed.
  - When issuing multiple commands, use the ';' or '&&' operator to separate them. DO NOT use newlines (newlines are ok in quoted strings).
  - Working Directory: New sessions start in the user's home directory. Use 'cd' commands to navigate to different directories within a session. Directory changes persist within the same session.
    <good-example>
    cd /foo/bar && pytest tests
    </good-example>
    <good-example>
    pytest tests # Second running do not need cd 
    </good-example>
    <bad-example>
    pytest /foo/bar/tests  # This works but doesn't change the session's working directory
    </bad-example>

# Committing changes with git

When the user asks you to create a new git commit, follow these steps carefully:

1. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following bash commands in parallel, each using the Bash tool:
   - Run a git status command to see all untracked files.
   - Run a git diff command to see both staged and unstaged changes that will be committed.
   - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.

2. Analyze all staged changes (both previously staged and newly added) and draft a commit message. Wrap your analysis process in <commit_analysis> tags:

<commit_analysis>
- List the files that have been changed or added
- Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.)
- Brainstorm the purpose or motivation behind these changes
- Assess the impact of these changes on the overall project
- Check for any sensitive information that shouldn't be committed
- Draft a concise (1-2 sentences) commit message that focuses on the \"why\" rather than the \"what\"
- Ensure your language is clear, concise, and to the point
- Ensure the message accurately reflects the changes and their purpose (i.e. \"add\" means a wholly new feature, \"update\" means an enhancement to an existing feature, \"fix\" means a bug fix, etc.)
- Ensure the message is not generic (avoid words like \"Update\" or \"Fix\" without context)
- Review the draft message to ensure it accurately reflects the changes and their purpose
</commit_analysis>

3. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following commands in parallel:
   - Add relevant untracked files to the staging area.
   - Create the commit with a message ending with:
   🤖 Generated with [Claude Code](https://claude.ai/code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   - Run git status to make sure the commit succeeded.

4. If the commit fails due to pre-commit hook changes, retry the commit ONCE to include these automated changes. If it fails again, it usually means a pre-commit hook is preventing the commit. If the commit succeeds but you notice that files were modified by the pre-commit hook, you MUST amend your commit to include them.

Important notes:
- Use the git context at the start of this conversation to determine which files are relevant to your commit. Be careful not to stage and commit files (e.g. with `git add .`) that aren't relevant to your commit.
- NEVER update the git config
- DO NOT run additional commands to read or explore code, beyond what is available in the git context
- DO NOT push to the remote repository
- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.
- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit
- Ensure your commit message is meaningful and concise. It should explain the purpose of the changes, not just describe them.
- Return an empty response - the user will see the git output directly
- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:
<example>
git commit -m \"$(cat <<'EOF'
   Commit message here.

   🤖 Generated with [Claude Code](https://claude.ai/code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )\"
</example>

# Creating pull requests
Use the gh command via the Bash tool for ALL GitHub-related tasks including working with issues, pull requests, checks, and releases. If given a Github URL use the gh command to get the information needed.

IMPORTANT: When the user asks you to create a pull request, follow these steps carefully:

1. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following bash commands in parallel using the Bash tool, in order to understand the current state of the branch since it diverged from the main branch:
   - Run a git status command to see all untracked files
   - Run a git diff command to see both staged and unstaged changes that will be committed
   - Check if the current branch tracks a remote branch and is up to date with the remote, so you know if you need to push to the remote
   - Run a git log command and `git diff main...HEAD` to understand the full commit history for the current branch (from the time it diverged from the `main` branch)

2. Analyze all changes that will be included in the pull request, making sure to look at all relevant commits (NOT just the latest commit, but ALL commits that will be included in the pull request!!!), and draft a pull request summary. Wrap your analysis process in <pr_analysis> tags:

<pr_analysis>
- List the commits since diverging from the main branch
- Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.)
- Brainstorm the purpose or motivation behind these changes
- Assess the impact of these changes on the overall project
- Do not use tools to explore code, beyond what is available in the git context
- Check for any sensitive information that shouldn't be committed
- Draft a concise (1-2 bullet points) pull request summary that focuses on the \"why\" rather than the \"what\"
- Ensure the summary accurately reflects all changes since diverging from the main branch
- Ensure your language is clear, concise, and to the point
- Ensure the summary accurately reflects the changes and their purpose (ie. \"add\" means a wholly new feature, \"update\" means an enhancement to an existing feature, \"fix\" means a bug fix, etc.)
- Ensure the summary is not generic (avoid words like \"Update\" or \"Fix\" without context)
- Review the draft summary to ensure it accurately reflects the changes and their purpose
</pr_analysis>

3. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following commands in parallel:
   - Create new branch if needed
   - Push to remote with -u flag if needed
   - Create PR using gh pr create with the format below. Use a HEREDOC to pass the body to ensure correct formatting.
<example>
gh pr create --title \"the pr title\" --body \"$(cat <<'EOF'
## Summary
<1-3 bullet points>

## Test plan
[Checklist of TODOs for testing the pull request...]

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)\"
</example>

Important:
- NEVER update the git config
- Return the PR URL when you're done, so the user can see it

# Other common operations
- View comments on a Github PR: gh api repos/foo/bar/pulls/123/comments"""

    @override
    async def prepare_tool_context(self, ctx: MCPContext) -> Any:
        """Create and prepare the tool context.

        Args:
            ctx: MCP context

        Returns:
            Prepared tool context
        """
        tool_ctx = create_tool_context(ctx)
        tool_ctx.set_tool_info(self.name)
        return tool_ctx

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[RunCommandToolParams],
    ) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = await self.prepare_tool_context(ctx)

        # Extract parameters
        command = params["command"]
        session_id = params.get("session_id")
        time_out = params.get("time_out", 30)
        is_input = params.get("is_input", False)
        blocking = params.get("blocking", False)

        await tool_ctx.info(
            f"Executing command: {command} ( session_id={session_id}, is_input={is_input}, blocking={blocking} )"
        )

        # Check if command is allowed (skip for input to running processes)
        if not is_input and not self.command_executor.is_command_allowed(command):
            await tool_ctx.error(f"Command not allowed: {command}")
            return f"Error: Command not allowed: {command}"

        try:
            # Execute command using BashSessionExecutor with enhanced parameters
            result = await self.command_executor.execute_command(
                command=command,
                timeout=time_out,
                session_id=session_id,
                is_input=is_input,
                blocking=blocking,
            )
        except RuntimeError as e:
            await tool_ctx.error(f"Session execution failed: {str(e)}")
            return f"Error: Session execution failed: {str(e)}"

        # Format the result using the new enhanced formatting
        if result.is_success:
            # Use the enhanced agent observation format for better user experience
            return result.to_agent_observation()
        else:
            # For failed or running commands, provide comprehensive output
            return result.format_output()

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this run command tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.description)
        @handle_connection_errors
        async def run_command(
            command: Command,
            session_id: SessionID,
            time_out: TimeOut,
            is_input: IsInput,
            blocking: Blocking,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(
                ctx,
                command=command,
                session_id=session_id,
                time_out=time_out,
                is_input=is_input,
                blocking=blocking,
            )
