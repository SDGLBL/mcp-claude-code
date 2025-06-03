"""Test fixtures for the MCP Claude Code project."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_claude_code.tools.common.context import ToolContext
from mcp_claude_code.tools.common.permissions import PermissionManager
from mcp_claude_code.tools.shell.bash_session_executor import BashSessionExecutor


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def test_file(temp_dir):
    """Create a test file in the temporary directory."""
    test_file_path = Path(temp_dir) / "test_file.txt"
    test_content = "This is a test file content.\nWith multiple lines.\n"

    with open(test_file_path, "w") as f:
        f.write(test_content)

    return str(test_file_path)


@pytest.fixture
def test_project_dir(temp_dir):
    """Create a simple test project structure."""
    project_dir = Path(temp_dir) / "test_project"
    project_dir.mkdir()

    # Create Python files
    py_dir = project_dir / "src" / "module"
    py_dir.mkdir(parents=True)

    with open(py_dir / "__init__.py", "w") as f:
        f.write("# Module init\n")

    with open(py_dir / "main.py", "w") as f:
        f.write("import os\n\ndef main():\n    print('Hello, world!')\n")

    # Create requirements.txt
    with open(project_dir / "requirements.txt", "w") as f:
        f.write("pytest==7.3.1\nmcp>=1.3.0\nhttpx>=0.27\n")

    # Create README
    with open(project_dir / "README.md", "w") as f:
        f.write("# Test Project\n\nThis is a test project for testing.\n")

    return str(project_dir)


@pytest.fixture
def permission_manager():
    """Create a permission manager with a test path allowed."""
    manager = PermissionManager()
    return manager


@pytest.fixture
def mcp_context():
    """Mock MCP context for testing."""
    mock_context = MagicMock()
    mock_context.info = AsyncMock()
    mock_context.error = AsyncMock()
    mock_context.warning = AsyncMock()
    mock_context.debug = AsyncMock()
    mock_context.report_progress = AsyncMock()
    mock_context.read_resource = AsyncMock()
    mock_context.request_id = "test-request-id"
    mock_context.client_id = "test-client-id"
    return mock_context


@pytest.fixture
def tool_context(mcp_context):
    """Create a tool context for testing."""
    return ToolContext(mcp_context)


@pytest.fixture
def command_executor(permission_manager):
    """Create a command executor for testing."""
    return BashSessionExecutor(permission_manager)
