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
        read_tool.name = "read_files"
        read_tool.description = "Read files"
        read_tool.isReadOnly = MagicMock(return_value=True)
        read_tool.needsPermissions = MagicMock(return_value=False)
        tools.append(read_tool)
        
        # Create a non-read-only tool
        write_tool = MagicMock(spec=BaseTool)
        write_tool.name = "write_file"
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
        allowed_tools = get_allowed_agent_tools(
            mock_tools, 
            permission_manager
        )
        
        # Should include all tools except for agent
        assert len(allowed_tools) == 3
        assert "read_files" in [tool.name for tool in allowed_tools]
        assert "write_file" in [tool.name for tool in allowed_tools]
        assert "run_command" in [tool.name for tool in allowed_tools]
        assert "agent" not in [tool.name for tool in allowed_tools]
        
    def test_get_system_prompt(self, mock_tools, permission_manager):
        """Test get_system_prompt includes all tools except agent."""
        # Get system prompt
        system_prompt = get_system_prompt(
            mock_tools, 
            permission_manager
        )
        
        # Should mention all tools except agent
        assert "`read_files`" in system_prompt
        assert "`write_file`" in system_prompt
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
        
        # Test default
        del os.environ["AGENT_MODEL"]
        assert get_default_model() == "gpt-4o"
        
    def test_get_model_parameters(self):
        """Test get_model_parameters."""
        # Test with environment variables
        os.environ["AGENT_TEMPERATURE"] = "0.5"
        os.environ["AGENT_API_TIMEOUT"] = "30"
        
        params = get_model_parameters()
        assert params["temperature"] == 0.5
        assert params["timeout"] == 30
        
        # Test defaults
        del os.environ["AGENT_TEMPERATURE"]
        del os.environ["AGENT_API_TIMEOUT"]
        
        params = get_model_parameters()
        assert params["temperature"] == 0.7
        assert params["timeout"] == 60
