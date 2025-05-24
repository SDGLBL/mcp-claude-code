"""Content replace tool implementation.

This module provides the ContentReplaceTool for replacing text patterns in files.
"""

import fnmatch
from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool


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

    @property
    @override
    def parameters(self) -> dict[str, Any]:
        """Get the parameter specifications for the tool.

        Returns:
            Parameter specifications
        """
        return {
            "properties": {
                "pattern": {"title": "Pattern", "type": "string"},
                "replacement": {"title": "Replacement", "type": "string"},
                "path": {"title": "Path", "type": "string"},
                "file_pattern": {
                    "default": "*",
                    "title": "File Pattern",
                    "type": "string",
                },
                "dry_run": {"default": False, "title": "Dry Run", "type": "boolean"},
            },
            "required": ["pattern", "replacement", "path"],
            "title": "content_replaceArguments",
            "type": "object",
        }

    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.

        Returns:
            List of required parameter names
        """
        return ["pattern", "replacement", "path"]

    @override
    async def call(self, ctx: MCPContext, **params: Any) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = self.create_tool_context(ctx)

        # Extract parameters
        pattern = params.get("pattern")
        replacement = params.get("replacement")
        path = params.get("path")
        file_pattern = params.get("file_pattern", "*")  # Default to all files
        dry_run = params.get("dry_run", False)  # Default to False

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

                            # Update document context
                            self.document_context.update_document(
                                str(file_path), new_content
                            )
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

        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def content_replace(
            ctx: MCPContext,
            pattern: str,
            replacement: str,
            path: str,
            file_pattern: str = "*",
            dry_run: bool = False,
        ) -> str:
            return await tool_self.call(
                ctx,
                pattern=pattern,
                replacement=replacement,
                path=path,
                file_pattern=file_pattern,
                dry_run=dry_run,
            )
