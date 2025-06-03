"""Multi-edit tool implementation.

This module provides the MultiEdit tool for making multiple precise text replacements in files.
"""

from difflib import unified_diff
from pathlib import Path
from typing import Annotated, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool

FilePath = Annotated[
    str,
    Field(
        description="The absolute path to the file to modify (must be absolute, not relative)",
    ),
]


class EditItem(TypedDict):
    """A single edit operation."""

    old_string: Annotated[
        str,
        Field(
            description="The text to replace (must match the file contents exactly, including all whitespace and indentation)",
        ),
    ]
    new_string: Annotated[
        str,
        Field(
            description="The edited text to replace the old_string",
        ),
    ]
    expected_replacements: Annotated[
        int,
        Field(
            default=1,
            description="The expected number of replacements to perform. Defaults to 1 if not specified.",
        ),
    ]


Edits = Annotated[
    list[EditItem],
    Field(
        description="Array of edit operations to perform sequentially on the file",
        min_length=1,
    ),
]


class MultiEditToolParams(TypedDict):
    """Parameters for the MultiEdit tool.

    Attributes:
        file_path: The absolute path to the file to modify (must be absolute, not relative)
        edits: Array of edit operations to perform sequentially on the file
    """

    file_path: FilePath
    edits: Edits


@final
class MultiEdit(FilesystemBaseTool):
    """Tool for making multiple precise text replacements in files."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "multi_edit"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """This is a tool for making multiple edits to a single file in one operation. It is built on top of the Edit tool and allows you to perform multiple find-and-replace operations efficiently. Prefer this tool over the Edit tool when you need to make multiple edits to the same file.

Before using this tool:

1. Use the Read tool to understand the file's contents and context
2. Verify the directory path is correct

To make multiple file edits, provide the following:
1. file_path: The absolute path to the file to modify (must be absolute, not relative)
2. edits: An array of edit operations to perform, where each edit contains:
   - old_string: The text to replace (must match the file contents exactly, including all whitespace and indentation)
   - new_string: The edited text to replace the old_string
   - expected_replacements: The number of replacements you expect to make. Defaults to 1 if not specified.

IMPORTANT:
- All edits are applied in sequence, in the order they are provided
- Each edit operates on the result of the previous edit
- All edits must be valid for the operation to succeed - if any edit fails, none will be applied
- This tool is ideal when you need to make several changes to different parts of the same file
- For Jupyter notebooks (.ipynb files), use the NotebookEdit instead

CRITICAL REQUIREMENTS:
1. All edits follow the same requirements as the single Edit tool
2. The edits are atomic - either all succeed or none are applied
3. Plan your edits carefully to avoid conflicts between sequential operations

WARNING:
- The tool will fail if edits.old_string matches multiple locations and edits.expected_replacements isn't specified
- The tool will fail if the number of matches doesn't equal edits.expected_replacements when it's specified
- The tool will fail if edits.old_string doesn't match the file contents exactly (including whitespace)
- The tool will fail if edits.old_string and edits.new_string are the same
- Since edits are applied in sequence, ensure that earlier edits don't affect the text that later edits are trying to find

When making edits:
- Ensure all edits result in idiomatic, correct code
- Do not leave the code in a broken state
- Always use absolute file paths (starting with /)

If you want to create a new file, use:
- A new file path, including dir name if needed
- First edit: empty old_string and the new file's contents as new_string
- Subsequent edits: normal edit operations on the created content"""

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[MultiEditToolParams],
    ) -> str:
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
        file_path: FilePath = params["file_path"]
        edits: Edits = params["edits"]

        # Validate parameters
        path_validation = self.validate_path(file_path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        # Validate each edit
        for i, edit in enumerate(edits):
            if not isinstance(edit, dict):
                await tool_ctx.error(f"Edit at index {i} must be an object")
                return f"Error: Edit at index {i} must be an object"

            old_string = edit.get("old_string")
            new_string = edit.get("new_string")
            expected_replacements = edit.get("expected_replacements", 1)

            if old_string is None:
                await tool_ctx.error(
                    f"Parameter 'old_string' in edit at index {i} is required but was None"
                )
                return f"Error: Parameter 'old_string' in edit at index {i} is required but was None"

            if new_string is None:
                await tool_ctx.error(
                    f"Parameter 'new_string' in edit at index {i} is required but was None"
                )
                return f"Error: Parameter 'new_string' in edit at index {i} is required but was None"

            if (
                expected_replacements is None
                or not isinstance(expected_replacements, (int, float))
                or expected_replacements < 0
            ):
                await tool_ctx.error(
                    f"Parameter 'expected_replacements' in edit at index {i} must be a non-negative number"
                )
                return f"Error: Parameter 'expected_replacements' in edit at index {i} must be a non-negative number"

            if old_string == new_string:
                await tool_ctx.error(
                    f"Edit at index {i}: old_string and new_string are identical"
                )
                return (
                    f"Error: Edit at index {i}: old_string and new_string are identical"
                )

        await tool_ctx.info(f"Applying {len(edits)} edits to file: {file_path}")

        # Check if file is allowed to be edited
        allowed, error_msg = await self.check_path_allowed(file_path, tool_ctx)
        if not allowed:
            return error_msg

        try:
            file_path_obj = Path(file_path)

            # Handle file creation case (when first edit has empty old_string)
            first_edit = edits[0]
            if not file_path_obj.exists() and first_edit.get("old_string") == "":
                # Check if parent directory is allowed
                parent_dir = str(file_path_obj.parent)
                if not self.is_path_allowed(parent_dir):
                    await tool_ctx.error(f"Parent directory not allowed: {parent_dir}")
                    return f"Error: Parent directory not allowed: {parent_dir}"

                # Create parent directories if they don't exist
                file_path_obj.parent.mkdir(parents=True, exist_ok=True)

                # Start with the content from the first edit
                current_content = first_edit.get("new_string", "")

                # Apply remaining edits to this content
                edits_to_apply = edits[1:]
                creation_mode = True
            else:
                # Normal edit mode - file must exist
                exists, error_msg = await self.check_path_exists(file_path, tool_ctx)
                if not exists:
                    return error_msg

                # Check is a file
                is_file, error_msg = await self.check_is_file(file_path, tool_ctx)
                if not is_file:
                    return error_msg

                # Read the file
                try:
                    with open(file_path_obj, "r", encoding="utf-8") as f:
                        current_content = f.read()
                except UnicodeDecodeError:
                    await tool_ctx.error(f"Cannot edit binary file: {file_path}")
                    return f"Error: Cannot edit binary file: {file_path}"

                edits_to_apply = edits
                creation_mode = False

            # Store original content for diff generation
            original_content = "" if creation_mode else current_content

            # Apply all edits sequentially
            total_replacements = 0
            for i, edit in enumerate(edits_to_apply):
                old_string = edit.get("old_string")
                new_string = edit.get("new_string")
                expected_replacements = edit.get("expected_replacements", 1)

                # Check if old_string exists in current content
                if old_string not in current_content:
                    edit_index = (
                        i + 1 if not creation_mode else i + 2
                    )  # Adjust for display
                    await tool_ctx.error(
                        f"Edit {edit_index}: The specified old_string was not found in the file content"
                    )
                    return f"Error: Edit {edit_index}: The specified old_string was not found in the file content. Please check that it matches exactly, including all whitespace and indentation."

                # Count occurrences
                occurrences = current_content.count(old_string)

                # Check if the number of occurrences matches expected_replacements
                if occurrences != expected_replacements:
                    edit_index = (
                        i + 1 if not creation_mode else i + 2
                    )  # Adjust for display
                    await tool_ctx.error(
                        f"Edit {edit_index}: Found {occurrences} occurrences of the specified old_string, but expected {expected_replacements}"
                    )
                    return f"Error: Edit {edit_index}: Found {occurrences} occurrences of the specified old_string, but expected {expected_replacements}. Change your old_string to uniquely identify the target text, or set expected_replacements={occurrences} to replace all occurrences."

                # Apply the replacement
                current_content = current_content.replace(old_string, new_string)
                total_replacements += expected_replacements

            # Generate diff
            original_lines = original_content.splitlines(keepends=True)
            modified_lines = current_content.splitlines(keepends=True)

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

            # Write the file
            if diff_text or creation_mode:
                with open(file_path_obj, "w", encoding="utf-8") as f:
                    f.write(current_content)

                if creation_mode:
                    pass
                else:
                    pass

                if creation_mode:
                    await tool_ctx.info(f"Successfully created file: {file_path}")
                    return f"Successfully created file: {file_path} ({len(current_content)} bytes)\n\n{formatted_diff}"
                else:
                    await tool_ctx.info(
                        f"Successfully applied {len(edits)} edits to file: {file_path} ({total_replacements} total replacements)"
                    )
                    return f"Successfully applied {len(edits)} edits to file: {file_path} ({total_replacements} total replacements)\n\n{formatted_diff}"
            else:
                return f"No changes made to file: {file_path}"

        except Exception as e:
            await tool_ctx.error(f"Error applying edits to file: {str(e)}")
            return f"Error applying edits to file: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this multi-edit tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.description)
        async def multi_edit(
            ctx: MCPContext,
            file_path: FilePath,
            edits: Edits,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(
                ctx,
                file_path=file_path,
                edits=edits,
            )
