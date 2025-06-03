"""Session manager for coordinating bash sessions.

This module provides the SessionManager class which manages the lifecycle
of BashSession instances, handling creation, retrieval, and cleanup.
"""

import shutil
import threading
from typing import Self, final

from mcp_claude_code.tools.shell.bash_session import BashSession
from mcp_claude_code.tools.shell.session_storage import SessionStorage


@final
class SessionManager:
    """Manager for bash sessions with tmux support.

    This class manages the creation, retrieval, and cleanup
    of persistent bash sessions. By default, it uses a singleton pattern,
    but can be instantiated directly for dependency injection scenarios.
    """

    _instance: Self | None = None
    _lock = threading.Lock()

    def __new__(
        cls, use_singleton: bool = True, session_storage: SessionStorage | None = None
    ) -> "SessionManager":
        """Create SessionManager instance.

        Args:
            use_singleton: If True, use singleton pattern. If False, create new instance.
        """
        if not use_singleton:
            # Create a new instance without singleton behavior
            instance = super().__new__(cls)
            instance._initialized = False
            return instance

        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self, use_singleton: bool = True, session_storage: SessionStorage | None = None
    ) -> None:
        """Initialize the session manager.

        Args:
            use_singleton: If True, use singleton pattern (for backward compatibility)
            session_storage: Optional session storage instance for dependency injection
        """
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self.default_timeout_seconds = 30
        self.default_session_timeout = 1800  # 30 minutes

        # Allow dependency injection of session storage for isolation
        if session_storage is not None:
            self._session_storage = session_storage
        elif use_singleton:
            # Use the default global SessionStorage for singleton instances
            from mcp_claude_code.tools.shell.session_storage import SessionStorage

            self._session_storage = SessionStorage
        else:
            # Use isolated instance storage for non-singleton instances
            from mcp_claude_code.tools.shell.session_storage import (
                SessionStorageInstance,
            )

            self._session_storage = SessionStorageInstance()

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
        poll_interval: float | None = None,
    ) -> BashSession:
        """Get an existing session or create a new one.

        Args:
            session_id: Unique identifier for the session
            work_dir: Working directory for the session
            username: Username to run commands as
            no_change_timeout_seconds: Timeout for commands with no output changes
            max_memory_mb: Memory limit for the session
            poll_interval: Polling interval in seconds (default 0.5, use 0.1 for tests)

        Returns:
            BashSession instance

        Raises:
            RuntimeError: If tmux is not available
        """
        # Check if tmux is available
        if not self.is_tmux_available():
            raise RuntimeError(
                "tmux is not available on this system. Please install tmux to use session-based command execution."
            )

        # Try to get existing session
        session = self._session_storage.get_session(session_id)
        if session is not None:
            return session

        # Create new session
        timeout = no_change_timeout_seconds or self.default_timeout_seconds
        interval = poll_interval if poll_interval is not None else 0.5
        session = BashSession(
            id=session_id,
            work_dir=work_dir,
            username=username,
            no_change_timeout_seconds=timeout,
            max_memory_mb=max_memory_mb,
            poll_interval=interval,
        )

        # Store the session
        self._session_storage.set_session(session_id, session)

        return session

    def get_session(self, session_id: str) -> BashSession | None:
        """Get an existing session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            BashSession instance if found, None otherwise
        """
        return self._session_storage.get_session(session_id)

    def remove_session(self, session_id: str) -> bool:
        """Remove a session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            True if session was removed, False if not found
        """
        return self._session_storage.remove_session(session_id)

    def cleanup_expired_sessions(self, max_age_seconds: int | None = None) -> int:
        """Clean up sessions that haven't been accessed recently.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup

        Returns:
            Number of sessions cleaned up
        """
        max_age = max_age_seconds or self.default_session_timeout
        return self._session_storage.cleanup_expired_sessions(max_age)

    def get_session_count(self) -> int:
        """Get the number of active sessions.

        Returns:
            Number of active sessions
        """
        return self._session_storage.get_session_count()

    def get_all_session_ids(self) -> list[str]:
        """Get all active session IDs.

        Returns:
            List of active session IDs
        """
        return self._session_storage.get_all_session_ids()

    def clear_all_sessions(self) -> int:
        """Clear all sessions.

        Returns:
            Number of sessions cleared
        """
        return self._session_storage.clear_all_sessions()
