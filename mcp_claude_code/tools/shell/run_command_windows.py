"""Run command tool implementation for Windows compatibility.

This module provides the RunCommandTool for running shell commands on Windows.
"""

import os
from typing import Annotated, Any, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.common.base import handle_connection_errors
from mcp_claude_code.tools.common.context import create_tool_context
from mcp_claude_code.tools.shell.base import ShellBaseTool
from mcp_claude_code.tools.shell.command_executor import CommandExecutor


@final
class RunCommandTool(ShellBaseTool):
    """Tool for executing shell commands."""

    def __init__(
        self, permission_manager: Any, command_executor: CommandExecutor
    ) -> None:
        """Initialize the run command tool.

        Args:
            permission_manager: Permission manager for access control
            command_executor: Command executor for running commands
        """
        super().__init__(permission_manager)
        self.command_executor: CommandExecutor = command_executor

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
        return """Executes a given bash command in a shell with optional timeout, ensuring proper handling and security measures.

Before executing the command, please follow these steps:

1. Directory Verification:
   - If the command will create new directories or files, first use the directory_tree tool to verify the parent directory exists and is the correct location
   - For example, before running \"mkdir foo/bar\", first use directory_tree to check that \"foo\" exists and is the intended parent directory

2. Command Execution:
   - After ensuring proper quoting, execute the command.
   - Capture the output of the command.

Usage notes:
  - The command argument is required.
  - You can specify an optional timeout in milliseconds (up to 600000ms / 10 minutes). If not specified, commands will timeout after 120000ms (2 minutes).
  - It is very helpful if you write a clear, concise description of what this command does in 5-10 words.
  - If the output exceeds 30000 characters, output will be truncated before being returned to you.
  - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Instead use Grep, Glob, or Task to search. You MUST avoid read tools like `cat`, `head`, `tail`, and `ls`, and use read and directory_tree to read files.
  - If you _still_ need to run `grep`, STOP. ALWAYS USE ripgrep at `rg` (or /opt/homebrew/Cellar/ripgrep/14.1.1/bin/rg) first, which all Claude Code users have pre-installed.
  - When issuing multiple commands, use the ';' or '&&' operator to separate them. DO NOT use newlines (newlines are ok in quoted strings).
    <good-example>
    cd /foo/bar && pytest tests
    </good-example>


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

   🤖 Generated with [MCP Claude Code](https://github.com/SDGLBL/mcp-claude-code)

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
    async def call(self, ctx: MCPContext, **params: Any) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = await self.prepare_tool_context(ctx)

        # Extract parameters
        command = params.get("command")
        cwd = params.get("cwd")
        shell_type = params.get("shell_type")
        use_login_shell = params.get("use_login_shell", True)

        # Validate required parameters
        if not command:
            await tool_ctx.error("Parameter 'command' is required but was None")
            return "Error: Parameter 'command' is required but was None"

        if command.strip() == "":
            await tool_ctx.error("Parameter 'command' cannot be empty")
            return "Error: Parameter 'command' cannot be empty"

        if not cwd:
            await tool_ctx.error("Parameter 'cwd' is required but was None")
            return "Error: Parameter 'cwd' is required but was None"

        if cwd.strip() == "":
            await tool_ctx.error("Parameter 'cwd' cannot be empty")
            return "Error: Parameter 'cwd' cannot be empty"

        await tool_ctx.info(f"Executing command: {command}")

        # Check if command is allowed
        if not self.command_executor.is_command_allowed(command):
            await tool_ctx.error(f"Command not allowed: {command}")
            return f"Error: Command not allowed: {command}"

        # Check if working directory is allowed
        if not self.is_path_allowed(cwd):
            await tool_ctx.error(f"Working directory not allowed: {cwd}")
            return f"Error: Working directory not allowed: {cwd}"

        # Check if working directory exists
        if not os.path.isdir(cwd):
            await tool_ctx.error(f"Working directory does not exist: {cwd}")
            return f"Error: Working directory does not exist: {cwd}"

        # Execute the command
        result = await self.command_executor.execute_command(
            command,
            cwd=cwd,
            shell_type=shell_type,
            timeout=120.0,  # Increased from 30s to 120s for better compatibility
            use_login_shell=use_login_shell,
        )

        # Report result
        if result.is_success:
            await tool_ctx.info("Command executed successfully")
        else:
            await tool_ctx.error(f"Command failed with exit code {result.return_code}")

        # Format the result
        if result.is_success:
            # For successful commands, just return stdout unless stderr has content
            if result.stderr:
                return f"Command executed successfully.\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            return result.stdout
        else:
            # For failed commands, include all available information
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
            command: Annotated[
                str,
                Field(
                    description="The shell command to execute",
                    min_length=1,
                ),
            ],
            cwd: Annotated[
                str,
                Field(
                    description="Working directory where the command should be executed",
                    min_length=1,
                ),
            ],
            shell_type: Annotated[
                str | None,
                Field(
                    description="Type of shell to use (e.g., bash, zsh). Defaults to system default",
                    default=None,
                ),
            ] = None,
            use_login_shell: Annotated[
                bool,
                Field(
                    description="Whether to use a login shell (default: True)",
                    default=True,
                ),
            ] = True,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(
                ctx,
                command=command,
                cwd=cwd,
                shell_type=shell_type,
                use_login_shell=use_login_shell,
            )
