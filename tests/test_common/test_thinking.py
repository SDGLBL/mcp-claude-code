"""Tests for the thinking tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_claude_code.tools.common.thinking_tool import ThinkingTool
from mcp_claude_code.tools.common.base import ToolRegistry


@pytest.fixture
def mcp_server():
    """Create a mock MCP server."""
    server = MagicMock()
    server.tool = MagicMock(return_value=lambda func: func)
    return server


@pytest.fixture
def thinking_tool():
    """Create a ThinkingTool instance."""
    return ThinkingTool()


@pytest.mark.asyncio
async def test_think_tool_registration(mcp_server, thinking_tool):
    """Test that the think tool is registered correctly."""
    # Test registration using ToolRegistry
    ToolRegistry.register_tool(mcp_server, thinking_tool)
    # Check if tool was registered
    assert mcp_server.tool.called


@pytest.mark.asyncio
async def test_think_with_valid_thought(thinking_tool, mcp_context):
    """Test the think tool with a valid thought."""
    # Mock context calls
    tool_ctx = MagicMock()
    tool_ctx.info = AsyncMock()
    tool_ctx.error = AsyncMock()
    tool_ctx.set_tool_info = AsyncMock()  # Make sure this is AsyncMock
    tool_ctx.prepare_tool_context = AsyncMock()

    # Patch the create_tool_context function
    with patch(
        "mcp_claude_code.tools.common.thinking_tool.create_tool_context",
        return_value=tool_ctx,
    ):
        # Test the tool's call method directly
        thought = "I should check if the file exists before trying to read it."
        result = await thinking_tool.call(ctx=mcp_context, thought=thought)

        # Check that the function behaved correctly
        tool_ctx.set_tool_info.assert_called_once_with("think")
        tool_ctx.info.assert_called_once_with("Thinking process recorded")
        assert "I've recorded your thinking process" in result


@pytest.mark.asyncio
async def test_think_with_empty_thought(thinking_tool, mcp_context):
    """Test the think tool with an empty thought."""
    # Mock context calls
    tool_ctx = MagicMock()
    tool_ctx.info = AsyncMock()
    tool_ctx.error = AsyncMock()
    tool_ctx.set_tool_info = AsyncMock()  # Make sure this is AsyncMock
    tool_ctx.prepare_tool_context = AsyncMock()

    # Patch the create_tool_context function
    with patch(
        "mcp_claude_code.tools.common.thinking_tool.create_tool_context",
        return_value=tool_ctx,
    ):
        # Test with None thought
        result_none = await thinking_tool.call(ctx=mcp_context, thought=None)
        assert "Error" in result_none

        # Test with empty string thought
        result_empty = await thinking_tool.call(ctx=mcp_context, thought="")
        assert "Error" in result_empty

        # Test with whitespace-only thought
        result_whitespace = await thinking_tool.call(ctx=mcp_context, thought="   ")
        assert "Error" in result_whitespace
