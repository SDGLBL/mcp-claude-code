"""Tests for the agent tool implementation."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_claude_code.tools.agent.agent_tool import AgentTool
from mcp_claude_code.tools.common.base import BaseTool

from mcp_claude_code.tools.common.permissions import PermissionManager


class TestAgentTool:
    """Test cases for the AgentTool."""

    @pytest.fixture
    def permission_manager(self):
        """Create a test permission manager."""
        return MagicMock(spec=PermissionManager)

    @pytest.fixture
    def mcp_context(self):
        """Create a test MCP context."""
        return MagicMock()

    @pytest.fixture
    def agent_tool(self, permission_manager):
        """Create a test agent tool."""
        with patch("mcp_claude_code.tools.agent.agent_tool.litellm"):
            # Set environment variable for test
            os.environ["OPENAI_API_KEY"] = "test_key"
            return AgentTool(permission_manager)

    @pytest.fixture
    def agent_tool_with_params(self, permission_manager):
        """Create a test agent tool with custom parameters."""
        with patch("mcp_claude_code.tools.agent.agent_tool.litellm"):
            return AgentTool(
                permission_manager=permission_manager,
                model="anthropic/claude-3-sonnet",
                api_key="test_anthropic_key",
                max_tokens=2000,
                max_iterations=40,
                max_tool_uses=150,
            )

    @pytest.fixture
    def mock_tools(self):
        """Create a list of mock tools."""
        tools = []
        for name in ["read", "search_content", "directory_tree"]:
            tool = MagicMock(spec=BaseTool)
            tool.name = name
            tool.description = f"Description for {name}"
            tool.parameters = {"properties": {}, "type": "object"}
            tool.required = []
            tools.append(tool)
        return tools

    def test_initialization(self, agent_tool):
        """Test agent tool initialization."""
        assert agent_tool.name == "dispatch_agent"
        assert "Launch a new agent" in agent_tool.description
        assert agent_tool.model_override is None
        assert agent_tool.api_key_override is None
        assert agent_tool.max_tokens_override is None
        assert agent_tool.max_iterations == 10
        assert agent_tool.max_tool_uses == 30

    def test_initialization_with_params(self, agent_tool_with_params):
        """Test agent tool initialization with custom parameters."""
        assert agent_tool_with_params.name == "dispatch_agent"
        assert agent_tool_with_params.model_override == "anthropic/claude-3-sonnet"
        assert agent_tool_with_params.api_key_override == "test_anthropic_key"
        assert agent_tool_with_params.max_tokens_override == 2000
        assert agent_tool_with_params.max_iterations == 40
        assert agent_tool_with_params.max_tool_uses == 150

    def test_model_and_api_key_override(self, permission_manager):
        """Test API key and model override functionality."""
        # Test with antropic model and API key
        agent_tool = AgentTool(
            permission_manager=permission_manager,
            model="anthropic/claude-3-sonnet",
            api_key="test_anthropic_key",
        )

        assert agent_tool.model_override == "anthropic/claude-3-sonnet"
        assert agent_tool.api_key_override == "test_anthropic_key"

        # Test with openai model and API key
        agent_tool = AgentTool(
            permission_manager=permission_manager,
            model="openai/gpt-4o",
            api_key="test_openai_key",
        )

        assert agent_tool.model_override == "openai/gpt-4o"
        assert agent_tool.api_key_override == "test_openai_key"

        # Test with no model or API key
        agent_tool = AgentTool(
            permission_manager=permission_manager,
        )

        assert agent_tool.model_override is None
        assert agent_tool.api_key_override is None

    @pytest.mark.asyncio
    async def test_call_with_litellm_error(self, agent_tool, mcp_context):
        """Test agent tool call when litellm raises an error."""
        # Mock the tool context
        tool_ctx = MagicMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.get_tools = AsyncMock(return_value=[])

        # Mock litellm to raise an error
        with patch(
            "mcp_claude_code.tools.agent.agent_tool.create_tool_context",
            return_value=tool_ctx,
        ):
            with patch(
                "mcp_claude_code.tools.agent.agent_tool.litellm.completion",
                side_effect=RuntimeError("API key error"),
            ):
                with patch(
                    "mcp_claude_code.tools.agent.agent_tool.get_allowed_agent_tools",
                    return_value=[],
                ):
                    with patch(
                        "mcp_claude_code.tools.agent.agent_tool.convert_tools_to_openai_functions",
                        return_value=[],
                    ):
                        with patch(
                            "mcp_claude_code.tools.agent.agent_tool.get_system_prompt",
                            return_value="System prompt",
                        ):
                            result = await agent_tool.call(
                                ctx=mcp_context, prompt="Test prompt"
                            )

        # We're just making sure an error is returned, the actual error message may vary in tests
        assert "Error" in result
        tool_ctx.error.assert_called()

    @pytest.mark.asyncio
    async def test_call_with_valid_prompt(self, agent_tool, mcp_context, mock_tools):
        """Test agent tool call with valid prompt string."""
        # Mock the tool context
        tool_ctx = MagicMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.mcp_context = mcp_context

        # Mock the _execute_agent method
        with patch.object(
            agent_tool, "_execute_agent", AsyncMock(return_value="Agent result")
        ):
            with patch(
                "mcp_claude_code.tools.agent.agent_tool.create_tool_context",
                return_value=tool_ctx,
            ):
                result = await agent_tool.call(
                    ctx=mcp_context,
                    prompt="Test prompt with absolute path /Users/bytedance/project/",
                )

        assert "Agent execution completed" in result
        assert "Agent result" in result
        tool_ctx.info.assert_called()

    @pytest.mark.asyncio
    async def test_call_with_no_absolute_path(self, agent_tool, mcp_context):
        """Test agent tool call with a prompt missing an absolute path."""
        # Mock the tool context
        tool_ctx = MagicMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.error = AsyncMock()

        with patch(
            "mcp_claude_code.tools.agent.agent_tool.create_tool_context",
            return_value=tool_ctx,
        ):
            # Test with a prompt without an absolute path
            result = await agent_tool.call(
                ctx=mcp_context, prompt="Search for all config files"
            )

        assert "Error" in result
        assert "must contain at least one absolute path" in result
        tool_ctx.error.assert_called_with(
            "The prompt does not contain an absolute path"
        )

    @pytest.mark.asyncio
    async def test_call_with_absolute_path(self, agent_tool, mcp_context, mock_tools):
        """Test agent tool call with a prompt containing an absolute path."""
        # Mock the tool context
        tool_ctx = MagicMock()
        tool_ctx.set_tool_info = AsyncMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.mcp_context = mcp_context

        # Mock the _execute_agent method to avoid actually calling it
        with patch.object(
            agent_tool, "_execute_agent", AsyncMock(return_value="Agent result")
        ):
            with patch(
                "mcp_claude_code.tools.agent.agent_tool.create_tool_context",
                return_value=tool_ctx,
            ):
                # Test with a prompt containing an absolute path
                result = await agent_tool.call(
                    ctx=mcp_context,
                    prompt="Search for all config files in /Users/bytedance/project/mcp-claude-code",
                )

        assert "Agent execution completed" in result
        assert "Agent result" in result
        tool_ctx.info.assert_called()

    @pytest.mark.asyncio
    async def test_execute_agent_with_tools_simple(
        self, agent_tool, mcp_context, mock_tools
    ):
        """Test _execute_agent_with_tools with a simple response."""
        # Mock the tool context
        tool_ctx = MagicMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.mcp_context = mcp_context

        # Mock the OpenAI response
        mock_message = MagicMock()
        mock_message.content = "Simple result"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # Set test mode and mock litellm
        os.environ["TEST_MODE"] = "1"
        with patch(
            "mcp_claude_code.tools.agent.agent_tool.litellm.completion",
            return_value=mock_response,
        ):
            # Execute the method
            result = await agent_tool._execute_agent_with_tools(
                "System prompt",
                "User prompt",
                mock_tools,
                [],  # openai_tools
                tool_ctx,
            )

        assert result == "Simple result"

    @pytest.mark.asyncio
    async def test_execute_agent_with_tools_tool_calls(
        self, agent_tool, mcp_context, mock_tools
    ):
        """Test _execute_agent_with_tools with tool calls."""
        # Mock the tool context
        tool_ctx = MagicMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.mcp_context = mcp_context

        # Set up one of the mock tools
        mock_tool = mock_tools[0]
        mock_tool.call = AsyncMock(return_value="Tool result")

        # Create a tool call
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function = MagicMock()
        mock_tool_call.function.name = mock_tool.name
        mock_tool_call.function.arguments = json.dumps({"param": "value"})

        # First response with tool call
        first_message = MagicMock()
        first_message.content = None
        first_message.tool_calls = [mock_tool_call]

        first_choice = MagicMock()
        first_choice.message = first_message

        first_response = MagicMock()
        first_response.choices = [first_choice]

        # Second response with final result
        second_message = MagicMock()
        second_message.content = "Final result"
        second_message.tool_calls = None

        second_choice = MagicMock()
        second_choice.message = second_message

        second_response = MagicMock()
        second_response.choices = [second_choice]

        # Set test mode and mock litellm
        os.environ["TEST_MODE"] = "1"
        with patch(
            "mcp_claude_code.tools.agent.agent_tool.litellm.completion",
            side_effect=[first_response, second_response],
        ):
            # Mock any complex dictionary or string processing by directly using the expected values in the test
            with patch.object(json, "loads", return_value={"param": "value"}):
                result = await agent_tool._execute_agent_with_tools(
                    "System prompt",
                    "User prompt",
                    mock_tools,
                    [
                        {"type": "function", "function": {"name": mock_tool.name}}
                    ],  # openai_tools
                    tool_ctx,
                )

        assert result == "Final result"
        mock_tool.call.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_agent(self, agent_tool, mcp_context, mock_tools):
        """Test the _execute_agent method."""
        # Mock the tool context
        tool_ctx = MagicMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.mcp_context = mcp_context

        # Create test prompt
        test_prompt = "Task 1"

        # Mock the necessary dependencies
        with patch(
            "mcp_claude_code.tools.agent.agent_tool.get_allowed_agent_tools",
            return_value=mock_tools,
        ):
            with patch(
                "mcp_claude_code.tools.agent.agent_tool.get_system_prompt",
                return_value="System prompt",
            ):
                with patch(
                    "mcp_claude_code.tools.agent.agent_tool.convert_tools_to_openai_functions",
                    return_value=[],
                ):
                    with patch.object(
                        agent_tool,
                        "_execute_agent_with_tools",
                        AsyncMock(return_value="Result 1"),
                    ):
                        result = await agent_tool._execute_agent(test_prompt, tool_ctx)

        # Check the result
        assert result == "Result 1"

    @pytest.mark.asyncio
    async def test_execute_agent_with_exception(
        self, agent_tool, mcp_context, mock_tools
    ):
        """Test the _execute_agent method with an exception."""
        # Mock the tool context
        tool_ctx = MagicMock()
        tool_ctx.info = AsyncMock()
        tool_ctx.error = AsyncMock()
        tool_ctx.mcp_context = mcp_context

        # Create test prompt
        test_prompt = "Task that fails"

        # Mock the necessary dependencies
        with patch(
            "mcp_claude_code.tools.agent.agent_tool.get_allowed_agent_tools",
            return_value=mock_tools,
        ):
            with patch(
                "mcp_claude_code.tools.agent.agent_tool.get_system_prompt",
                return_value="System prompt",
            ):
                with patch(
                    "mcp_claude_code.tools.agent.agent_tool.convert_tools_to_openai_functions",
                    return_value=[],
                ):
                    with patch.object(
                        agent_tool,
                        "_execute_agent_with_tools",
                        side_effect=Exception("Task failed"),
                    ):
                        result = await agent_tool._execute_agent(test_prompt, tool_ctx)

        # Check the result format
        assert "Error" in result
        assert "Task failed" in result
