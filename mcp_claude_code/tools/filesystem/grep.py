"""Grep tool implementation.

This module provides the Grep tool for finding text patterns in files using ripgrep.
"""

import asyncio
import fnmatch
import json
import re
import shlex
import shutil
from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.common.context import ToolContext
from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool


@final
class Grep(FilesystemBaseTool):
    """Fast content search tool that works with any codebase size."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "grep"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Fast content search tool that works with any codebase size.
Searches file contents using regular expressions.
Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.).
Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}").
Returns matching file paths sorted by modification time.
Use this tool when you need to find files containing specific patterns.
When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead."""

    @property
    @override
    def parameters(self) -> dict[str, Any]:
        """Get the parameter specifications for the tool.

        Returns:
            Parameter specifications
        """
        return {
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regular expression pattern to search for in file contents",
                },
                "path": {
                    "type": "string",
                    "description": "The directory to search in. Defaults to the current working directory.",
                },
                "include": {
                    "type": "string",
                    "description": 'File pattern to include in the search (e.g. "*.js", "*.{ts,tsx}")',
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Legacy parameter: File pattern to include in the search. Use 'include' instead.",
                },
            },
            "required": ["pattern"],
            "additionalProperties": False,
            "$schema": "http://json-schema.org/draft-07/schema#",
        }

    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.

        Returns:
            List of required parameter names
        """
        return ["pattern"]

    def is_ripgrep_installed(self) -> bool:
        """Check if ripgrep (rg) is installed.

        Returns:
            True if ripgrep is installed, False otherwise
        """
        return shutil.which("rg") is not None

    async def run_ripgrep(
        self,
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
            results = self.parse_ripgrep_json_output(stdout.decode())
            return results

        except Exception as e:
            await tool_ctx.error(f"Error running ripgrep: {str(e)}")
            return f"Error running ripgrep: {str(e)}"

    def parse_ripgrep_json_output(self, output: str) -> str:
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
        self,
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
        await tool_ctx.info(f"Using fallback Python implementation for grep")

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
                    if self.is_path_allowed(entry_path):
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
                await tool_ctx.info(
                    f"Searching through {total_files} files in directory"
                )

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
                            await tool_ctx.warning(
                                f"Error reading {file_path}: {str(e)}"
                            )
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

    @override
    async def call(self, ctx: MCPContext, **params: Any) -> str:
        """Execute the grep tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = self.create_tool_context(ctx)

        # Extract parameters
        pattern = params.get("pattern")
        path: str = params.get("path", ".")
        # Support both 'include' and legacy 'file_pattern' parameter for backward compatibility
        include: str = params.get("include") or params.get("file_pattern", "*")

        # Validate required parameters
        if pattern is None:
            await tool_ctx.error("Parameter 'pattern' is required but was None")
            return "Error: Parameter 'pattern' is required but was None"

        if isinstance(pattern, str) and pattern.strip() == "":
            await tool_ctx.error("Parameter 'pattern' cannot be empty")
            return "Error: Parameter 'pattern' cannot be empty"

        # Validate path if provided
        if path:
            path_validation = self.validate_path(path)
            if path_validation.is_error:
                await tool_ctx.error(path_validation.error_message)
                return f"Error: {path_validation.error_message}"

            # Check if path is allowed
            allowed, error_msg = await self.check_path_allowed(path, tool_ctx)
            if not allowed:
                return error_msg

            # Check if path exists
            exists, error_msg = await self.check_path_exists(path, tool_ctx)
            if not exists:
                return error_msg

        # Log operation
        search_info = f"Searching for pattern '{pattern}'"
        if include:
            search_info += f" in files matching '{include}'"
        search_info += f" in path: {path}"
        await tool_ctx.info(search_info)

        # Check if ripgrep is installed and use it if available
        try:
            if self.is_ripgrep_installed():
                await tool_ctx.info("ripgrep is installed, using ripgrep for search")
                result = await self.run_ripgrep(pattern, path, tool_ctx, include)
                return result
            else:
                await tool_ctx.info(
                    "ripgrep is not installed, using fallback implementation"
                )
                result = await self.fallback_grep(pattern, path, tool_ctx, include)
                return result
        except Exception as e:
            await tool_ctx.error(f"Error in grep tool: {str(e)}")
            return f"Error in grep tool: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this grep tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def grep(
            ctx: MCPContext,
            pattern: str,
            path: str = ".",
            include: str | None = None,
            file_pattern: str | None = "*",
        ) -> str:
            # Use 'include' parameter if provided, otherwise fall back to 'file_pattern'
            include_param = include or file_pattern
            return await tool_self.call(
                ctx, pattern=pattern, path=path, include=include_param
            )
