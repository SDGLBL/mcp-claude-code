"""Session storage module for shell command sessions.

This module provides storage functionality for managing persistent shell sessions,
similar to the TodoStorage pattern used in the todo tools.
"""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_claude_code.tools.shell.bash_session import BashSession


class SessionStorage:
    """In-memory storage for shell command sessions.

    This class manages the lifecycle of shell sessions, providing storage,
    retrieval, and cleanup functionality.
    """

    _sessions: dict[str, "BashSession"] = {}
    _last_access: dict[str, float] = {}

    @classmethod
    def get_session(cls, session_id: str) -> "BashSession | None":
        """Get a session by ID.

        Args:
            session_id: The session identifier

        Returns:
            The session if found, None otherwise
        """
        session = cls._sessions.get(session_id)
        if session:
            cls._last_access[session_id] = time.time()
        return session

    @classmethod
    def set_session(cls, session_id: str, session: "BashSession") -> None:
        """Store a session.

        Args:
            session_id: The session identifier
            session: The session to store
        """
        cls._sessions[session_id] = session
        cls._last_access[session_id] = time.time()

    @classmethod
    def remove_session(cls, session_id: str) -> bool:
        """Remove a session from storage.

        Args:
            session_id: The session identifier

        Returns:
            True if session was removed, False if not found
        """
        session = cls._sessions.pop(session_id, None)
        cls._last_access.pop(session_id, None)

        if session:
            # Clean up the session resources
            try:
                session.close()
            except Exception:
                pass  # Ignore cleanup errors
            return True
        return False

    @classmethod
    def get_session_count(cls) -> int:
        """Get the number of active sessions.

        Returns:
            Number of active sessions
        """
        return len(cls._sessions)

    @classmethod
    def get_all_session_ids(cls) -> list[str]:
        """Get all active session IDs.

        Returns:
            List of active session IDs
        """
        return list(cls._sessions.keys())

    @classmethod
    def cleanup_expired_sessions(cls, max_age_seconds: int = 1800) -> int:
        """Clean up sessions that haven't been accessed recently.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup (default: 30 minutes)

        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        expired_sessions = []

        for session_id, last_access in cls._last_access.items():
            if current_time - last_access > max_age_seconds:
                expired_sessions.append(session_id)

        cleaned_count = 0
        for session_id in expired_sessions:
            if cls.remove_session(session_id):
                cleaned_count += 1

        return cleaned_count

    @classmethod
    def clear_all_sessions(cls) -> int:
        """Clear all sessions.

        Returns:
            Number of sessions cleared
        """
        session_ids = list(cls._sessions.keys())
        cleared_count = 0

        for session_id in session_ids:
            if cls.remove_session(session_id):
                cleared_count += 1

        return cleared_count
