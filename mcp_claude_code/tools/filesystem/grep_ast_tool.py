"""Grep AST tool implementation.

This module provides the GrepAstTool for searching through source code files with AST context,
seeing matching lines with useful context showing how they fit into the code structure.
"""

import os
from pathlib import Path
from typing import Any, final, override

from grep_ast.grep_ast import TreeContext
from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.filesystem.base import FilesystemBaseTool


@final
class GrepAstTool(FilesystemBaseTool):
    """Tool for searching through source code files with AST context."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "grep_ast"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Search through source code files and see matching lines with useful context.

Grep source code files and see matching lines with useful context that show how they fit 
into the code structure. See the loops, functions, methods, classes, etc. that contain
all the matching lines. Get a sense of what's inside a matched class or function definition.
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
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for in source code files",
                },
                "path": {
                    "type": "string",
                    "description": "The path to search in (file or directory)",
                },
                "ignore_case": {
                    "type": "boolean",
                    "description": "Whether to ignore case when matching",
                    "default": False,
                },
                "line_number": {
                    "type": "boolean",
                    "description": "Whether to display line numbers",
                    "default": False,
                },
            },
            "required": ["pattern", "path"],
            "type": "object",
        }

    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.

        Returns:
            List of required parameter names
        """
        return ["pattern", "path"]

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
        pattern = params.get("pattern")
        path = params.get("path")
        ignore_case = params.get("ignore_case", False)
        line_number = params.get("line_number", False)

        # Validate parameters
        if not pattern:
            await tool_ctx.error("Parameter 'pattern' is required but was None")
            return "Error: Parameter 'pattern' is required but was None"

        if not path:
            await tool_ctx.error("Parameter 'path' is required but was None")
            return "Error: Parameter 'path' is required but was None"

        # Validate the path
        path_validation = self.validate_path(path)
        if not path_validation.is_valid:
            await tool_ctx.error(f"Invalid path: {path_validation.error}")
            return f"Error: Invalid path: {path_validation.error}"

        # Check if path is allowed
        is_allowed, error_message = await self.check_path_allowed(path, tool_ctx)
        if not is_allowed:
            return error_message

        # Check if path exists
        is_exists, error_message = await self.check_path_exists(path, tool_ctx)
        if not is_exists:
            return error_message

        await tool_ctx.info(f"Searching for '{pattern}' in {path}")

        # Get the files to process
        path_obj = Path(path)
        files_to_process = []

        if path_obj.is_file():
            files_to_process.append(str(path_obj))
        elif path_obj.is_dir():
            for root, _, files in os.walk(path_obj):
                for file in files:
                    file_path = Path(root) / file
                    if self.is_path_allowed(str(file_path)):
                        files_to_process.append(str(file_path))

        if not files_to_process:
            await tool_ctx.warning(f"No source code files found in {path}")
            return f"No source code files found in {path}"

        # Process each file
        results = []
        processed_count = 0

        await tool_ctx.info(f"Found {len(files_to_process)} file(s) to process")

        for file_path in files_to_process:
            await tool_ctx.report_progress(processed_count, len(files_to_process))

            try:
                # Read the file
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()

                # Process the file with grep-ast
                try:
                    tc = TreeContext(
                        file_path,
                        code,
                        color=False,
                        verbose=False,
                        line_number=line_number,
                    )

                    # Find matches
                    loi = tc.grep(pattern, ignore_case)

                    if loi:
                        tc.add_lines_of_interest(loi)
                        tc.add_context()
                        output = tc.format()

                        # Add the result to our list
                        results.append(f"\n{file_path}:\n{output}\n")
                except Exception as e:
                    # Skip files that can't be parsed by tree-sitter
                    await tool_ctx.warning(f"Could not parse {file_path}: {str(e)}")
            except UnicodeDecodeError:
                await tool_ctx.warning(f"Could not read {file_path} as text")
            except Exception as e:
                await tool_ctx.error(f"Error processing {file_path}: {str(e)}")

            processed_count += 1

        # Final progress report
        await tool_ctx.report_progress(len(files_to_process), len(files_to_process))

        if not results:
            await tool_ctx.warning(f"No matches found for '{pattern}' in {path}")
            return f"No matches found for '{pattern}' in {path}"

        await tool_ctx.info(f"Found matches in {len(results)} file(s)")

        # Join the results
        return "\n".join(results)

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def grep_ast(
            ctx: MCPContext,
            pattern: str,
            path: str,
            ignore_case: bool = False,
            line_number: bool = False,
        ) -> str:
            return await tool_self.call(
                ctx,
                pattern=pattern,
                path=path,
                ignore_case=ignore_case,
                line_number=line_number,
            )
