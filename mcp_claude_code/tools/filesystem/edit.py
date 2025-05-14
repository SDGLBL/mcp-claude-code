"""Edit tool implementation.

This module provides the Edit tool for making precise text replacements in files.
"""

from difflib import unified_diff
from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool


@final
class Edit(FilesystemBaseTool):
    """Tool for making precise text replacements in files."""
    
    @property
    @override
    def name(self) -> str:
        """Get the tool name.
        
        Returns:
            Tool name
        """
        return "edit"
        
    @property
    @override
    def description(self) -> str:
        """Get the tool description.
        
        Returns:
            Tool description
        """
        return """This is a tool for editing files. For moving or renaming files, you should generally use the Bash tool with the 'mv' command instead. For larger edits, use the Write tool to overwrite files. For Jupyter notebooks (.ipynb files), use the NotebookEdit instead.

Before using this tool:

1. Use the View tool to understand the file's contents and context

2. Verify the directory path is correct (only applicable when creating new files):
   - Use the LS tool to verify the parent directory exists and is the correct location"""
        
    @property
    @override
    def parameters(self) -> dict[str, Any]:
        """Get the parameter specifications for the tool.
        
        Returns:
            Parameter specifications
        """
        return {
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify (must be absolute, not relative)",
                },
                "old_string": {
                    "type": "string",
                    "description": "The text to replace (must match the file contents exactly, including all whitespace and indentation)",
                },
                "new_string": {
                    "type": "string",
                    "description": "The edited text to replace the old_string",
                },
                "expected_replacements": {
                    "type": "number",
                    "default": 1,
                    "description": "The expected number of replacements to perform. Defaults to 1 if not specified.",
                }
            },
            "required": ["file_path", "old_string", "new_string"],
            "type": "object",
            "additionalProperties": False,
        }
        
    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.
        
        Returns:
            List of required parameter names
        """
        return ["file_path", "old_string", "new_string"]
        
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
        file_path = params.get("file_path")
        old_string = params.get("old_string")
        new_string = params.get("new_string")
        expected_replacements = params.get("expected_replacements", 1)  # Default to 1 if not provided
        
        if not file_path:
            await tool_ctx.error("Parameter 'file_path' is required but was None")
            return "Error: Parameter 'file_path' is required but was None"

        if file_path.strip() == "":
            await tool_ctx.error("Parameter 'file_path' cannot be empty")
            return "Error: Parameter 'file_path' cannot be empty"

        # Validate parameters
        path_validation = self.validate_path(file_path)
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
            await tool_ctx.error("Parameter 'old_string' cannot be empty for existing files")
            return "Error: Parameter 'old_string' cannot be empty for existing files"

        if new_string is None:
            await tool_ctx.error("Parameter 'new_string' is required but was None")
            return "Error: Parameter 'new_string' is required but was None"

        if expected_replacements is None or not isinstance(expected_replacements, (int, float)) or expected_replacements < 0:
            await tool_ctx.error("Parameter 'expected_replacements' must be a non-negative number")
            return "Error: Parameter 'expected_replacements' must be a non-negative number"

        await tool_ctx.info(f"Editing file: {file_path}")

        # Check if file is allowed to be edited
        allowed, error_msg = await self.check_path_allowed(file_path, tool_ctx)
        if not allowed:
            return error_msg

        try:
            file_path_obj = Path(file_path)
            
            # If the file doesn't exist and old_string is empty, create a new file
            if not file_path_obj.exists() and old_string == "":
                # Check if parent directory is allowed
                parent_dir = str(file_path_obj.parent)
                if not self.is_path_allowed(parent_dir):
                    await tool_ctx.error(f"Parent directory not allowed: {parent_dir}")
                    return f"Error: Parent directory not allowed: {parent_dir}"

                # Create parent directories if they don't exist
                file_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                # Create the new file with the new_string content
                with open(file_path_obj, "w", encoding="utf-8") as f:
                    f.write(new_string)
                
                # Add to document context
                self.document_context.add_document(file_path, new_string)
                
                await tool_ctx.info(f"Successfully created file: {file_path}")
                return f"Successfully created file: {file_path} ({len(new_string)} bytes)"
            
            # Check file exists for non-creation operations
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
                formatted_diff = (
                    f"```{num_backticks}diff\n{diff_text}```{num_backticks}\n"
                )

                # Write the file if there are changes
                if diff_text:
                    with open(file_path_obj, "w", encoding="utf-8") as f:
                        f.write(modified_content)

                    # Update document context
                    self.document_context.update_document(file_path, modified_content)

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
            
    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this edit tool with the MCP server.
        
        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.
        
        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure
        
        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def edit(ctx: MCPContext, file_path: str, old_string: str, new_string: str, expected_replacements: int = 1) -> str:
            return await tool_self.call(
                ctx, 
                file_path=file_path, 
                old_string=old_string, 
                new_string=new_string, 
                expected_replacements=expected_replacements
            )