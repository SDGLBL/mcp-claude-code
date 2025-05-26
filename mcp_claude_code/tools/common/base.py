"""Base classes for MCP Claude Code tools.

This module provides abstract base classes that define interfaces and common functionality
for all tools used in MCP Claude Code. These abstractions help ensure consistent tool
behavior and provide a foundation for tool registration and management.

This module supports both FastMCP v1 (legacy class-based) and v2 (function-based) patterns
during the migration period.
"""

import functools
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, final

from fastmcp import Context as MCPContext
from fastmcp import FastMCP

from mcp_claude_code.tools.common.context import DocumentContext
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.common.validation import (
    ValidationResult,
    validate_path_parameter,
)


def handle_connection_errors(
    func: Callable[..., Awaitable[str]],
) -> Callable[..., Awaitable[str]]:
    """Decorator to handle connection errors in MCP tool functions.

    This decorator wraps tool functions to catch ClosedResourceError and other
    connection-related exceptions that occur when the client disconnects.

    Args:
        func: The async tool function to wrap

    Returns:
        Wrapped function that handles connection errors gracefully
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Check if this is a connection-related error
            error_name = type(e).__name__
            if any(
                name in error_name
                for name in [
                    "ClosedResourceError",
                    "ConnectionError",
                    "BrokenPipeError",
                ]
            ):
                # Client has disconnected - log the error but don't crash
                # Return a simple error message (though it likely won't be received)
                return f"Client disconnected during operation: {error_name}"
            else:
                # Re-raise non-connection errors
                raise

    return wrapper


class BaseTool(ABC):
    """Abstract base class for all MCP Claude Code tools.

    This class defines the core interface that all tools must implement, ensuring
    consistency in how tools are registered, documented, and called.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the tool name.

        Returns:
            The tool name as it will appear in the MCP server
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Detailed description of the tool's purpose and usage
        """
        pass

    @property
    def mcp_description(self) -> str:
        """Get the complete tool description for MCP.

        This method combines the tool description with parameter descriptions.

        Returns:
            Complete tool description including parameter details
        """
        # Start with the base description
        desc = self.description.strip()

        # Add parameter descriptions section if there are parameters
        if self.parameters and "properties" in self.parameters:
            # Add Args section header
            desc += "\n\nArgs:"

            # Get the properties dictionary
            properties = self.parameters["properties"]

            # Add each parameter description
            for param_name, param_info in properties.items():
                # Get the title if available, otherwise use the parameter name and capitalize it
                if "title" in param_info:
                    title = param_info["title"]
                else:
                    # Convert snake_case to Title Case
                    title = " ".join(
                        word.capitalize() for word in param_name.split("_")
                    )

                # Check if the parameter is required
                required = param_name in self.required
                required_text = "" if required else " (optional)"

                # Get the parameter description if available
                param_description = ""
                if "description" in param_info:
                    param_description = f" - {param_info['description']}"

                # Add the parameter description line
                desc += f"\n    {param_name}: {title}{required_text}{param_description}"

        # Add Returns section
        desc += "\n\nReturns:\n    "

        # Add a generic return description based on the tool's purpose
        # This could be enhanced with more specific return descriptions
        if "read" in self.name or "get" in self.name or "search" in self.name:
            desc += f"{self.name.replace('_', ' ').capitalize()} results"
        elif "write" in self.name or "edit" in self.name or "create" in self.name:
            desc += "Result of the operation"
        else:
            desc += "Tool execution results"

        return desc

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Get the parameter specifications for the tool.

        Returns:
            Dictionary containing parameter specifications in JSON Schema format
        """
        pass

    @property
    @abstractmethod
    def required(self) -> list[str]:
        """Get the list of required parameter names.

        Returns:
            List of parameter names that are required for the tool
        """
        pass

    @abstractmethod
    async def call(self, ctx: MCPContext, **params: Any) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context for the tool call
            **params: Tool parameters provided by the caller

        Returns:
            Tool execution result as a string
        """
        pass

    @abstractmethod
    def register(self, mcp_server: FastMCP) -> None:
        """Register this tool with the MCP server.

        This method must be implemented by each tool class to create a wrapper function
        with explicitly defined parameters that calls this tool's call method.
        The wrapper function is then registered with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        pass


class FileSystemTool(BaseTool, ABC):
    """Base class for filesystem-related tools.

    Provides common functionality for working with files and directories,
    including permission checking and path validation.
    """

    def __init__(
        self, document_context: DocumentContext, permission_manager: PermissionManager
    ) -> None:
        """Initialize filesystem tool.

        Args:
            document_context: Document context for tracking file contents
            permission_manager: Permission manager for access control
        """
        self.document_context: DocumentContext = document_context
        self.permission_manager: PermissionManager = permission_manager

    def validate_path(self, path: str, param_name: str = "path") -> ValidationResult:
        """Validate a path parameter.

        Args:
            path: Path to validate
            param_name: Name of the parameter (for error messages)

        Returns:
            Validation result containing validation status and error message if any
        """
        return validate_path_parameter(path, param_name)

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed according to permission settings.

        Args:
            path: Path to check

        Returns:
            True if the path is allowed, False otherwise
        """
        return self.permission_manager.is_path_allowed(path)


@final
class ToolRegistry:
    """Registry for MCP Claude Code tools.

    Provides functionality for registering tool implementations with an MCP server,
    handling the conversion between tool classes and MCP tool functions.
    """

    @staticmethod
    def register_tool(mcp_server: FastMCP, tool: BaseTool) -> None:
        """Register a tool with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
            tool: The tool to register
        """
        # Use the tool's register method which handles all the details
        tool.register(mcp_server)

    @staticmethod
    def register_tools(mcp_server: FastMCP, tools: list[BaseTool]) -> None:
        """Register multiple tools with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
            tools: List of tools to register
        """
        for tool in tools:
            ToolRegistry.register_tool(mcp_server, tool)


# FastMCP v2 style helper functions and utilities


def create_simple_tool_wrapper(
    tool_func: Callable[..., Awaitable[str]], context_required: bool = True
) -> Callable[..., Awaitable[str]]:
    """Create a simple wrapper for tool functions.

    This helper creates wrappers for FastMCP v2 style tool functions,
    ensuring proper context handling and error management.

    Args:
        tool_func: The tool function to wrap
        context_required: Whether the function requires context injection

    Returns:
        Wrapped function ready for FastMCP v2 registration
    """

    @handle_connection_errors
    @functools.wraps(tool_func)
    async def wrapper(*args: Any, **kwargs: Any) -> str:
        # For FastMCP v2, context is automatically injected
        return await tool_func(*args, **kwargs)

    return wrapper


class SimpleFileSystemTool:
    """Simplified base for filesystem tools using FastMCP v2 pattern.

    This class provides utility methods for filesystem tools without requiring
    complex inheritance patterns. Tools can use this as a mixin or utility.
    """

    def __init__(
        self, document_context: DocumentContext, permission_manager: PermissionManager
    ) -> None:
        """Initialize filesystem tool utilities.

        Args:
            document_context: Document context for tracking file contents
            permission_manager: Permission manager for access control
        """
        self.document_context: DocumentContext = document_context
        self.permission_manager: PermissionManager = permission_manager

    def validate_path(self, path: str, param_name: str = "path") -> ValidationResult:
        """Validate a path parameter.

        Args:
            path: Path to validate
            param_name: Name of the parameter (for error messages)

        Returns:
            Validation result containing validation status and error message if any
        """
        return validate_path_parameter(path, param_name)

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed according to permission settings.

        Args:
            path: Path to check

        Returns:
            True if the path is allowed, False otherwise
        """
        return self.permission_manager.is_path_allowed(path)


# Global instances for simplified filesystem tools
# These will be initialized by the tool registration system
_document_context: DocumentContext | None = None
_permission_manager: PermissionManager | None = None


def initialize_global_tool_context(
    document_context: DocumentContext, permission_manager: PermissionManager
) -> None:
    """Initialize global context for simplified tools.

    Args:
        document_context: Document context for tracking file contents
        permission_manager: Permission manager for access control
    """
    global _document_context, _permission_manager
    _document_context = document_context
    _permission_manager = permission_manager


def get_document_context() -> DocumentContext:
    """Get the global document context.

    Returns:
        Document context instance

    Raises:
        RuntimeError: If context not initialized
    """
    if _document_context is None:
        raise RuntimeError(
            "Document context not initialized. Call initialize_global_tool_context first."
        )
    return _document_context


def get_permission_manager() -> PermissionManager:
    """Get the global permission manager.

    Returns:
        Permission manager instance

    Raises:
        RuntimeError: If permission manager not initialized
    """
    if _permission_manager is None:
        raise RuntimeError(
            "Permission manager not initialized. Call initialize_global_tool_context first."
        )
    return _permission_manager


def validate_path(path: str, param_name: str = "path") -> ValidationResult:
    """Validate a path parameter using global context.

    Args:
        path: Path to validate
        param_name: Name of the parameter (for error messages)

    Returns:
        Validation result containing validation status and error message if any
    """
    return validate_path_parameter(path, param_name)


def is_path_allowed(path: str) -> bool:
    """Check if a path is allowed using global permission manager.

    Args:
        path: Path to check

    Returns:
        True if the path is allowed, False otherwise
    """
    permission_manager = get_permission_manager()
    return permission_manager.is_path_allowed(path)
