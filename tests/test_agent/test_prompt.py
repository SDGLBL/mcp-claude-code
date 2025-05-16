"""Tests for the agent tool prompt module."""

import os
from unittest.mock import MagicMock

import pytest

from mcp_claude_code.tools.agent.prompt import (
    get_allowed_agent_tools,
    get_default_model,
    get_model_parameters,
    get_system_prompt,
)
from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.permissions import PermissionManager


class TestPrompt:
    """Test cases for the agent tool prompt module."""

    @pytest.fixture
    def permission_manager(self):
        """Create a test permission manager."""
        return MagicMock(spec=PermissionManager)

    @pytest.fixture
    def mock_tools(self):
        """Create a list of mock tools."""
        tools = []

        # Create a read-only tool
        read_tool = MagicMock(spec=BaseTool)
        read_tool.name = "read"
        read_tool.description = "Read files"
        read_tool.isReadOnly = MagicMock(return_value=True)
        read_tool.needsPermissions = MagicMock(return_value=False)
        tools.append(read_tool)

        # Create a non-read-only tool
        write_tool = MagicMock(spec=BaseTool)
        write_tool.name = "write"
        write_tool.description = "Write to files"
        write_tool.isReadOnly = MagicMock(return_value=False)
        write_tool.needsPermissions = MagicMock(return_value=True)
        tools.append(write_tool)

        # Create a tool that needs permissions
        cmd_tool = MagicMock(spec=BaseTool)
        cmd_tool.name = "run_command"
        cmd_tool.description = "Run shell commands"
        cmd_tool.isReadOnly = MagicMock(return_value=False)
        cmd_tool.needsPermissions = MagicMock(return_value=True)
        tools.append(cmd_tool)

        # Create an agent tool (should be filtered out to prevent recursion)
        agent_tool = MagicMock(spec=BaseTool)
        agent_tool.name = "agent"
        agent_tool.description = "Launch agent"
        agent_tool.isReadOnly = MagicMock(return_value=True)
        agent_tool.needsPermissions = MagicMock(return_value=False)
        tools.append(agent_tool)

        return tools

    def test_get_allowed_agent_tools(self, mock_tools, permission_manager):
        """Test get_allowed_agent_tools only filters out the agent tool."""
        # Get allowed tools
        allowed_tools = get_allowed_agent_tools(mock_tools, permission_manager)

        # Should include all tools except for agent
        assert len(allowed_tools) == 3
        assert "read" in [tool.name for tool in allowed_tools]
        assert "write" in [tool.name for tool in allowed_tools]
        assert "run_command" in [tool.name for tool in allowed_tools]
        assert "agent" not in [tool.name for tool in allowed_tools]

    def test_get_system_prompt(self, mock_tools, permission_manager):
        """Test get_system_prompt includes all tools except agent."""
        # Get system prompt
        system_prompt = get_system_prompt(mock_tools, permission_manager)

        # Should mention all tools except agent
        assert "`read`" in system_prompt
        assert "`write`" in system_prompt
        assert "`run_command`" in system_prompt
        assert "`agent`" not in system_prompt

        # Should mention read-only limitation
        assert "read-only tools" in system_prompt
        assert "you cannot modify files or execute commands" in system_prompt

    def test_get_default_model(self):
        """Test get_default_model."""
        # Test with environment variable
        os.environ["AGENT_MODEL"] = "test-model-123"
        assert get_default_model() == "test-model-123"

        # Test with model override - explicitly with TEST_MODE to avoid provider prefix
        os.environ["TEST_MODE"] = "1"
        assert get_default_model("openai/gpt-4o") == "openai/gpt-4o"
        assert (
            get_default_model("gpt-4o-mini") == "gpt-4o-mini"
        )  # In test mode, no prefix added
        assert (
            get_default_model("anthropic/claude-3-sonnet")
            == "anthropic/claude-3-sonnet"
        )

        # Test with provider prefixing in non-test mode
        del os.environ["TEST_MODE"]
        assert get_default_model("gpt-4") == "openai/gpt-4"

        # Test default
        del os.environ["AGENT_MODEL"]
        assert get_default_model() == "openai/gpt-4o"

    def test_get_model_parameters(self):
        """Test get_model_parameters."""
        # Test with environment variables
        os.environ["AGENT_TEMPERATURE"] = "0.5"
        os.environ["AGENT_API_TIMEOUT"] = "30"
        os.environ["AGENT_MAX_TOKENS"] = "2000"

        params = get_model_parameters()
        assert params["temperature"] == 0.5
        assert params["timeout"] == 30
        assert params["max_tokens"] == 2000

        # Test with max_tokens override
        params = get_model_parameters(max_tokens=1500)
        assert params["temperature"] == 0.5
        assert params["timeout"] == 30
        assert params["max_tokens"] == 1500  # Override takes precedence

        # Test defaults
        del os.environ["AGENT_TEMPERATURE"]
        del os.environ["AGENT_API_TIMEOUT"]
        del os.environ["AGENT_MAX_TOKENS"]

        params = get_model_parameters()
        assert params["temperature"] == 0.7
        assert params["timeout"] == 60
        assert "max_tokens" not in params  # Not set when not provided

        # Test with only max_tokens override
        params = get_model_parameters(max_tokens=1000)
        assert params["temperature"] == 0.7
        assert params["timeout"] == 60
        assert params["max_tokens"] == 1000
