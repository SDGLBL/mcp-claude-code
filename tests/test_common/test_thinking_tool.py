"""Tests for the refactored ThinkingTool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_claude_code.tools.common.thinking_tool import ThinkingTool


class TestThinkingTool:
    """Test the refactored ThinkingTool."""

    @pytest.fixture
    def thinking_tool(self):
        """Create a ThinkingTool instance for testing."""
        return ThinkingTool()

    def test_initialization(self, thinking_tool: ThinkingTool):
        """Test initializing ThinkingTool."""
        assert thinking_tool.name == "think"
        assert "Use the tool to think about something" in thinking_tool.description

    @pytest.mark.asyncio
    async def test_valid_thought(
        self, thinking_tool: ThinkingTool, mcp_context: MagicMock
    ):
        """Test the thinking tool with a valid thought."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.common.thinking_tool.create_tool_context",
            return_value=tool_ctx,
        ):
            # Call the tool directly
            thought = "This is a test thought process"
            result = await thinking_tool.call(ctx=mcp_context, thought=thought)

            # Verify result
            assert "I've recorded your thinking process" in result
            tool_ctx.info.assert_called_with("Thinking process recorded")

    @pytest.mark.asyncio
    async def test_empty_thought(
        self, thinking_tool: ThinkingTool, mcp_context: MagicMock
    ):
        """Test the thinking tool with an empty thought."""
        # Mock context calls
        tool_ctx = AsyncMock()
        with patch(
            "mcp_claude_code.tools.common.thinking_tool.create_tool_context",
            return_value=tool_ctx,
        ):
            # Call the tool with an empty thought
            result = await thinking_tool.call(ctx=mcp_context, thought="")

            # Verify result
            assert (
                "Error: Parameter 'thought' is required but was None or empty" in result
            )
            tool_ctx.error.assert_called()
