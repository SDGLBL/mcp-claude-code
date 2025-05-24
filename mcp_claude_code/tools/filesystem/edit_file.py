"""Edit file tool implementation.

This module provides the EditFileTool for making line-based edits to text files.
"""

from difflib import unified_diff
from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool


@final
class EditFileTool(FilesystemBaseTool):
    """Tool for making line-based edits to files."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "edit_file"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Make line-based edits to a text file.

Each edit replaces exact line sequences with new content.
Returns a git-style diff showing the changes made.
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
                "path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify (must be absolute, not relative)",
                },
                "edits": {
                    "items": {
                        "properties": {
                            "oldText": {
                                "type": "string",
                                "description": "The text to replace (must be unique within the file, and must match the file contents exactly, including all whitespace and indentation)",
                            },
                            "newText": {
                                "type": "string",
                                "description": "The edited text to replace the old_string",
                            },
                        },
                        "additionalProperties": {"type": "string"},
                        "type": "object",
                    },
                    "description": 'List of edit operations [{"oldText": "...", "newText": "..."}]',
                    "type": "array",
                },
                "dry_run": {
                    "default": False,
                    "type": "boolean",
                    "description": "If true, do not write changes to the file",
                },
            },
            "required": ["path", "edits"],
            "title": "edit_fileArguments",
            "type": "object",
        }

    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.

        Returns:
            List of required parameter names
        """
        return ["path", "edits"]

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
        self.set_tool_context_info(tool_ctx)

        # Extract parameters
        path = params.get("path")
        edits = params.get("edits")
        dry_run = params.get("dry_run", False)  # Default to False if not provided

        if not path:
            await tool_ctx.error("Parameter 'path' is required but was None")
            return "Error: Parameter 'path' is required but was None"

        if path.strip() == "":
            await tool_ctx.error("Parameter 'path' cannot be empty")
            return "Error: Parameter 'path' cannot be empty"

        # Validate parameters
        path_validation = self.validate_path(path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        if not edits:
            await tool_ctx.error("Parameter 'edits' is required but was None")
            return "Error: Parameter 'edits' is required but was None"

        if not edits:  # Check for empty list
            await tool_ctx.warning("No edits specified")
            return "Error: No edits specified"

        # Validate each edit to ensure oldText is not empty
        for i, edit in enumerate(edits):
            old_text = edit.get("oldText", "")
            if not old_text or old_text.strip() == "":
                await tool_ctx.error(
                    f"Parameter 'oldText' in edit at index {i} is empty"
                )
                return f"Error: Parameter 'oldText' in edit at index {i} cannot be empty - must provide text to match"

        # dry_run parameter can be None safely as it has a default value in the function signature

        await tool_ctx.info(f"Editing file: {path}")

        # Check if file is allowed to be edited
        allowed, error_msg = await self.check_path_allowed(path, tool_ctx)
        if not allowed:
            return error_msg

        # Additional check already verified by is_path_allowed above
        await tool_ctx.info(f"Editing file: {path}")

        try:
            file_path = Path(path)

            # Check file exists
            exists, error_msg = await self.check_path_exists(path, tool_ctx)
            if not exists:
                return error_msg

            # Check is a file
            is_file, error_msg = await self.check_is_file(path, tool_ctx)
            if not is_file:
                return error_msg

            # Read the file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    original_content = f.read()

                # Apply edits
                modified_content = original_content
                edits_applied = 0

                for edit in edits:
                    old_text = edit.get("oldText", "")
                    new_text = edit.get("newText", "")

                    if old_text in modified_content:
                        modified_content = modified_content.replace(old_text, new_text)
                        edits_applied += 1
                    else:
                        # Try line-by-line matching for whitespace flexibility
                        old_lines = old_text.splitlines()
                        content_lines = modified_content.splitlines()

                        for i in range(len(content_lines) - len(old_lines) + 1):
                            current_chunk = content_lines[i : i + len(old_lines)]

                            # Compare with whitespace normalization
                            matches = all(
                                old_line.strip() == content_line.strip()
                                for old_line, content_line in zip(
                                    old_lines, current_chunk
                                )
                            )

                            if matches:
                                # Replace the matching lines
                                new_lines = new_text.splitlines()
                                content_lines[i : i + len(old_lines)] = new_lines
                                modified_content = "\n".join(content_lines)
                                edits_applied += 1
                                break

                if edits_applied < len(edits):
                    await tool_ctx.warning(
                        f"Some edits could not be applied: {edits_applied}/{len(edits)}"
                    )

                # Generate diff
                original_lines = original_content.splitlines(keepends=True)
                modified_lines = modified_content.splitlines(keepends=True)

                diff_lines = list(
                    unified_diff(
                        original_lines,
                        modified_lines,
                        fromfile=f"{path} (original)",
                        tofile=f"{path} (modified)",
                        n=3,
                    )
                )

                diff_text = "".join(diff_lines)

                # Determine the number of backticks needed
                num_backticks = 3
                while f"```{num_backticks}" in diff_text:
                    num_backticks += 1

                # Format diff with appropriate number of backticks
                formatted_diff = (
                    f"```{num_backticks}diff\n{diff_text}```{num_backticks}\n"
                )

                # Write the file if not a dry run
                if not dry_run and diff_text:  # Only write if there are changes
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(modified_content)

                    # Update document context
                    self.document_context.update_document(path, modified_content)

                    await tool_ctx.info(
                        f"Successfully edited file: {path} ({edits_applied} edits applied)"
                    )
                    return f"Successfully edited file: {path} ({edits_applied} edits applied)\n\n{formatted_diff}"
                elif not diff_text:
                    return f"No changes made to file: {path}"
                else:
                    await tool_ctx.info(
                        f"Dry run: {edits_applied} edits would be applied"
                    )
                    return f"Dry run: {edits_applied} edits would be applied\n\n{formatted_diff}"
            except UnicodeDecodeError:
                await tool_ctx.error(f"Cannot edit binary file: {path}")
                return f"Error: Cannot edit binary file: {path}"
        except Exception as e:
            await tool_ctx.error(f"Error editing file: {str(e)}")
            return f"Error editing file: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this edit file tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def edit_file(
            ctx: MCPContext,
            path: str,
            edits: list[dict[str, str]],
            dry_run: bool = False,
        ) -> str:
            return await tool_self.call(ctx, path=path, edits=edits, dry_run=dry_run)
