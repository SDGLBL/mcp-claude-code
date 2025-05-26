"""Grep AST tool implementation.

This module provides the grep_ast tool for searching through source code files with AST context,
seeing matching lines with useful context showing how they fit into the code structure.
Converted to FastMCP v2 function-based pattern.
"""

from pathlib import Path

from grep_ast.grep_ast import TreeContext
from fastmcp import Context as MCPContext
from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import (
    is_path_allowed,
    validate_path,
)
from mcp_claude_code.tools.common.context import create_tool_context


async def grep_ast(
    pattern: str,
    path: str,
    ctx: MCPContext,
    ignore_case: bool = False,
    line_number: bool = False,
) -> str:
    """Search through source code files and see matching lines with useful AST (Abstract Syntax Tree) context. This tool helps you understand code structure by showing how matched lines fit into functions, classes, and other code blocks.

    Unlike traditional search tools like `search_content` that only show matching lines, `grep_ast` leverages the AST to reveal the structural context around matches, making it easier to understand the code organization.

    When to use this tool:
    1. When you need to understand where a pattern appears within larger code structures
    2. When searching for function or class definitions that match a pattern
    3. When you want to see not just the matching line but its surrounding context in the code
    4. When exploring unfamiliar codebases and need structural context
    5. When examining how a specific pattern is used across different parts of the codebase

    This tool is superior to regular grep/search_content when you need to understand code structure, not just find text matches.

    Example usage:
    ```
    grep_ast(pattern="function_name", path="/path/to/file.py", ignore_case=False, line_number=True)
    ```

    Args:
        pattern: The regex pattern to search for in source code files
        path: The path to search in (file or directory)
        ctx: MCP context for the tool call
        ignore_case: Whether to ignore case when matching
        line_number: Whether to display line numbers

    Returns:
        Tool execution results
    """
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("grep_ast")

    # Validate required parameters
    if pattern is None:
        await tool_ctx.error("Parameter 'pattern' is required but was None")
        return "Error: Parameter 'pattern' is required but was None"

    if isinstance(pattern, str) and pattern.strip() == "":
        await tool_ctx.error("Parameter 'pattern' cannot be empty")
        return "Error: Parameter 'pattern' cannot be empty"

    if path is None:
        await tool_ctx.error("Parameter 'path' is required but was None")
        return "Error: Parameter 'path' is required but was None"

    if isinstance(path, str) and path.strip() == "":
        await tool_ctx.error("Parameter 'path' cannot be empty")
        return "Error: Parameter 'path' cannot be empty"

    # Validate path parameter
    path_validation = validate_path(path)
    if path_validation.is_error:
        await tool_ctx.error(path_validation.error_message)
        return f"Error: {path_validation.error_message}"

    await tool_ctx.info(
        f"Searching AST for pattern '{pattern}' in path: {path} (ignore_case: {ignore_case}, line_number: {line_number})"
    )

    # Check if path is allowed
    if not is_path_allowed(path):
        await tool_ctx.error(
            f"Access denied - path outside allowed directories: {path}"
        )
        return f"Error: Access denied - path outside allowed directories: {path}"

    try:
        path_obj = Path(path)

        # Check if path exists
        if not path_obj.exists():
            await tool_ctx.error(f"Path does not exist: {path}")
            return f"Error: Path does not exist: {path}"

        await tool_ctx.info(f"Analyzing code structure for pattern: {pattern}")

        # Use TreeContext to get AST-based search results
        tree_context = TreeContext()

        # Prepare arguments for TreeContext.run
        args = type(
            "Args",
            (),
            {
                "pattern": pattern,
                "path": str(path_obj),
                "ignore_case": ignore_case,
                "line_number": line_number,
                "no_line_number": not line_number,  # TreeContext expects this inverse flag
            },
        )()

        # Capture output by temporarily redirecting stdout
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            # Run the TreeContext analysis
            tree_context.run(args)

            # Get the captured output
            result = captured_output.getvalue()
        finally:
            # Restore stdout
            sys.stdout = old_stdout

        if not result or result.strip() == "":
            return f"No matches found for pattern '{pattern}' in {path}"

        await tool_ctx.info(f"Found AST matches for pattern '{pattern}'")
        return result.strip()

    except Exception as e:
        await tool_ctx.error(f"Error searching AST: {str(e)}")
        return f"Error searching AST: {str(e)}"


def register_grep_ast_tool(mcp_server: FastMCP) -> None:
    """Register the grep_ast tool with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
    """
    mcp_server.tool()(grep_ast)
