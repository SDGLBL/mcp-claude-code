"""Content replace tool implementation.

This module provides the ContentReplaceTool for replacing text patterns in files.
"""

import fnmatch
from pathlib import Path
from typing import Annotated, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool

Pattern = Annotated[
    str,
    Field(
        description="Text pattern to search for in files",
        min_length=1,
    ),
]

Replacement = Annotated[
    str,
    Field(
        description="Text to replace the pattern with (can be empty string)",
    ),
]

SearchPath = Annotated[
    str,
    Field(
        description="Path to file or directory to search in",
        min_length=1,
    ),
]

FilePattern = Annotated[
    str,
    Field(
        description="File name pattern to match (default: all files)",
        default="*",
    ),
]

DryRun = Annotated[
    bool,
    Field(
        description="If True, only preview changes without modifying files",
        default=False,
    ),
]


class ContentReplaceToolParams(TypedDict):
    """Parameters for the ContentReplaceTool.

    Attributes:
        pattern: Text pattern to search for in files
        replacement: Text to replace the pattern with (can be empty string)
        path: Path to file or directory to search in
        file_pattern: File name pattern to match (default: all files)
        dry_run: If True, only preview changes without modifying files
    """

    pattern: Pattern
    replacement: Replacement
    path: SearchPath
    file_pattern: FilePattern
    dry_run: DryRun


@final
class ContentReplaceTool(FilesystemBaseTool):
    """Tool for replacing text patterns in files."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "content_replace"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Replace a pattern in file contents across multiple files.

Searches for text patterns across all files in the specified directory
that match the file pattern and replaces them with the specified text.
Can be run in dry-run mode to preview changes without applying them.
Only works within allowed directories."""

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[ContentReplaceToolParams],
    ) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = self.create_tool_context(ctx)

        # Extract parameters
        pattern: Pattern = params["pattern"]
        replacement: Replacement = params["replacement"]
        path: SearchPath = params["path"]
        file_pattern = params.get("file_pattern", "*")  # Default to all files
        dry_run = params.get("dry_run", False)  # Default to False

        path_validation = self.validate_path(path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        # file_pattern and dry_run can be None safely as they have default values

        await tool_ctx.info(
            f"Replacing pattern '{pattern}' with '{replacement}' in files matching '{file_pattern}' in {path}"
        )

        # Check if path is allowed
        allowed, error_msg = await self.check_path_allowed(path, tool_ctx)
        if not allowed:
            return error_msg

        # Additional check already verified by is_path_allowed above
        await tool_ctx.info(
            f"Replacing pattern '{pattern}' with '{replacement}' in files matching '{file_pattern}' in {path}"
        )

        try:
            input_path = Path(path)

            # Check if path exists
            exists, error_msg = await self.check_path_exists(path, tool_ctx)
            if not exists:
                return error_msg

            # Find matching files
            matching_files: list[Path] = []

            # Process based on whether path is a file or directory
            if input_path.is_file():
                # Single file search
                if file_pattern == "*" or fnmatch.fnmatch(
                    input_path.name, file_pattern
                ):
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
                    if self.is_path_allowed(entry_path):
                        allowed_paths.add(entry_path)

                # Find matching files efficiently
                for entry in input_path.rglob("*"):
                    entry_path = str(entry)
                    if entry_path in allowed_paths and entry.is_file():
                        if file_pattern == "*" or fnmatch.fnmatch(
                            entry.name, file_pattern
                        ):
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

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this content replace tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.description)
        async def content_replace(
            ctx: MCPContext,
            pattern: Pattern,
            replacement: Replacement,
            path: SearchPath,
            file_pattern: FilePattern,
            dry_run: DryRun,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(
                ctx,
                pattern=pattern,
                replacement=replacement,
                path=path,
                file_pattern=file_pattern,
                dry_run=dry_run,
            )
