"""Tests for the agent tool adapter module."""

from unittest.mock import MagicMock

import pytest

from mcp_claude_code.tools.agent.tool_adapter import (
    convert_tool_parameters,
    convert_tools_to_openai_functions,
)
from mcp_claude_code.tools.common.base import BaseTool


class TestToolAdapter:
    """Test cases for the agent tool adapter module."""

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool."""
        tool = MagicMock(spec=BaseTool)
        tool.name = "read"
        tool.description = "Read files from the file system"
        tool.parameters = {
            "properties": {
                "file_path": {
                    "anyOf": [
                        {"items": {"type": "string"}, "type": "array"},
                        {"type": "string"},
                    ],
                    "title": "File Path",
                },
            },
            "required": ["file_path"],
            "title": "readArguments",
            "type": "object",
        }
        tool.required = ["file_path"]
        return tool

    @pytest.fixture
    def mock_simple_tool(self):
        """Create a mock tool with minimal parameters."""
        tool = MagicMock(spec=BaseTool)
        tool.name = "think"
        tool.description = "Think about something"
        tool.parameters = {
            "properties": {
                "thought": {
                    "title": "Thought",
                    "type": "string",
                },
            },
        }
        tool.required = ["thought"]
        return tool

    def test_convert_tools_to_openai_functions(self, mock_tool, mock_simple_tool):
        """Test convert_tools_to_openai_functions."""
        # Convert tools
        openai_functions = convert_tools_to_openai_functions(
            [mock_tool, mock_simple_tool]
        )

        # Verify result
        assert len(openai_functions) == 2

        # Check first tool
        assert openai_functions[0]["type"] == "function"
        assert openai_functions[0]["function"]["name"] == "read"
        assert (
            openai_functions[0]["function"]["description"]
            == "Read files from the file system"
        )
        assert "parameters" in openai_functions[0]["function"]

        # Check second tool
        assert openai_functions[1]["type"] == "function"
        assert openai_functions[1]["function"]["name"] == "think"
        assert openai_functions[1]["function"]["description"] == "Think about something"
        assert "parameters" in openai_functions[1]["function"]

    def test_convert_tool_parameters_complete(self, mock_tool):
        """Test convert_tool_parameters with complete parameters."""
        # Convert parameters
        params = convert_tool_parameters(mock_tool)

        # Verify result
        assert params["type"] == "object"
        assert "properties" in params
        assert "file_path" in params["properties"]
        assert params["required"] == ["file_path"]

    def test_convert_tool_parameters_minimal(self, mock_simple_tool):
        """Test convert_tool_parameters with minimal parameters."""
        # Convert parameters
        params = convert_tool_parameters(mock_simple_tool)

        # Verify result
        assert params["type"] == "object"
        assert "properties" in params
        assert "thought" in params["properties"]
        assert params["required"] == ["thought"]
