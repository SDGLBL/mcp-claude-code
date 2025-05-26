"""Read notebook tool implementation.

This module provides the notebook_read tool for reading Jupyter notebook files.
Converted to FastMCP v2 function-based pattern.
"""

import json
from pathlib import Path

from fastmcp import Context as MCPContext

from mcp_claude_code.tools.common.base import is_path_allowed
from mcp_claude_code.tools.common.context import create_tool_context
from mcp_claude_code.tools.jupyter.base import parse_notebook, format_notebook_cells


async def notebook_read(
    notebook_path: str,
    ctx: MCPContext,
) -> str:
    """Reads a Jupyter notebook (.ipynb file) and returns all of the cells with their outputs.

    Jupyter notebooks are interactive documents that combine code, text, and
    visualizations, commonly used for data analysis and scientific computing.
    The notebook_path parameter must be an absolute path, not a relative path.

    Args:
        notebook_path: The absolute path to the Jupyter notebook file to read
        ctx: MCP context

    Returns:
        Formatted string representation of the notebook cells and outputs

    Raises:
        ValueError: If the path is invalid or the file is not a notebook
        FileNotFoundError: If the notebook file does not exist
        PermissionError: If access to the file is denied
    """
    # Create tool context
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("notebook_read")

    # Validate and resolve path
    path = Path(notebook_path).resolve()

    # Check permissions
    if not is_path_allowed(path, tool_ctx):
        raise PermissionError(f"Access denied to path: {path}")

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"Notebook file not found: {path}")

    # Check if it's a file (not directory)
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Ensure it's a notebook file
    if path.suffix != ".ipynb":
        raise ValueError(f"File must be a Jupyter notebook (.ipynb): {path}")

    try:
        # Parse the notebook using standalone functions
        notebook_data, cells = await parse_notebook(path)

        # Format the cells as readable output
        formatted_cells = format_notebook_cells(cells)

        # Update context with file read
        tool_ctx.document_context.update_file_content(str(path), formatted_cells)

        await tool_ctx.info(
            f"Successfully read notebook: {notebook_path} ({len(cells)} cells)"
        )
        return formatted_cells

    except json.JSONDecodeError as e:
        await tool_ctx.log_error(f"Invalid JSON in notebook file: {e}")
        raise ValueError(f"Invalid JSON in notebook file: {e}")
    except Exception as e:
        await tool_ctx.log_error(f"Failed to read notebook: {e}")
        raise
