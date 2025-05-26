"""Edit tool implementation.

This module provides the edit tool for making precise text replacements in files.
Converted to FastMCP v2 function-based pattern.
"""

from difflib import unified_diff
from pathlib import Path

from fastmcp import Context as MCPContext
from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import (
    get_document_context,
    is_path_allowed,
    validate_path,
)
from mcp_claude_code.tools.common.context import create_tool_context


async def edit(
    file_path: str,
    old_string: str,
    new_string: str,
    ctx: MCPContext,
    expected_replacements: int = 1,
) -> str:
    """Performs exact string replacements in files with strict occurrence count validation.

    Usage:
    - When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
    - ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.

    Args:
        file_path: The absolute path to the file to modify (must be absolute, not relative)
        old_string: The text to replace (must match the file contents exactly, including all whitespace and indentation)
        new_string: The edited text to replace the old_string
        expected_replacements: The expected number of replacements to perform. Defaults to 1 if not specified.
        ctx: MCP context for the tool call

    Returns:
        Result of the operation
    """
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("edit")

    if not file_path:
        await tool_ctx.error("Parameter 'file_path' is required but was None")
        return "Error: Parameter 'file_path' is required but was None"

    if file_path.strip() == "":
        await tool_ctx.error("Parameter 'file_path' cannot be empty")
        return "Error: Parameter 'file_path' cannot be empty"

    # Validate parameters
    path_validation = validate_path(file_path)
    if path_validation.is_error:
        await tool_ctx.error(path_validation.error_message)
        return f"Error: {path_validation.error_message}"

    if old_string is None:
        await tool_ctx.error("Parameter 'old_string' is required but was None")
        return "Error: Parameter 'old_string' is required but was None"

    # Only validate old_string for non-empty if we're not creating a new file
    # Empty old_string is valid when creating a new file
    file_exists = Path(file_path).exists()
    if file_exists and old_string.strip() == "":
        await tool_ctx.error(
            "Parameter 'old_string' cannot be empty for existing files"
        )
        return "Error: Parameter 'old_string' cannot be empty for existing files"

    if new_string is None:
        await tool_ctx.error("Parameter 'new_string' is required but was None")
        return "Error: Parameter 'new_string' is required but was None"

    if (
        expected_replacements is None
        or not isinstance(expected_replacements, (int, float))
        or expected_replacements < 0
    ):
        await tool_ctx.error(
            "Parameter 'expected_replacements' must be a non-negative number"
        )
        return "Error: Parameter 'expected_replacements' must be a non-negative number"

    await tool_ctx.info(f"Editing file: {file_path}")

    # Check if file is allowed to be edited
    if not is_path_allowed(file_path):
        await tool_ctx.error(
            f"Access denied - path outside allowed directories: {file_path}"
        )
        return f"Error: Access denied - path outside allowed directories: {file_path}"

    try:
        file_path_obj = Path(file_path)

        # If the file doesn't exist and old_string is empty, create a new file
        if not file_path_obj.exists() and old_string == "":
            # Check if parent directory is allowed
            parent_dir = str(file_path_obj.parent)
            if not is_path_allowed(parent_dir):
                await tool_ctx.error(f"Parent directory not allowed: {parent_dir}")
                return f"Error: Parent directory not allowed: {parent_dir}"

            # Create parent directories if they don't exist
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Create the new file with the new_string content
            with open(file_path_obj, "w", encoding="utf-8") as f:
                f.write(new_string)

            # Add to document context
            document_context = get_document_context()
            document_context.add_document(file_path, new_string)

            await tool_ctx.info(f"Successfully created file: {file_path}")
            return f"Successfully created file: {file_path} ({len(new_string)} bytes)"

        # Check file exists for non-creation operations
        if not file_path_obj.exists():
            await tool_ctx.error(f"File does not exist: {file_path}")
            return f"Error: File does not exist: {file_path}"

        # Check is a file
        if not file_path_obj.is_file():
            await tool_ctx.error(f"Path is not a file: {file_path}")
            return f"Error: Path is not a file: {file_path}"

        # Read the file
        try:
            with open(file_path_obj, "r", encoding="utf-8") as f:
                original_content = f.read()

            # Apply edit
            if old_string in original_content:
                # Count occurrences of the old_string in the content
                occurrences = original_content.count(old_string)

                # Check if the number of occurrences matches expected_replacements
                if occurrences != expected_replacements:
                    await tool_ctx.error(
                        f"Found {occurrences} occurrences of the specified old_string, but expected {expected_replacements}"
                    )
                    return f"Error: Found {occurrences} occurrences of the specified old_string, but expected {expected_replacements}. Change your old_string to uniquely identify the target text, or set expected_replacements={occurrences} to replace all occurrences."

                # Replace all occurrences since the count matches expectations
                modified_content = original_content.replace(old_string, new_string)
            else:
                # If we can't find the exact string, report an error
                await tool_ctx.error(
                    "The specified old_string was not found in the file content"
                )
                return "Error: The specified old_string was not found in the file content. Please check that it matches exactly, including all whitespace and indentation."

            # Generate diff
            original_lines = original_content.splitlines(keepends=True)
            modified_lines = modified_content.splitlines(keepends=True)

            diff_lines = list(
                unified_diff(
                    original_lines,
                    modified_lines,
                    fromfile=f"{file_path} (original)",
                    tofile=f"{file_path} (modified)",
                    n=3,
                )
            )

            diff_text = "".join(diff_lines)

            # Determine the number of backticks needed
            num_backticks = 3
            while f"```{num_backticks}" in diff_text:
                num_backticks += 1

            # Format diff with appropriate number of backticks
            formatted_diff = f"```{num_backticks}diff\n{diff_text}```{num_backticks}\n"

            # Write the file if there are changes
            if diff_text:
                with open(file_path_obj, "w", encoding="utf-8") as f:
                    f.write(modified_content)

                # Update document context
                document_context = get_document_context()
                document_context.update_document(file_path, modified_content)

                await tool_ctx.info(
                    f"Successfully edited file: {file_path} ({expected_replacements} replacements applied)"
                )
                return f"Successfully edited file: {file_path} ({expected_replacements} replacements applied)\n\n{formatted_diff}"
            else:
                return f"No changes made to file: {file_path}"
        except UnicodeDecodeError:
            await tool_ctx.error(f"Cannot edit binary file: {file_path}")
            return f"Error: Cannot edit binary file: {file_path}"
    except Exception as e:
        await tool_ctx.error(f"Error editing file: {str(e)}")
        return f"Error editing file: {str(e)}"


def register_edit_tool(mcp_server: FastMCP) -> None:
    """Register the edit tool with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
    """
    mcp_server.tool()(edit)
