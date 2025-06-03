"""Enhanced Context for MCP Claude Code tools.

This module provides an enhanced Context class that wraps the MCP Context
and adds additional functionality specific to Claude Code tools.
"""

import json
import os
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, ClassVar, final

from fastmcp import Context as MCPContext
from mcp.server.lowlevel.helper_types import ReadResourceContents


@final
class ToolContext:
    """Enhanced context for MCP Claude Code tools.

    This class wraps the MCP Context and adds additional functionality
    for tracking tool execution, progress reporting, and resource access.
    """

    # Track all active contexts for debugging
    _active_contexts: ClassVar[set["ToolContext"]] = set()

    def __init__(self, mcp_context: MCPContext) -> None:
        """Initialize the tool context.

        Args:
            mcp_context: The underlying MCP Context
        """
        self._mcp_context: MCPContext = mcp_context
        self._tool_name: str | None = None
        self._execution_id: str | None = None

        # Add to active contexts
        ToolContext._active_contexts.add(self)

    def __del__(self) -> None:
        """Clean up when the context is destroyed."""
        # Remove from active contexts
        ToolContext._active_contexts.discard(self)

    @property
    def mcp_context(self) -> MCPContext:
        """Get the underlying MCP Context.

        Returns:
            The MCP Context
        """
        return self._mcp_context

    @property
    def request_id(self) -> str:
        """Get the request ID from the MCP context.

        Returns:
            The request ID
        """
        return self._mcp_context.request_id

    @property
    def client_id(self) -> str | None:
        """Get the client ID from the MCP context.

        Returns:
            The client ID
        """
        return self._mcp_context.client_id

    def set_tool_info(self, tool_name: str, execution_id: str | None = None) -> None:
        """Set information about the currently executing tool.

        Args:
            tool_name: The name of the tool being executed
            execution_id: Optional unique execution ID
        """
        self._tool_name = tool_name
        self._execution_id = execution_id

    async def info(self, message: str) -> None:
        """Log an informational message.

        Args:
            message: The message to log
        """
        try:
            await self._mcp_context.info(self._format_message(message))
        except Exception:
            # Silently ignore errors when client has disconnected
            pass

    async def debug(self, message: str) -> None:
        """Log a debug message.

        Args:
            message: The message to log
        """
        try:
            await self._mcp_context.debug(self._format_message(message))
        except Exception:
            # Silently ignore errors when client has disconnected
            pass

    async def warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: The message to log
        """
        try:
            await self._mcp_context.warning(self._format_message(message))
        except Exception:
            # Silently ignore errors when client has disconnected
            pass

    async def error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: The message to log
        """
        try:
            await self._mcp_context.error(self._format_message(message))
        except Exception:
            # Silently ignore errors when client has disconnected
            pass

    def _format_message(self, message: str) -> str:
        """Format a message with tool information if available.

        Args:
            message: The original message

        Returns:
            The formatted message
        """
        if self._tool_name:
            if self._execution_id:
                return f"[{self._tool_name}:{self._execution_id}] {message}"
            return f"[{self._tool_name}] {message}"
        return message

    async def report_progress(self, current: int, total: int) -> None:
        """Report progress to the client.

        Args:
            current: Current progress value
            total: Total progress value
        """
        try:
            await self._mcp_context.report_progress(current, total)
        except Exception:
            # Silently ignore errors when client has disconnected
            pass

    async def read_resource(self, uri: str) -> Iterable[ReadResourceContents]:
        """Read a resource via the MCP protocol.

        Args:
            uri: The resource URI

        Returns:
            A tuple of (content, mime_type)
        """
        return await self._mcp_context.read_resource(uri)


# Factory function to create a ToolContext from an MCP Context
def create_tool_context(mcp_context: MCPContext) -> ToolContext:
    """Create a ToolContext from an MCP Context.

    Args:
        mcp_context: The MCP Context

    Returns:
        A new ToolContext
    """
    return ToolContext(mcp_context)
