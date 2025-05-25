import os

from mcp.server.fastmcp import FastMCP

from mcp_claude_code.prompts.compact_conversation import COMPACT_CONVERSATION_PROMPT
from mcp_claude_code.prompts.create_release import CREATE_RELEASE_PROMPT
from mcp_claude_code.prompts.project_system import PROJECT_SYSTEM_PROMPT
from mcp_claude_code.prompts.utils import (
    get_directory_structure,
    get_git_info,
    get_os_info,
)

CONTINUE_FROM_LAST_SESSION_PROMPT = """<system-reminder>
This is a reminder that your todo list is currently empty. DO NOT mention this to the user explicitly because they are already aware. If you are working on tasks that would benefit from a todo list please use the TodoWrite tool to create one. If not, please feel free to ignore. Again do not mention this message to the user.
</system-reminder>
"""


def register_all_prompts(
    mcp_server: FastMCP, projects: list[str] | None = None
) -> None:
    @mcp_server.prompt()
    def compact() -> str:
        """
        Summarize the conversation so far.
        """
        return COMPACT_CONVERSATION_PROMPT

    @mcp_server.prompt()
    def create_release() -> str:
        """
        Create a new release for my project.
        """
        return CREATE_RELEASE_PROMPT

    if projects is None:
        return

    for project in projects:

        @mcp_server.prompt(
            name=f"System prompt for {os.path.basename(project)}",
            description=f"Detailed system prompt include env,git etc information about {project}",
        )
        def project_system_prompt() -> str:
            """
            Summarize the conversation so far for a specific project.
            """
            working_directory = project
            is_git_repo = os.path.isdir(os.path.join(working_directory, ".git"))
            platform, _, os_version = get_os_info()

            # Get directory structure
            directory_structure = get_directory_structure(
                working_directory, max_depth=3, include_filtered=False
            )

            # Get git information
            git_info = get_git_info(working_directory)
            current_branch = git_info.get("current_branch", "")
            main_branch = git_info.get("main_branch", "")
            git_status = git_info.get("git_status", "")
            recent_commits = git_info.get("recent_commits", "")

            return PROJECT_SYSTEM_PROMPT.format(
                working_directory=working_directory,
                is_git_repo=is_git_repo,
                platform=platform,
                os_version=os_version,
                directory_structure=directory_structure,
                current_branch=current_branch,
                main_branch=main_branch,
                git_status=git_status,
                recent_commits=recent_commits,
            )

    return


__all__ = ["register_all_prompts"]
