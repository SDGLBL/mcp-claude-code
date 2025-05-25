"""Parameter validation utilities for MCP Claude Code tools.

This module provides utilities for validating parameters in tool functions.
"""

from typing import TypeVar, final

T = TypeVar("T")


@final
class ValidationResult:
    """Result of a parameter validation."""

    def __init__(self, is_valid: bool, error_message: str = ""):
        """Initialize a validation result.

        Args:
            is_valid: Whether the parameter is valid
            error_message: Optional error message for invalid parameters
        """
        self.is_valid: bool = is_valid
        self.error_message: str = error_message

    @property
    def is_error(self) -> bool:
        """Check if the validation resulted in an error.

        Returns:
            True if there was a validation error, False otherwise
        """
        return not self.is_valid


def validate_path_parameter(
    path: str | None, parameter_name: str = "path"
) -> ValidationResult:
    """Validate a path parameter.

    Args:
        path: The path parameter to validate
        parameter_name: The name of the parameter (for error messages)

    Returns:
        A ValidationResult indicating whether the parameter is valid
    """
    # Check for None
    if path is None:
        return ValidationResult(
            is_valid=False,
            error_message=f"Path parameter '{parameter_name}' is required but was None",
        )

    # Check for empty path
    if path.strip() == "":
        return ValidationResult(
            is_valid=False,
            error_message=f"Path parameter '{parameter_name}' is required but was empty string",
        )

    # Path is valid
    return ValidationResult(is_valid=True)
