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

from mcp.server.fastmcp import Context as MCPContext
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


@final
class DocumentContext:
    """Manages document context and codebase understanding."""

    def __init__(self) -> None:
        """Initialize the document context."""
        self.documents: dict[str, str] = {}
        self.document_metadata: dict[str, dict[str, Any]] = {}
        self.modified_times: dict[str, float] = {}
        self.allowed_paths: set[Path] = set()

    def add_allowed_path(self, path: str) -> None:
        """Add a path to the allowed paths.

        Args:
            path: The path to allow
        """
        resolved_path: Path = Path(path).resolve()
        self.allowed_paths.add(resolved_path)

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed.

        Args:
            path: The path to check

        Returns:
            True if the path is allowed, False otherwise
        """
        resolved_path: Path = Path(path).resolve()

        # Check if the path is within any allowed path
        for allowed_path in self.allowed_paths:
            try:
                _ = resolved_path.relative_to(allowed_path)
                return True
            except ValueError:
                continue

        return False

    def add_document(
        self, path: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Add a document to the context.

        Args:
            path: The path of the document
            content: The content of the document
            metadata: Optional metadata about the document
        """
        self.documents[path] = content
        self.modified_times[path] = time.time()

        if metadata:
            self.document_metadata[path] = metadata
        else:
            # Try to infer metadata
            self.document_metadata[path] = self._infer_metadata(path, content)

    def get_document(self, path: str) -> str | None:
        """Get a document from the context.

        Args:
            path: The path of the document

        Returns:
            The document content, or None if not found
        """
        return self.documents.get(path)

    def get_document_metadata(self, path: str) -> dict[str, Any] | None:
        """Get document metadata.

        Args:
            path: The path of the document

        Returns:
            The document metadata, or None if not found
        """
        return self.document_metadata.get(path)

    def update_document(self, path: str, content: str) -> None:
        """Update a document in the context.

        Args:
            path: The path of the document
            content: The new content of the document
        """
        self.documents[path] = content
        self.modified_times[path] = time.time()

        # Update metadata
        self.document_metadata[path] = self._infer_metadata(path, content)

    def remove_document(self, path: str) -> None:
        """Remove a document from the context.

        Args:
            path: The path of the document
        """
        if path in self.documents:
            del self.documents[path]

        if path in self.document_metadata:
            del self.document_metadata[path]

        if path in self.modified_times:
            del self.modified_times[path]

    def _infer_metadata(self, path: str, content: str) -> dict[str, Any]:
        """Infer metadata about a document.

        Args:
            path: The path of the document
            content: The content of the document

        Returns:
            Inferred metadata
        """
        extension: str = Path(path).suffix.lower()

        metadata: dict[str, Any] = {
            "extension": extension,
            "size": len(content),
            "line_count": content.count("\n") + 1,
        }

        # Infer language based on extension
        language_map: dict[str, list[str]] = {
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx"],
            "java": [".java"],
            "c++": [".c", ".cpp", ".h", ".hpp"],
            "go": [".go"],
            "rust": [".rs"],
            "ruby": [".rb"],
            "php": [".php"],
            "html": [".html", ".htm"],
            "css": [".css"],
            "markdown": [".md"],
            "json": [".json"],
            "yaml": [".yaml", ".yml"],
            "xml": [".xml"],
            "sql": [".sql"],
            "shell": [".sh", ".bash"],
        }

        # Find matching language
        for language, extensions in language_map.items():
            if extension in extensions:
                metadata["language"] = language
                break
        else:
            metadata["language"] = "text"

        return metadata

    def load_directory(
        self,
        directory: str,
        recursive: bool = True,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        """Load all files in a directory into the context.

        Args:
            directory: The directory to load
            recursive: Whether to load subdirectories
            exclude_patterns: Patterns to exclude
        """
        if not self.is_path_allowed(directory):
            raise ValueError(f"Directory not allowed: {directory}")

        dir_path: Path = Path(directory)

        if not dir_path.exists() or not dir_path.is_dir():
            raise ValueError(f"Not a valid directory: {directory}")

        if exclude_patterns is None:
            exclude_patterns = []

        # Common directories and files to exclude
        default_excludes: list[str] = [
            "__pycache__",
            ".git",
            ".github",
            ".ssh",
            ".gnupg",
            ".config",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            ".idea",
            ".vscode",
            ".DS_Store",
        ]

        exclude_patterns.extend(default_excludes)

        def should_exclude(path: Path) -> bool:
            """Check if a path should be excluded.

            Args:
                path: The path to check

            Returns:
                True if the path should be excluded, False otherwise
            """
            for pattern in exclude_patterns:
                if pattern.startswith("*"):
                    if path.name.endswith(pattern[1:]):
                        return True
                elif pattern in str(path):
                    return True
            return False

        # Walk the directory
        for root, dirs, files in os.walk(dir_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]

            # Process files
            for file in files:
                file_path: Path = Path(root) / file

                if should_exclude(file_path):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content: str = f.read()

                    # Add to context
                    self.add_document(str(file_path), content)
                except UnicodeDecodeError:
                    # Skip binary files
                    continue

            # Stop if not recursive
            if not recursive:
                break

    def to_json(self) -> str:
        """Convert the context to a JSON string.

        Returns:
            A JSON string representation of the context
        """
        data: dict[str, Any] = {
            "documents": self.documents,
            "metadata": self.document_metadata,
            "modified_times": self.modified_times,
            "allowed_paths": [str(p) for p in self.allowed_paths],
        }

        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "DocumentContext":
        """Create a context from a JSON string.

        Args:
            json_str: The JSON string

        Returns:
            A new DocumentContext instance
        """
        data: dict[str, Any] = json.loads(json_str)

        context = cls()
        context.documents = data.get("documents", {})
        context.document_metadata = data.get("metadata", {})
        context.modified_times = data.get("modified_times", {})
        context.allowed_paths = set(Path(p) for p in data.get("allowed_paths", []))

        return context
