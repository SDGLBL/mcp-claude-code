"""Tests for the context module."""

from unittest.mock import MagicMock

import pytest

from mcp_claude_code.tools.common.context import (
    ToolContext,
    create_tool_context,
)


class TestToolContext:
    """Test the ToolContext class."""

    def test_initialization(self, mcp_context: MagicMock):
        """Test initializing a ToolContext."""
        tool_context = ToolContext(mcp_context)

        assert tool_context.mcp_context == mcp_context
        assert tool_context.request_id == mcp_context.request_id
        assert tool_context.client_id == mcp_context.client_id

    def test_set_tool_info(self, mcp_context: MagicMock):
        """Test setting tool info."""
        tool_context = ToolContext(mcp_context)
        tool_name = "test_tool"
        execution_id = "123456"

        tool_context.set_tool_info(tool_name, execution_id)

        # Test internal state
        assert tool_context._tool_name == tool_name
        assert tool_context._execution_id == execution_id

    @pytest.mark.asyncio
    async def test_logging_methods(self, mcp_context: MagicMock):
        """Test logging methods."""
        tool_context = ToolContext(mcp_context)
        tool_context.set_tool_info("test_tool")

        # Test info logging
        await tool_context.info("Test info")
        mcp_context.info.assert_called_once_with("[test_tool] Test info")

        # Test debug logging
        await tool_context.debug("Test debug")
        mcp_context.debug.assert_called_once_with("[test_tool] Test debug")

        # Test warning logging
        await tool_context.warning("Test warning")
        mcp_context.warning.assert_called_once_with("[test_tool] Test warning")

        # Test error logging
        await tool_context.error("Test error")
        mcp_context.error.assert_called_once_with("[test_tool] Test error")

    def test_format_message(self, mcp_context: MagicMock):
        """Test message formatting."""
        tool_context = ToolContext(mcp_context)

        # No tool info
        message = tool_context._format_message("Test message")
        assert message == "Test message"

        # With tool name
        tool_context.set_tool_info("test_tool")
        message = tool_context._format_message("Test message")
        assert message == "[test_tool] Test message"

        # With tool name and execution id
        tool_context.set_tool_info("test_tool", "123456")
        message = tool_context._format_message("Test message")
        assert message == "[test_tool:123456] Test message"

    @pytest.mark.asyncio
    async def test_report_progress(self, mcp_context: MagicMock):
        """Test progress reporting."""
        tool_context = ToolContext(mcp_context)

        await tool_context.report_progress(50, 100)
        mcp_context.report_progress.assert_called_once_with(50, 100)

    @pytest.mark.asyncio
    async def test_read_resource(self, mcp_context: MagicMock):
        """Test reading a resource."""
        tool_context = ToolContext(mcp_context)

        await tool_context.read_resource("resource://test")
        mcp_context.read_resource.assert_called_once_with("resource://test")


def test_create_tool_context(mcp_context: MagicMock):
    """Test creating a tool context."""
    tool_context = create_tool_context(mcp_context)

    assert isinstance(tool_context, ToolContext)
    assert tool_context.mcp_context == mcp_context
