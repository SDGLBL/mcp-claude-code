"""Write file tool implementation.

This module provides the write tool for creating or overwriting files.
Converted to FastMCP v2 function-based pattern.
"""

from pathlib import Path

from fastmcp import Context as MCPContext
from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import (
    get_document_context,
    is_path_allowed,
    validate_path,
)
from mcp_claude_code.tools.common.context import create_tool_context


async def write(file_path: str, content: str, ctx: MCPContext) -> str:
    """Writes a file to the local filesystem.

    Usage:
    - This tool will overwrite the existing file if there is one at the provided path.
    - If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.
    - ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
    - NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

    Args:
        file_path: The absolute path to the file to write (must be absolute, not relative)
        content: The content to write to the file
        ctx: MCP context for the tool call

    Returns:
        Result of the operation
    """
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("write")

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

    if not content:
        await tool_ctx.error("Parameter 'content' is required but was None")
        return "Error: Parameter 'content' is required but was None"

    await tool_ctx.info(f"Writing file: {file_path}")

    # Check if file is allowed to be written
    if not is_path_allowed(file_path):
        await tool_ctx.error(
            f"Access denied - path outside allowed directories: {file_path}"
        )
        return f"Error: Access denied - path outside allowed directories: {file_path}"

    try:
        path_obj = Path(file_path)

        # Check if parent directory is allowed
        parent_dir = str(path_obj.parent)
        if not is_path_allowed(parent_dir):
            await tool_ctx.error(f"Parent directory not allowed: {parent_dir}")
            return f"Error: Parent directory not allowed: {parent_dir}"

        # Create parent directories if they don't exist
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(path_obj, "w", encoding="utf-8") as f:
            f.write(content)

        # Add to document context
        document_context = get_document_context()
        document_context.add_document(file_path, content)

        await tool_ctx.info(
            f"Successfully wrote file: {file_path} ({len(content)} bytes)"
        )
        return f"Successfully wrote file: {file_path} ({len(content)} bytes)"
    except Exception as e:
        await tool_ctx.error(f"Error writing file: {str(e)}")
        return f"Error writing file: {str(e)}"


def register_write_tool(mcp_server: FastMCP) -> None:
    """Register the write tool with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
    """
    mcp_server.tool()(write)
