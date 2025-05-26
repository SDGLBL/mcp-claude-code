"""Directory tree tool implementation.

This module provides the directory_tree tool for viewing file and directory structures.
Converted to FastMCP v2 function-based pattern.
"""

from pathlib import Path
from typing import Any

from fastmcp import Context as MCPContext
from fastmcp import FastMCP

from mcp_claude_code.tools.common.base import (
    is_path_allowed,
    validate_path,
)
from mcp_claude_code.tools.common.context import create_tool_context


async def directory_tree(
    path: str, ctx: MCPContext, depth: int = 3, include_filtered: bool = False
) -> str:
    """Get a recursive tree view of files and directories with customizable depth and filtering.

    Returns a structured view of the directory tree with files and subdirectories.
    Directories are marked with trailing slashes. The output is formatted as an
    indented list for readability. By default, common development directories like
    .git, node_modules, and venv are noted but not traversed unless explicitly
    requested. Only works within allowed directories.

    Args:
        path: The path to the directory to view
        ctx: MCP context for the tool call
        depth: The maximum depth to traverse (0 for unlimited)
        include_filtered: Include directories that are normally filtered

    Returns:
        Tool execution results
    """
    tool_ctx = create_tool_context(ctx)
    tool_ctx.set_tool_info("directory_tree")

    if not path:
        await tool_ctx.error("Parameter 'path' is required but was None")
        return "Error: Parameter 'path' is required but was None"

    if path.strip() == "":
        await tool_ctx.error("Parameter 'path' cannot be empty")
        return "Error: Parameter 'path' cannot be empty"

    # Validate path parameter
    path_validation = validate_path(path)
    if path_validation.is_error:
        await tool_ctx.error(path_validation.error_message)
        return f"Error: {path_validation.error_message}"

    await tool_ctx.info(
        f"Getting directory tree: {path} (depth: {depth}, include_filtered: {include_filtered})"
    )

    # Check if path is allowed
    if not is_path_allowed(path):
        await tool_ctx.error(
            f"Access denied - path outside allowed directories: {path}"
        )
        return f"Error: Access denied - path outside allowed directories: {path}"

    try:
        dir_path = Path(path)

        # Check if path exists
        if not dir_path.exists():
            await tool_ctx.error(f"Path does not exist: {path}")
            return f"Error: Path does not exist: {path}"

        # Check if path is a directory
        if not dir_path.is_dir():
            await tool_ctx.error(f"Path is not a directory: {path}")
            return f"Error: Path is not a directory: {path}"

        # Define filtered directories
        FILTERED_DIRECTORIES = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".idea",
            ".vs",
            ".vscode",
            "dist",
            "build",
            "target",
            ".ruff_cache",
            ".llm-context",
        }

        # Log filtering settings
        await tool_ctx.info(
            f"Directory tree filtering: include_filtered={include_filtered}"
        )

        # Check if a directory should be filtered
        def should_filter(current_path: Path) -> bool:
            # Don't filter if it's the explicitly requested path
            if str(current_path.absolute()) == str(dir_path.absolute()):
                # Don't filter explicitly requested paths
                return False

            # Filter based on directory name if filtering is enabled
            return current_path.name in FILTERED_DIRECTORIES and not include_filtered

        # Track stats for summary
        stats = {
            "directories": 0,
            "files": 0,
            "skipped_depth": 0,
            "skipped_filtered": 0,
        }

        # Build the tree recursively
        async def build_tree(
            current_path: Path, current_depth: int = 0
        ) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []

            # Skip processing if path isn't allowed
            if not is_path_allowed(str(current_path)):
                return result

            try:
                # Sort entries: directories first, then files alphabetically
                entries = sorted(
                    current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name)
                )

                for entry in entries:
                    # Skip entries that aren't allowed
                    if not is_path_allowed(str(entry)):
                        continue

                    if entry.is_dir():
                        stats["directories"] += 1
                        entry_data: dict[str, Any] = {
                            "name": entry.name,
                            "type": "directory",
                        }

                        # Check if we should filter this directory
                        if should_filter(entry):
                            entry_data["skipped"] = "filtered-directory"
                            stats["skipped_filtered"] += 1
                            result.append(entry_data)
                            continue

                        # Check depth limit (if enabled)
                        if depth > 0 and current_depth >= depth:
                            entry_data["skipped"] = "depth-limit"
                            stats["skipped_depth"] += 1
                            result.append(entry_data)
                            continue

                        # Process children recursively with depth increment
                        entry_data["children"] = await build_tree(
                            entry, current_depth + 1
                        )
                        result.append(entry_data)
                    else:
                        # Files should be at the same level check as directories
                        if depth <= 0 or current_depth < depth:
                            stats["files"] += 1
                            # Add file entry
                            result.append({"name": entry.name, "type": "file"})

            except Exception as e:
                await tool_ctx.warning(f"Error processing {current_path}: {str(e)}")

            return result

        # Format the tree as a simple indented structure
        def format_tree(tree_data: list[dict[str, Any]], level: int = 0) -> list[str]:
            lines = []

            for item in tree_data:
                # Indentation based on level
                indent = "  " * level

                # Format based on type
                if item["type"] == "directory":
                    if "skipped" in item:
                        lines.append(
                            f"{indent}{item['name']}/ [skipped - {item['skipped']}]"
                        )
                    else:
                        lines.append(f"{indent}{item['name']}/")
                        # Add children with increased indentation if present
                        if "children" in item:
                            lines.extend(format_tree(item["children"], level + 1))
                else:
                    # File
                    lines.append(f"{indent}{item['name']}")

            return lines

        # Build tree starting from the requested directory
        tree_data = await build_tree(dir_path)

        # Format as simple text
        formatted_output = "\n".join(format_tree(tree_data))

        # Add stats summary
        summary = (
            f"\nDirectory Stats: {stats['directories']} directories, {stats['files']} files "
            f"({stats['skipped_depth']} skipped due to depth limit, "
            f"{stats['skipped_filtered']} filtered directories skipped)"
        )

        await tool_ctx.info(
            f"Generated directory tree for {path} (depth: {depth}, include_filtered: {include_filtered})"
        )

        return formatted_output + summary
    except Exception as e:
        await tool_ctx.error(f"Error generating directory tree: {str(e)}")
        return f"Error generating directory tree: {str(e)}"


def register_directory_tree_tool(mcp_server: FastMCP) -> None:
    """Register the directory_tree tool with the MCP server.

    Args:
        mcp_server: The FastMCP server instance
    """
    mcp_server.tool()(directory_tree)
