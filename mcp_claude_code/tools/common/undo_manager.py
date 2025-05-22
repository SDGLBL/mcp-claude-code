"""Undo manager for tracking and reverting file operations.

This module provides the UndoManager system for tracking file modifications
and enabling undo functionality for write and edit operations.
"""

import time
from typing import Any, final


@final
class UndoOperation:
    """Represents a single undoable operation."""

    def __init__(
        self,
        file_path: str,
        operation_type: str,
        timestamp: float,
        previous_content: str | None,
        new_content: str,
        operation_details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an undo operation.

        Args:
            file_path: Absolute path to the file that was modified
            operation_type: Type of operation ("write" or "edit")
            timestamp: When the operation occurred (Unix timestamp)
            previous_content: File content before the operation (None if file didn't exist)
            new_content: File content after the operation
            operation_details: Additional details about the operation
        """
        self.file_path: str = file_path
        self.operation_type: str = operation_type
        self.timestamp: float = timestamp
        self.previous_content: str | None = previous_content
        self.new_content: str = new_content
        self.operation_details: dict[str, Any] = operation_details or {}

    def format_summary(self) -> str:
        """Format a human-readable summary of this operation.

        Returns:
            Formatted summary string
        """
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))
        
        if self.operation_type == "write":
            if self.previous_content is None:
                action = "Created file"
            else:
                action = "Overwrote file"
        elif self.operation_type == "edit":
            replacements = self.operation_details.get("expected_replacements", 1)
            action = f"Edited file ({replacements} replacement{'s' if replacements != 1 else ''})"
        else:
            action = f"Modified file ({self.operation_type})"

        return f"{time_str}: {action} - {len(self.new_content)} bytes"


@final
class UndoManager:
    """Manages undo operations for file modifications."""

    def __init__(self, max_operations_per_file: int = 10, enabled: bool = True) -> None:
        """Initialize the undo manager.

        Args:
            max_operations_per_file: Maximum number of operations to keep per file
            enabled: Whether undo functionality is enabled
        """
        self.max_operations_per_file: int = max_operations_per_file
        self.enabled: bool = enabled
        self.operations: dict[str, list[UndoOperation]] = {}

    def record_operation(
        self,
        file_path: str,
        operation_type: str,
        previous_content: str | None,
        new_content: str,
        operation_details: dict[str, Any] | None = None,
    ) -> None:
        """Record an operation for potential undo.

        Args:
            file_path: Absolute path to the file that was modified
            operation_type: Type of operation ("write" or "edit")
            previous_content: File content before the operation (None if file didn't exist)
            new_content: File content after the operation
            operation_details: Additional details about the operation
        """
        if not self.enabled:
            return

        # Create the operation record
        operation = UndoOperation(
            file_path=file_path,
            operation_type=operation_type,
            timestamp=time.time(),
            previous_content=previous_content,
            new_content=new_content,
            operation_details=operation_details,
        )

        # Initialize file history if needed
        if file_path not in self.operations:
            self.operations[file_path] = []

        # Add the operation
        self.operations[file_path].append(operation)

        # Trim history if it exceeds the limit
        if len(self.operations[file_path]) > self.max_operations_per_file:
            # Remove oldest operations
            self.operations[file_path] = self.operations[file_path][
                -self.max_operations_per_file:
            ]

    def undo_last_operation(self, file_path: str) -> UndoOperation | None:
        """Remove and return the last operation for a file.

        Args:
            file_path: Absolute path to the file

        Returns:
            The last operation if available, None otherwise
        """
        if not self.enabled:
            return None

        if file_path not in self.operations or not self.operations[file_path]:
            return None

        # Remove and return the last operation
        return self.operations[file_path].pop()

    def get_undo_history(
        self, file_path: str, limit: int | None = None
    ) -> list[UndoOperation]:
        """Get undo history for a file.

        Args:
            file_path: Absolute path to the file
            limit: Maximum number of operations to return (most recent first)

        Returns:
            List of operations in reverse chronological order (most recent first)
        """
        if file_path not in self.operations:
            return []

        operations = self.operations[file_path]

        # Return in reverse order (most recent first)
        if limit is not None:
            return operations[-limit:][::-1]
        else:
            return operations[::-1]

    def has_undo_available(self, file_path: str) -> bool:
        """Check if undo is available for a file.

        Args:
            file_path: Absolute path to the file

        Returns:
            True if undo operations are available, False otherwise
        """
        if not self.enabled:
            return False

        return file_path in self.operations and len(self.operations[file_path]) > 0

    def clear_history(self, file_path: str | None = None) -> None:
        """Clear undo history for a file or all files.

        Args:
            file_path: Absolute path to the file, or None to clear all history
        """
        if file_path is None:
            # Clear all history
            self.operations.clear()
        else:
            # Clear history for specific file
            if file_path in self.operations:
                del self.operations[file_path]

    def get_total_operations_count(self) -> int:
        """Get the total number of operations tracked.

        Returns:
            Total number of operations across all files
        """
        return sum(len(ops) for ops in self.operations.values())

    def get_files_with_history(self) -> list[str]:
        """Get list of files that have undo history.

        Returns:
            List of file paths with available undo operations
        """
        return [
            file_path
            for file_path, ops in self.operations.items()
            if len(ops) > 0
        ]

    def get_memory_usage_estimate(self) -> int:
        """Get an estimate of memory usage in bytes.

        Returns:
            Estimated memory usage in bytes
        """
        total_bytes = 0
        for operations in self.operations.values():
            for op in operations:
                # Estimate memory for content strings
                if op.previous_content:
                    total_bytes += len(op.previous_content.encode('utf-8'))
                total_bytes += len(op.new_content.encode('utf-8'))
                total_bytes += len(op.file_path.encode('utf-8'))
                
                # Rough estimate for other fields
                total_bytes += 100  # timestamp, operation_type, details, etc.

        return total_bytes
