"""Undo tool implementation.

This module provides the UndoTool for reverting recent file operations.
"""

import time
from pathlib import Path
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool


@final
class UndoTool(FilesystemBaseTool):
    """Tool for undoing recent file operations."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "undo"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Undo the most recent write or edit operation on a file.

Reverts the file to its previous state before the last modification.
Only works on files that have been modified during the current session.
Can also list the undo history for a file to see available operations."""

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
                    "description": "Absolute path to the file to undo changes for",
                },
                "list_history": {
                    "type": "boolean",
                    "description": "If true, list available undo operations instead of performing undo",
                    "default": False,
                },
                "show_content": {
                    "type": "boolean", 
                    "description": "If true and list_history is true, show content preview for each operation",
                    "default": False,
                },
            },
            "required": ["file_path"],
            "type": "object",
        }

    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.

        Returns:
            List of required parameter names
        """
        return ["file_path"]

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
        list_history = params.get("list_history", False)
        show_content = params.get("show_content", False)

        # Validate required parameters
        if not file_path:
            await tool_ctx.error("Parameter 'file_path' is required but was None")
            return "Error: Parameter 'file_path' is required but was None"

        if file_path.strip() == "":
            await tool_ctx.error("Parameter 'file_path' cannot be empty")
            return "Error: Parameter 'file_path' cannot be empty"

        # Validate path parameter
        path_validation = self.validate_path(file_path)
        if path_validation.is_error:
            await tool_ctx.error(path_validation.error_message)
            return f"Error: {path_validation.error_message}"

        # Check if path is allowed
        allowed, error_msg = await self.check_path_allowed(file_path, tool_ctx)
        if not allowed:
            return error_msg

        # Check if undo manager is enabled
        if not self.document_context.undo_manager.enabled:
            await tool_ctx.error("Undo functionality is disabled")
            return "Error: Undo functionality is disabled on this server"

        if list_history:
            return await self._list_undo_history(file_path, show_content, tool_ctx)
        else:
            return await self._perform_undo(file_path, tool_ctx)

    async def _list_undo_history(
        self, file_path: str, show_content: bool, tool_ctx: Any
    ) -> str:
        """List the undo history for a file.

        Args:
            file_path: Path to the file
            show_content: Whether to show content previews
            tool_ctx: Tool context for logging

        Returns:
            Formatted history string
        """
        await tool_ctx.info(f"Listing undo history for: {file_path}")

        # Get undo history
        history = self.document_context.undo_manager.get_undo_history(file_path)

        if not history:
            return f"No undo history available for: {file_path}"

        # Format the history
        result_lines = [f"Undo history for: {file_path}", ""]

        for i, operation in enumerate(history):
            # Format basic operation info
            time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(operation.timestamp)
            )
            
            operation_desc = f"Operation {i + 1}: {operation.operation_type}"
            if operation.operation_type == "edit":
                replacements = operation.operation_details.get("actual_replacements", 1)
                operation_desc += f" ({replacements} replacement{'s' if replacements != 1 else ''})"
            elif operation.operation_type == "write":
                if operation.previous_content is None:
                    operation_desc += " (created file)"
                else:
                    operation_desc += " (overwrote file)"

            result_lines.append(f"{operation_desc}")
            result_lines.append(f"  Time: {time_str}")
            result_lines.append(f"  Content size: {len(operation.new_content)} bytes")

            if operation.previous_content is not None:
                result_lines.append(f"  Previous size: {len(operation.previous_content)} bytes")
            else:
                result_lines.append("  Previous: (file did not exist)")

            # Show content preview if requested
            if show_content:
                # Show first few lines of content
                preview_lines = operation.new_content.split('\n')[:3]
                if len(preview_lines) > 0:
                    result_lines.append("  Content preview:")
                    for line in preview_lines:
                        result_lines.append(f"    {line[:80]}{'...' if len(line) > 80 else ''}")
                    if len(operation.new_content.split('\n')) > 3:
                        result_lines.append("    ...")

            result_lines.append("")  # Empty line between operations

        # Add summary
        result_lines.append(f"Total operations: {len(history)}")
        result_lines.append(
            f"Use 'undo' without list_history=true to revert the most recent operation."
        )

        return "\n".join(result_lines)

    async def _perform_undo(self, file_path: str, tool_ctx: Any) -> str:
        """Perform the undo operation.

        Args:
            file_path: Path to the file
            tool_ctx: Tool context for logging

        Returns:
            Result message
        """
        await tool_ctx.info(f"Performing undo for: {file_path}")

        # Check if undo is available
        if not self.document_context.undo_manager.has_undo_available(file_path):
            return f"No undo operations available for: {file_path}"

        # Get the last operation
        last_operation = self.document_context.undo_manager.undo_last_operation(file_path)
        if last_operation is None:
            return f"Failed to retrieve undo operation for: {file_path}"

        try:
            file_path_obj = Path(file_path)

            # Revert the file based on the operation
            if last_operation.previous_content is None:
                # The operation created a new file, so delete it
                if file_path_obj.exists():
                    file_path_obj.unlink()
                    # Remove from document context
                    self.document_context.remove_document(file_path)
                    
                    await tool_ctx.info(f"Deleted file (undoing creation): {file_path}")
                    return f"Successfully undone file creation: {file_path} (file deleted)"
                else:
                    return f"File no longer exists, cannot undo creation: {file_path}"
            else:
                # Restore the previous content
                with open(file_path_obj, "w", encoding="utf-8") as f:
                    f.write(last_operation.previous_content)

                # Update document context
                self.document_context.update_document(file_path, last_operation.previous_content)

                # Format result message
                operation_desc = last_operation.format_summary()
                
                await tool_ctx.info(f"Restored file to previous state: {file_path}")
                return f"Successfully undone operation: {operation_desc}\nFile restored to previous state ({len(last_operation.previous_content)} bytes)"

        except Exception as e:
            # If undo fails, restore the operation to the history
            self.document_context.undo_manager.operations.setdefault(file_path, []).append(last_operation)
            
            await tool_ctx.error(f"Failed to undo operation: {str(e)}")
            return f"Error: Failed to undo operation for {file_path}: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this undo tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def undo(
            ctx: MCPContext,
            file_path: str,
            list_history: bool = False,
            show_content: bool = False,
        ) -> str:
            return await tool_self.call(
                ctx, 
                file_path=file_path, 
                list_history=list_history, 
                show_content=show_content
            )
