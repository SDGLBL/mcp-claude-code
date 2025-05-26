"""Grep tool implementation.

This module provides the grep tool for finding text patterns in files using ripgrep.
Converted to FastMCP v2 function-based pattern.
"""

import asyncio
import fnmatch
import json
import re
import shlex
import shutil
from pathlib import Path

from fastmcp import Context as MCPContext
from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import (
    is_path_allowed,
    validate_path,
)
from mcp_claude_code.tools.common.context import ToolContext, create_tool_context


def is_ripgrep_installed() -> bool:
    """Check if ripgrep (rg) is installed.

    Returns:
        True if ripgrep is installed, False otherwise
    """
    return shutil.which("rg") is not None


async def run_ripgrep(
    pattern: str,
    path: str,
    tool_ctx: ToolContext,
    include_pattern: str | None = None,
) -> str:
    """Run ripgrep with the given parameters and return the results.

    Args:
        pattern: The regular expression pattern to search for
        path: The directory or file to search in
        include_pattern: Optional file pattern to include in the search
        tool_ctx: Tool context for logging

    Returns:
        The search results as formatted string
    """
    # Special case for tests: direct file path with include pattern that doesn't match
    if Path(path).is_file() and include_pattern and include_pattern != "*":
        if not fnmatch.fnmatch(Path(path).name, include_pattern):
            await tool_ctx.info(
                f"File does not match pattern '{include_pattern}': {path}"
            )
            return f"File does not match pattern '{include_pattern}': {path}"

    cmd = ["rg", "--json", pattern]

    # Add path
    cmd.append(path)

    # Add include pattern if provided
    if include_pattern and include_pattern != "*":
        cmd.extend(["-g", include_pattern])

    await tool_ctx.info(f"Running ripgrep command: {shlex.join(cmd)}")

    try:
        # Execute ripgrep process
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0 and process.returncode != 1:
            # rg returns 1 when no matches are found, which is not an error
            await tool_ctx.error(
                f"ripgrep failed with exit code {process.returncode}: {stderr.decode()}"
            )
            return f"Error executing ripgrep: {stderr.decode()}"

        # Parse the JSON output
        results = parse_ripgrep_json_output(stdout.decode())
        return results

    except Exception as e:
        await tool_ctx.error(f"Error running ripgrep: {str(e)}")
        return f"Error running ripgrep: {str(e)}"


def parse_ripgrep_json_output(output: str) -> str:
    """Parse ripgrep JSON output and format it for human readability.

    Args:
        output: The JSON output from ripgrep

    Returns:
        Formatted string with search results
    """
    if not output.strip():
        return "No matches found."

    formatted_results = []
    file_results = {}

    for line in output.splitlines():
        if not line.strip():
            continue

        try:
            data = json.loads(line)

            if data.get("type") == "match":
                path = data.get("data", {}).get("path", {}).get("text", "")
                line_number = data.get("data", {}).get("line_number", 0)
                line_text = (
                    data.get("data", {}).get("lines", {}).get("text", "").rstrip()
                )

                if path not in file_results:
                    file_results[path] = []

                file_results[path].append((line_number, line_text))

        except json.JSONDecodeError as e:
            formatted_results.append(f"Error parsing JSON: {str(e)}")

    # Count total matches
    total_matches = sum(len(matches) for matches in file_results.values())
    total_files = len(file_results)

    if total_matches == 0:
        return "No matches found."

    formatted_results.append(
        f"Found {total_matches} matches in {total_files} file{'s' if total_files > 1 else ''}:"
    )
    formatted_results.append("")  # Empty line for readability

    # Format the results by file
    for file_path, matches in file_results.items():
        for line_number, line_text in matches:
            formatted_results.append(f"{file_path}:{line_number}: {line_text}")

    return "\n".join(formatted_results)


async def fallback_grep(
    pattern: str,
    path: str,
    tool_ctx: ToolContext,
    include_pattern: str | None = None,
) -> str:
    """Fallback Python implementation when ripgrep is not available.

    Args:
        pattern: The regular expression pattern to search for
        path: The directory or file to search in
        include_pattern: Optional file pattern to include in the search
        tool_ctx: Tool context for logging

    Returns:
        The search results as formatted string
    """
    await tool_ctx.info("Using fallback Python implementation for grep")

    try:
        input_path = Path(path)

        # Find matching files
        matching_files: list[Path] = []

        # Process based on whether path is a file or directory
        if input_path.is_file():
            # Single file search - check file pattern match first
            if (
                include_pattern is None
                or include_pattern == "*"
                or fnmatch.fnmatch(input_path.name, include_pattern)
            ):
                matching_files.append(input_path)
                await tool_ctx.info(f"Searching single file: {path}")
            else:
                # File doesn't match the pattern, return immediately
                await tool_ctx.info(
                    f"File does not match pattern '{include_pattern}': {path}"
                )
                return f"File does not match pattern '{include_pattern}': {path}"
        elif input_path.is_dir():
            # Directory search - find all files
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
                    if (
                        include_pattern is None
                        or include_pattern == "*"
                        or fnmatch.fnmatch(entry.name, include_pattern)
                    ):
                        matching_files.append(entry)

            await tool_ctx.info(f"Found {len(matching_files)} matching files")
        else:
            # This shouldn't happen if path exists
            await tool_ctx.error(f"Path is neither a file nor a directory: {path}")
            return f"Error: Path is neither a file nor a directory: {path}"

        # Report progress
        total_files = len(matching_files)
        if input_path.is_file():
            await tool_ctx.info(f"Searching file: {path}")
        else:
            await tool_ctx.info(f"Searching through {total_files} files in directory")

        # Set up for parallel processing
        results: list[str] = []
        files_processed = 0
        matches_found = 0
        batch_size = 20  # Process files in batches to avoid overwhelming the system

        # Use a semaphore to limit concurrent file operations
        semaphore = asyncio.Semaphore(10)

        # Create an async function to search a single file
        async def search_file(file_path: Path) -> list[str]:
            nonlocal files_processed, matches_found
            file_results: list[str] = []

            try:
                async with semaphore:  # Limit concurrent operations
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            for line_num, line in enumerate(f, 1):
                                if re.search(pattern, line):
                                    file_results.append(
                                        f"{file_path}:{line_num}: {line.rstrip()}"
                                    )
                                    matches_found += 1
                        files_processed += 1
                    except UnicodeDecodeError:
                        # Skip binary files
                        files_processed += 1
                    except Exception as e:
                        await tool_ctx.warning(f"Error reading {file_path}: {str(e)}")
            except Exception as e:
                await tool_ctx.warning(f"Error processing {file_path}: {str(e)}")

            return file_results

        # Process files in parallel batches
        for i in range(0, len(matching_files), batch_size):
            batch = matching_files[i : i + batch_size]
            batch_tasks = [search_file(file_path) for file_path in batch]

            # Report progress
            await tool_ctx.report_progress(i, total_files)

            # Wait for the batch to complete
            batch_results = await asyncio.gather(*batch_tasks)

            # Flatten and collect results
            for file_result in batch_results:
                results.extend(file_result)

        # Final progress report
        await tool_ctx.report_progress(total_files, total_files)

        if not results:
            if input_path.is_file():
                return f"No matches found for pattern '{pattern}' in file: {path}"
            else:
                return f"No matches found for pattern '{pattern}' in files matching '{include_pattern or '*'}' in directory: {path}"

        await tool_ctx.info(
            f"Found {matches_found} matches in {files_processed} file{'s' if files_processed > 1 else ''}"
        )
        return (
            f"Found {matches_found} matches in {files_processed} file{'s' if files_processed > 1 else ''}:\n\n"
            + "\n".join(results)
        )
    except Exception as e:
        await tool_ctx.error(f"Error searching file contents: {str(e)}")
        return f"Error searching file contents: {str(e)}"


async def grep(
    pattern: str,
    ctx: MCPContext,
    path: str = ".",
    include: str | None = None,
    file_pattern: str | None = "*",
) -> str:
    """Fast content search tool that works with any codebase size.

    Searches file contents using regular expressions.
    Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.).
    Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}").
    Returns matching file paths sorted by modification time.
    Use this tool when you need to find files containing specific patterns.
    When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead.

    Args:
        pattern: The regular expression pattern to search for in file contents
        ctx: MCP context for the tool call
        path: The directory to search in. Defaults to the current working directory.
        include: File pattern to include in the search (e.g. "*.js", "*.{ts,tsx}")
        file_pattern: Legacy parameter: File pattern to include in the search. Use 'include' instead.

    Returns:
        Tool execution results
    """
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("grep")

    # Support both 'include' and legacy 'file_pattern' parameter for backward compatibility
    include_param: str = include or file_pattern or "*"

    # Validate required parameters
    if pattern is None:
        await tool_ctx.error("Parameter 'pattern' is required but was None")
        return "Error: Parameter 'pattern' is required but was None"

    if isinstance(pattern, str) and pattern.strip() == "":
        await tool_ctx.error("Parameter 'pattern' cannot be empty")
        return "Error: Parameter 'pattern' cannot be empty"

    # Validate path if provided
    if path:
        path_validation = validate_path(path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        # Check if path is allowed
        if not is_path_allowed(path):
            await tool_ctx.error(
                f"Access denied - path outside allowed directories: {path}"
            )
            return f"Error: Access denied - path outside allowed directories: {path}"

        # Check if path exists
        path_obj = Path(path)
        if not path_obj.exists():
            await tool_ctx.error(f"Path does not exist: {path}")
            return f"Error: Path does not exist: {path}"

    # Log operation
    search_info = f"Searching for pattern '{pattern}'"
    if include_param:
        search_info += f" in files matching '{include_param}'"
    search_info += f" in path: {path}"
    await tool_ctx.info(search_info)

    # Check if ripgrep is installed and use it if available
    try:
        if is_ripgrep_installed():
            await tool_ctx.info("ripgrep is installed, using ripgrep for search")
            result = await run_ripgrep(pattern, path, tool_ctx, include_param)
            return result
        else:
            await tool_ctx.info(
                "ripgrep is not installed, using fallback implementation"
            )
            result = await fallback_grep(pattern, path, tool_ctx, include_param)
            return result
    except Exception as e:
        await tool_ctx.error(f"Error in grep tool: {str(e)}")
        return f"Error in grep tool: {str(e)}"


def register_grep_tool(mcp_server: FastMCP) -> None:
    """Register the grep tool with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
    """
    mcp_server.tool()(grep)
