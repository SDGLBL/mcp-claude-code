"""Session storage module for shell command sessions.

This module provides storage functionality for managing persistent shell sessions.
It supports both global class-based storage (for backward compatibility) and
instance-based storage (for dependency injection scenarios).
"""

import time
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from mcp_claude_code.tools.shell.bash_session import BashSession


@final
class SessionStorageInstance:
    """Instance-based storage for shell command sessions.

    This class provides isolated storage for different SessionManager instances,
    preventing shared state between different contexts. It includes LRU eviction
    and TTL-based cleanup to prevent memory leaks.
    """

    def __init__(self, max_sessions: int = 20, default_ttl_seconds: int = 300):
        """Initialize instance storage.

        Args:
            max_sessions: Maximum number of sessions to keep (LRU eviction after this)
            default_ttl_seconds: Default TTL for sessions in seconds (5 minutes)
        """
        self._sessions: dict[str, "BashSession"] = {}
        self._last_access: dict[str, float] = {}
        self._access_order: list[str] = []  # Track access order for LRU
        self.max_sessions = max_sessions
        self.default_ttl_seconds = default_ttl_seconds

    def _update_access_order(self, session_id: str) -> None:
        """Update the access order for LRU tracking.

        Args:
            session_id: The session that was accessed
        """
        # Remove from current position if exists
        if session_id in self._access_order:
            self._access_order.remove(session_id)
        # Add to end (most recently used)
        self._access_order.append(session_id)

    def _evict_lru_if_needed(self) -> None:
        """Evict least recently used sessions if over capacity."""
        # More aggressive eviction: start evicting when we reach 80% capacity
        eviction_threshold = max(1, int(self.max_sessions * 0.8))
        while len(self._sessions) >= eviction_threshold and self._access_order:
            # Get least recently used session (first in list)
            lru_session_id = self._access_order[0]
            self.remove_session(lru_session_id)

    def get_session(self, session_id: str) -> "BashSession | None":
        """Get a session by ID.

        Args:
            session_id: The session identifier

        Returns:
            The session if found, None otherwise
        """
        session = self._sessions.get(session_id)
        if session:
            current_time = time.time()
            self._last_access[session_id] = current_time
            self._update_access_order(session_id)

            # Check if session has expired
            session_age = current_time - self._last_access.get(session_id, current_time)
            if session_age > self.default_ttl_seconds:
                self.remove_session(session_id)
                return None

        return session

    def set_session(self, session_id: str, session: "BashSession") -> None:
        """Store a session.

        Args:
            session_id: The session identifier
            session: The session to store
        """
        current_time = time.time()

        # If session already exists, update it
        if session_id in self._sessions:
            self._sessions[session_id] = session
            self._last_access[session_id] = current_time
            self._update_access_order(session_id)
        else:
            # New session - check if we need to evict first
            self._evict_lru_if_needed()

            # Add new session
            self._sessions[session_id] = session
            self._last_access[session_id] = current_time
            self._update_access_order(session_id)

    def remove_session(self, session_id: str) -> bool:
        """Remove a session from storage.

        Args:
            session_id: The session identifier

        Returns:
            True if session was removed, False if not found
        """
        session = self._sessions.pop(session_id, None)
        self._last_access.pop(session_id, None)

        # Remove from access order tracking
        if session_id in self._access_order:
            self._access_order.remove(session_id)

        if session:
            # Clean up the session resources
            try:
                session.close()
            except Exception:
                pass  # Ignore cleanup errors
            return True
        return False

    def get_session_count(self) -> int:
        """Get the number of active sessions.

        Returns:
            Number of active sessions
        """
        return len(self._sessions)

    def get_all_session_ids(self) -> list[str]:
        """Get all active session IDs.

        Returns:
            List of active session IDs
        """
        return list(self._sessions.keys())

    def cleanup_expired_sessions(self, max_age_seconds: int | None = None) -> int:
        """Clean up sessions that haven't been accessed recently.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup.
                           If None, uses instance default TTL.

        Returns:
            Number of sessions cleaned up
        """
        max_age = (
            max_age_seconds if max_age_seconds is not None else self.default_ttl_seconds
        )
        current_time = time.time()
        expired_sessions: list[str] = []

        for session_id, last_access in self._last_access.items():
            if current_time - last_access > max_age:
                expired_sessions.append(session_id)

        cleaned_count = 0
        for session_id in expired_sessions:
            if self.remove_session(session_id):
                cleaned_count += 1

        return cleaned_count

    def clear_all_sessions(self) -> int:
        """Clear all sessions.

        Returns:
            Number of sessions cleared
        """
        session_ids = list(self._sessions.keys())
        cleared_count = 0

        for session_id in session_ids:
            if self.remove_session(session_id):
                cleared_count += 1

        return cleared_count

    def get_lru_session_ids(self) -> list[str]:
        """Get session IDs in LRU order (least recently used first).

        Returns:
            List of session IDs in LRU order
        """
        return self._access_order.copy()

    def get_session_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        return {
            "total_sessions": len(self._sessions),
            "max_sessions": self.max_sessions,
            "utilization": len(self._sessions) / self.max_sessions
            if self.max_sessions > 0
            else 0,
            "default_ttl_seconds": self.default_ttl_seconds,
        }


class SessionStorage:
    """Global class-based storage for shell command sessions.

    This class maintains backward compatibility while providing the same
    interface as SessionStorageInstance for global session management.
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
    def cleanup_expired_sessions(cls, max_age_seconds: int = 300) -> int:
        """Clean up sessions that haven't been accessed recently.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup (default: 5 minutes)

        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        expired_sessions: list[str] = []

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
