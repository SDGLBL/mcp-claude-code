"""Read tool implementation.

This module provides the read tool for reading the contents of files.
Converted to FastMCP v2 function-based pattern.
"""

from pathlib import Path

from fastmcp import Context as MCPContext
from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import get_document_context, is_path_allowed
from mcp_claude_code.tools.common.context import create_tool_context


# Default values for truncation
DEFAULT_LINE_LIMIT = 2000
MAX_LINE_LENGTH = 2000
LINE_TRUNCATION_INDICATOR = "... [line truncated]"


async def read(
    file_path: str, ctx: MCPContext, offset: int = 0, limit: int = DEFAULT_LINE_LIMIT
) -> str:
    """Reads a file from the local filesystem. You can access any file directly by using this tool.
    Assume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.

    Usage:
    - The file_path parameter must be an absolute path, not a relative path
    - By default, it reads up to 2000 lines starting from the beginning of the file
    - You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters
    - Any lines longer than 2000 characters will be truncated
    - Results are returned using cat -n format, with line numbers starting at 1
    - For Jupyter notebooks (.ipynb files), use the notebook_read instead
    - When reading multiple files, you MUST use the batch tool to read them all at once

    Args:
        file_path: The absolute path to the file to read
        offset: The line number to start reading from. Only provide if the file is too large to read at once
        limit: The number of lines to read. Only provide if the file is too large to read at once.
        ctx: MCP context for the tool call

    Returns:
        Tool execution results
    """
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("read")

    # Validate the 'file_path' parameter
    if not file_path:
        await tool_ctx.error("Parameter 'file_path' is required but was None")
        return "Error: Parameter 'file_path' is required but was None"

    await tool_ctx.info(f"Reading file: {file_path} (offset: {offset}, limit: {limit})")

    # Check if path is allowed
    if not is_path_allowed(file_path):
        await tool_ctx.error(
            f"Access denied - path outside allowed directories: {file_path}"
        )
        return f"Error: Access denied - path outside allowed directories: {file_path}"

    try:
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            await tool_ctx.error(f"File does not exist: {file_path}")
            return f"Error: File does not exist: {file_path}"

        if not file_path_obj.is_file():
            await tool_ctx.error(f"Path is not a file: {file_path}")
            return f"Error: Path is not a file: {file_path}"

        # Read the file
        try:
            # Read and process the file with line numbers and truncation
            lines = []
            current_line = 0
            truncated_lines = 0

            # Try with utf-8 encoding first
            try:
                with open(file_path_obj, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        # Skip lines before offset
                        if i < offset:
                            continue

                        # Stop after reading 'limit' lines
                        if current_line >= limit:
                            truncated_lines = True
                            break

                        current_line += 1

                        # Truncate long lines
                        if len(line) > MAX_LINE_LENGTH:
                            line = line[:MAX_LINE_LENGTH] + LINE_TRUNCATION_INDICATOR

                        # Add line with line number (1-based)
                        lines.append(f"{i + 1:6d}  {line.rstrip()}")

                # Add to document context (store the full content for future reference)
                with open(file_path_obj, "r", encoding="utf-8") as f:
                    full_content = f.read()
                document_context = get_document_context()
                document_context.add_document(file_path, full_content)

            except UnicodeDecodeError:
                # Try with latin-1 encoding
                try:
                    lines = []
                    current_line = 0
                    truncated_lines = 0

                    with open(file_path_obj, "r", encoding="latin-1") as f:
                        for i, line in enumerate(f):
                            # Skip lines before offset
                            if i < offset:
                                continue

                            # Stop after reading 'limit' lines
                            if current_line >= limit:
                                truncated_lines = True
                                break

                            current_line += 1

                            # Truncate long lines
                            if len(line) > MAX_LINE_LENGTH:
                                line = (
                                    line[:MAX_LINE_LENGTH] + LINE_TRUNCATION_INDICATOR
                                )

                            # Add line with line number (1-based)
                            lines.append(f"{i + 1:6d}  {line.rstrip()}")

                    # Add to document context (store the full content for future reference)
                    with open(file_path_obj, "r", encoding="latin-1") as f:
                        full_content = f.read()
                    document_context = get_document_context()
                    document_context.add_document(file_path, full_content)

                    await tool_ctx.warning(
                        f"File read with latin-1 encoding: {file_path}"
                    )

                except Exception:
                    await tool_ctx.error(f"Cannot read binary file: {file_path}")
                    return f"Error: Cannot read binary file: {file_path}"

            # Format the result
            result = "\n".join(lines)

            # Add truncation message if necessary
            if truncated_lines:
                result += f"\n... (output truncated, showing {limit} of {limit + truncated_lines}+ lines)"

            await tool_ctx.info(f"Successfully read file: {file_path}")
            return result

        except Exception as e:
            await tool_ctx.error(f"Error reading file: {str(e)}")
            return f"Error: {str(e)}"

    except Exception as e:
        await tool_ctx.error(f"Error reading file: {str(e)}")
        return f"Error: {str(e)}"


def register_read_tool(mcp_server: FastMCP) -> None:
    """Register the read tool with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
    """
    mcp_server.tool()(read)
