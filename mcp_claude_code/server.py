"""MCP server implementing Claude Code capabilities."""

import os
from pathlib import Path
from typing import Any, Literal, cast, final

from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.shell.command_execution import CommandExecution
from mcp_claude_code.context import DocumentContext
from mcp_claude_code.executors import ProjectAnalyzer
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.project import ProjectManager
from mcp_claude_code.tools import register_all_tools


@final
class ClaudeCodeServer:
    """MCP server implementing Claude Code capabilities."""

    def __init__(self, name: str = "claude-code", allowed_paths: list[str] | None = None):
        """Initialize the Claude Code server.
        
        Args:
            name: The name of the server
            allowed_paths: list of paths that the server is allowed to access
        """
        self.mcp = FastMCP(name)
        
        # Initialize context, permissions, and command executor
        self.document_context = DocumentContext()
        self.permission_manager = PermissionManager()
        
        # Initialize command executor
        self.command_executor = CommandExecution(
            permission_manager=self.permission_manager,
            verbose=False  # Set to True for debugging
        )
        
        # Initialize project analyzer
        self.project_analyzer = ProjectAnalyzer(self.command_executor)
        
        # Initialize project manager
        self.project_manager = ProjectManager(
            self.document_context,
            self.permission_manager,
            self.project_analyzer
        )
        
        # Add allowed paths
        if allowed_paths:
            for path in allowed_paths:
                self.permission_manager.add_allowed_path(path)
                self.document_context.add_allowed_path(path)
        
        # Register all tools
        register_all_tools(
            mcp_server=self.mcp,
            document_context=self.document_context,
            permission_manager=self.permission_manager,
            command_executor=self.command_executor,
            project_manager=self.project_manager,
            project_analyzer=self.project_analyzer
        )
    
    def run(self, transport: str = 'stdio', allowed_paths: list[str] | None = None):
        """Run the MCP server.
        
        Args:
            transport: The transport to use (stdio or sse)
            allowed_paths: list of paths that the server is allowed to access
        """
        # Add allowed paths if provided
        allowed_paths_list = allowed_paths or []
        for path in allowed_paths_list:
            self.permission_manager.add_allowed_path(path)
            self.document_context.add_allowed_path(path)
        
        # Run the server
        transport_type = cast(Literal['stdio', 'sse'], transport)
        self.mcp.run(transport=transport_type)


def main():
    """Run the Claude Code MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MCP server implementing Claude Code capabilities"
    )
    
    _ = parser.add_argument(
        "--name",
        default="claude-code",
        help="Name of the MCP server (default: claude-code)"
    )
    
    _ = parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol to use (default: stdio)"
    )
    
    _ = parser.add_argument(
        "--allow-path",
        action="append",
        dest="allowed_paths",
        help="Add an allowed path (can be specified multiple times)"
    )
    
    args = parser.parse_args()
    
    # Type annotations for args to avoid Any warnings
    name: str = args.name
    transport: str = args.transport
    allowed_paths: list[str] | None = args.allowed_paths
    
    # Create and run the server
    server = ClaudeCodeServer(name=name, allowed_paths=allowed_paths)
    server.run(transport=transport, allowed_paths=allowed_paths or [])


if __name__ == "__main__":
    main()
