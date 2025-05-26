"""Content replace tool implementation.

This module provides the content_replace tool for replacing text patterns in files.
Converted to FastMCP v2 function-based pattern.
"""

import fnmatch
from pathlib import Path

from fastmcp import Context as MCPContext
from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import (
    get_document_context,
    is_path_allowed,
    validate_path,
)
from mcp_claude_code.tools.common.context import create_tool_context


async def content_replace(
    pattern: str,
    replacement: str,
    path: str,
    ctx: MCPContext,
    file_pattern: str = "*",
    dry_run: bool = False,
) -> str:
    """Replace a pattern in file contents across multiple files.

    Searches for text patterns across all files in the specified directory
    that match the file pattern and replaces them with the specified text.
    Can be run in dry-run mode to preview changes without applying them.
    Only works within allowed directories.

    Args:
        pattern: Pattern to search for
        replacement: Replacement text
        path: Path to search in
        ctx: MCP context for the tool call
        file_pattern: File pattern to match
        dry_run: Whether to perform a dry run

    Returns:
        Tool execution results
    """
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("content_replace")

    # Validate required parameters
    if not pattern:
        await tool_ctx.error("Parameter 'pattern' is required but was None")
        return "Error: Parameter 'pattern' is required but was None"

    if pattern.strip() == "":
        await tool_ctx.error("Parameter 'pattern' cannot be empty")
        return "Error: Parameter 'pattern' cannot be empty"

    if replacement is None:
        await tool_ctx.error("Parameter 'replacement' is required but was None")
        return "Error: Parameter 'replacement' is required but was None"

    if not path:
        await tool_ctx.error("Parameter 'path' is required but was None")
        return "Error: Parameter 'path' is required but was None"

    if path.strip() == "":
        await tool_ctx.error("Parameter 'path' cannot be empty")
        return "Error: Parameter 'path' cannot be empty"

    # Note: replacement can be an empty string as sometimes you want to delete the pattern

    path_validation = validate_path(path)
    if path_validation.is_error:
        await tool_ctx.error(path_validation.error_message)
        return f"Error: {path_validation.error_message}"

    # file_pattern and dry_run can be None safely as they have default values

    await tool_ctx.info(
        f"Replacing pattern '{pattern}' with '{replacement}' in files matching '{file_pattern}' in {path}"
    )

    # Check if path is allowed
    if not is_path_allowed(path):
        await tool_ctx.error(
            f"Access denied - path outside allowed directories: {path}"
        )
        return f"Error: Access denied - path outside allowed directories: {path}"

    try:
        input_path = Path(path)

        # Check if path exists
        if not input_path.exists():
            await tool_ctx.error(f"Path does not exist: {path}")
            return f"Error: Path does not exist: {path}"

        # Find matching files
        matching_files: list[Path] = []

        # Process based on whether path is a file or directory
        if input_path.is_file():
            # Single file search
            if file_pattern == "*" or fnmatch.fnmatch(input_path.name, file_pattern):
                matching_files.append(input_path)
                await tool_ctx.info(f"Searching single file: {path}")
            else:
                await tool_ctx.info(
                    f"File does not match pattern '{file_pattern}': {path}"
                )
                return f"File does not match pattern '{file_pattern}': {path}"
        elif input_path.is_dir():
            # Directory search - optimized file finding
            await tool_ctx.info(f"Finding files in directory: {path}")

            # Keep track of allowed paths for filtering
            allowed_paths: set[str] = set()

            # Collect all allowed paths first for faster filtering
            for entry in input_path.rglob("*"):
                entry_path = str(entry)
                if is_path_allowed(entry_path):
                    allowed_paths.add(entry_path)

            # Find matching files efficiently
            for entry in input_path.rglob("*"):
                entry_path = str(entry)
                if entry_path in allowed_paths and entry.is_file():
                    if file_pattern == "*" or fnmatch.fnmatch(entry.name, file_pattern):
                        matching_files.append(entry)

            await tool_ctx.info(f"Found {len(matching_files)} matching files")
        else:
            # This shouldn't happen since we already checked for existence
            await tool_ctx.error(f"Path is neither a file nor a directory: {path}")
            return f"Error: Path is neither a file nor a directory: {path}"

        # Report progress
        total_files = len(matching_files)
        await tool_ctx.info(f"Processing {total_files} files")

        # Process files
        results: list[str] = []
        files_modified = 0
        replacements_made = 0

        for i, file_path in enumerate(matching_files):
            # Report progress every 10 files
            if i % 10 == 0:
                await tool_ctx.report_progress(i, total_files)

            try:
                # Read file
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Count occurrences
                count = content.count(pattern)

                if count > 0:
                    # Replace pattern
                    new_content = content.replace(pattern, replacement)

                    # Add to results
                    replacements_made += count
                    files_modified += 1
                    results.append(f"{file_path}: {count} replacements")

                    # Write file if not a dry run
                    if not dry_run:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)

                        # Update document context
                        document_context = get_document_context()
                        document_context.update_document(str(file_path), new_content)
            except UnicodeDecodeError:
                # Skip binary files
                continue
            except Exception as e:
                await tool_ctx.warning(f"Error processing {file_path}: {str(e)}")

        # Final progress report
        await tool_ctx.report_progress(total_files, total_files)

        if replacements_made == 0:
            return f"No occurrences of pattern '{pattern}' found in files matching '{file_pattern}' in {path}"

        if dry_run:
            await tool_ctx.info(
                f"Dry run: {replacements_made} replacements would be made in {files_modified} files"
            )
            message = f"Dry run: {replacements_made} replacements of '{pattern}' with '{replacement}' would be made in {files_modified} files:"
        else:
            await tool_ctx.info(
                f"Made {replacements_made} replacements in {files_modified} files"
            )
            message = f"Made {replacements_made} replacements of '{pattern}' with '{replacement}' in {files_modified} files:"

        return message + "\n\n" + "\n".join(results)
    except Exception as e:
        await tool_ctx.error(f"Error replacing content: {str(e)}")
        return f"Error replacing content: {str(e)}"


def register_content_replace_tool(mcp_server: FastMCP) -> None:
    """Register the content_replace tool with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
    """
    mcp_server.tool()(content_replace)
