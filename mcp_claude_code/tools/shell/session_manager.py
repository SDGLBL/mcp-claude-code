"""Session manager for coordinating bash sessions.

This module provides the SessionManager class which manages the lifecycle
of BashSession instances, handling creation, retrieval, and cleanup.
"""

import os
import shutil
import threading
from typing import Optional

from mcp_claude_code.tools.shell.bash_session import BashSession
from mcp_claude_code.tools.shell.session_storage import SessionStorage


class SessionManager:
    """Manager for bash sessions with tmux support.

    This singleton class manages the creation, retrieval, and cleanup
    of persistent bash sessions.
    """

    _instance: Optional["SessionManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "SessionManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the session manager."""
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self.default_timeout_seconds = 30
        self.default_session_timeout = 1800  # 30 minutes

    def is_tmux_available(self) -> bool:
        """Check if tmux is available on the system.

        Returns:
            True if tmux is available, False otherwise
        """
        return shutil.which("tmux") is not None

    def get_or_create_session(
        self,
        session_id: str,
        work_dir: str,
        username: str | None = None,
        no_change_timeout_seconds: int | None = None,
        max_memory_mb: int | None = None,
    ) -> BashSession:
        """Get an existing session or create a new one.

        Args:
            session_id: Unique identifier for the session
            work_dir: Working directory for the session
            username: Username to run commands as
            no_change_timeout_seconds: Timeout for commands with no output changes
            max_memory_mb: Memory limit for the session

        Returns:
            BashSession instance

        Raises:
            RuntimeError: If tmux is not available
        """
        # Check if tmux is available
        if not self.is_tmux_available():
            raise RuntimeError(
                "tmux is not available on this system. "
                "Please install tmux to use session-based command execution."
            )

        # Try to get existing session
        session = SessionStorage.get_session(session_id)
        if session is not None:
            return session

        # Create new session
        timeout = no_change_timeout_seconds or self.default_timeout_seconds
        session = BashSession(
            work_dir=work_dir,
            username=username,
            no_change_timeout_seconds=timeout,
            max_memory_mb=max_memory_mb,
        )

        # Store the session
        SessionStorage.set_session(session_id, session)

        return session

    def get_session(self, session_id: str) -> BashSession | None:
        """Get an existing session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            BashSession instance if found, None otherwise
        """
        return SessionStorage.get_session(session_id)

    def remove_session(self, session_id: str) -> bool:
        """Remove a session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            True if session was removed, False if not found
        """
        return SessionStorage.remove_session(session_id)

    def cleanup_expired_sessions(self, max_age_seconds: int | None = None) -> int:
        """Clean up sessions that haven't been accessed recently.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup

        Returns:
            Number of sessions cleaned up
        """
        max_age = max_age_seconds or self.default_session_timeout
        return SessionStorage.cleanup_expired_sessions(max_age)

    def get_session_count(self) -> int:
        """Get the number of active sessions.

        Returns:
            Number of active sessions
        """
        return SessionStorage.get_session_count()

    def get_all_session_ids(self) -> list[str]:
        """Get all active session IDs.

        Returns:
            List of active session IDs
        """
        return SessionStorage.get_all_session_ids()

    def clear_all_sessions(self) -> int:
        """Clear all sessions.

        Returns:
            Number of sessions cleared
        """
        return SessionStorage.clear_all_sessions()

    def validate_session_id(self, session_id: str) -> tuple[bool, str]:
        """Validate a session ID.

        Args:
            session_id: The session ID to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not session_id:
            return False, "Session ID cannot be empty"

        if not isinstance(session_id, str):
            return False, "Session ID must be a string"

        # Check for reasonable length
        if len(session_id) > 100:
            return False, "Session ID too long (max 100 characters)"

        # Check for valid characters (alphanumeric, dash, underscore)
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
            return (
                False,
                "Session ID can only contain alphanumeric characters, dashes, and underscores",
            )

        return True, ""
