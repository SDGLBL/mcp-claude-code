from mcp.server.fastmcp import FastMCP

COMPACT_CONVERSATION_PROMPT = """Please create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions.
This summary should be thorough in capturing technical details, code patterns, and architectural decisions that would be essential for continuing development work without losing context.

Before providing your final summary, wrap your analysis in <analysis> tags to organize your thoughts and ensure you've covered all necessary points. In your analysis process:

1. Chronologically analyze each message and section of the conversation. For each section thoroughly identify:
 - The user's explicit requests and intents
 - Your approach to addressing the user's requests
 - Key decisions, technical concepts and code patterns
 - Specific details like file names, full code snippets, function signatures, file edits, etc
2. Double-check for technical accuracy and completeness, addressing each required element thoroughly.

Your summary should include the following sections:

1. Primary Request and Intent: Capture all of the user's explicit requests and intents in detail
2. Key Technical Concepts: List all important technical concepts, technologies, and frameworks discussed.
3. Files and Code Sections: Enumerate specific files and code sections examined, modified, or created. Pay special attention to the most recent messages and include full code snippets where applicable and include a summary of why this file read or edit is important.
4. Problem Solving: Document problems solved and any ongoing troubleshooting efforts.
5. Pending Tasks: Outline any pending tasks that you have explicitly been asked to work on.
6. Current Work: Describe in detail precisely what was being worked on immediately before this summary request, paying special attention to the most recent messages from both user and assistant. Include file names and code snippets where applicable.
7. Optional Next Step: List the next step that you will take that is related to the most recent work you were doing. IMPORTANT: ensure that this step is DIRECTLY in line with the user's explicit requests, and the task you were working on immediately before this summary request. If your last task was concluded, then only list next steps if they are explicitly in line with the users request. Do not start on tangential requests without confirming with the user first.
 If there is a next step, include direct quotes from the most recent conversation showing exactly what task you were working on and where you left off. This should be verbatim to ensure there's no drift in task interpretation.

Here's an example of how your output should be structured:

<example>
## analysis

<analysis>
[Your thought process, ensuring all points are covered thoroughly and accurately]
</analysis>

## summary
<summary>
1. Primary Request and Intent:
 [Detailed description]

2. Key Technical Concepts:
 - [Concept 1]
 - [Concept 2]
 - [...]

3. Files and Code Sections:
 - [File Name 1]
 - [Summary of why this file is important]
 - [Summary of the changes made to this file, if any]
 - [Important Code Snippet]
 - [File Name 2]
 - [Important Code Snippet]
 - [...]

4. Problem Solving:
 [Description of solved problems and ongoing troubleshooting]

5. Pending Tasks:
 - [Task 1]
 - [Task 2]
 - [...]

6. Current Work:
 [Precise description of current work]

7. Optional Next Step:
 [Optional Next step to take]

</summary>
</example>

Please provide your summary based on the conversation so far, following this structure and ensuring precision and thoroughness in your response. 

There may be additional summarization instructions provided in the included context. If so, remember to follow these instructions when creating the above summary. Examples of instructions include:
<example>
## Compact Instructions
When summarizing the conversation focus on typescript code changes and also remember the mistakes you made and how you fixed them.
</example>

<example>
# Summary instructions
When you are using compact - please focus on test output and code changes. Include file reads verbatim.
</example>"""

CREATE_RELEASE_PROMPT = """Help me create a new release for my project. Follow these steps to guide me through the process:

## Initial Analysis
1. Examine the project version files (typically `__init__.py`, `package.json`, `pyproject.toml`, etc.)
2. Review the current CHANGELOG.md format and previous releases
3. Check the release workflow configuration (GitHub Actions, CI/CD pipelines)
4. Review commits since the last release tag:
   ```bash
   git log <last-tag>..HEAD --pretty=format:"%h %s%n%b" --name-status
   ```

## Version Update
1. Identify all files containing version numbers
2. Update version numbers consistently across all files
3. Follow semantic versioning guidelines (MAJOR.MINOR.PATCH)

## Changelog Creation
1. Add a new section at the top of CHANGELOG.md with the new version and today's date
2. Group changes by type: Added, Changed, Fixed, Removed, etc.
3. Include commit hashes in parentheses for reference
4. Write clear, detailed descriptions for each change
5. Follow established project conventions for changelog format

## Release Commit and Tag
1. Commit the version and changelog updates:
   ```bash
   git add <changed-files>
   git commit -m "chore: bump version to X.Y.Z"
   ```
2. Create an annotated tag:
   ```bash
   git tag -a "vX.Y.Z" -m "Release vX.Y.Z"
   ```
3. Push the changes and tag:
   ```bash
   git push origin main
   git push origin vX.Y.Z
   ```

Guide me through each step, examining my project structure to determine the appropriate files to modify and explaining any decisions you make along the way."""


def register_all_prompts(mcp_server: FastMCP) -> None:
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

    return


__all__ = ["register_all_prompts"]
