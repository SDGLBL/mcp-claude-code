"""Test batch tool functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Context as MCPContext

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.batch_tool import BatchTool


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(self, name, result="mock result"):
        self._name = name
        self._result = result
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Mock {self._name} tool"

    @property
    def parameters(self) -> dict:
        return {
            "properties": {"param1": {"type": "string"}, "param2": {"type": "integer"}},
            "required": ["param1"],
            "type": "object",
        }

    @property
    def required(self) -> list[str]:
        return ["param1"]

    async def call(self, ctx, **params):
        self.call_count += 1
        return f"{self._result}: {params}"

    def register(self, mcp_server):
        pass


class FailingMockTool(MockTool):
    """Mock tool that fails when called."""

    async def call(self, ctx, **params):
        self.call_count += 1
        raise ValueError("Mock error")


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=MCPContext)
    context.info = AsyncMock()
    context.error = AsyncMock()
    context.warning = AsyncMock()
    return context


@pytest.fixture
def tools_dict():
    """Create a dictionary of mock tools."""
    return {
        "tool1": MockTool("tool1", "tool1 result"),
        "tool2": MockTool("tool2", "tool2 result"),
        "failing_tool": FailingMockTool("failing_tool"),
    }


@pytest.fixture
def batch_tool(tools_dict):
    """Create a BatchTool instance with mock tools."""
    return BatchTool(tools_dict)


@pytest.mark.asyncio
async def test_batch_tool_execution(mock_context, batch_tool):
    """Test that batch tool executes all tools correctly."""
    # Define batch parameters
    params = {
        "description": "Test batch",
        "invocations": [
            {"tool_name": "tool1", "input": {"param1": "value1", "param2": 42}},
            {"tool_name": "tool2", "input": {"param1": "value2"}},
        ],
    }

    # Execute batch tool
    result = await batch_tool.call(mock_context, **params)

    # Check that all tools were called
    assert batch_tool.tools["tool1"].call_count == 1
    assert batch_tool.tools["tool2"].call_count == 1

    # Check that the result contains outputs from both tools
    assert "tool1 result" in result
    assert "tool2 result" in result
    assert "value1" in result
    assert "value2" in result


@pytest.mark.asyncio
async def test_batch_tool_with_missing_tool(mock_context, batch_tool):
    """Test batch tool with a non-existent tool."""
    params = {
        "description": "Test batch with missing tool",
        "invocations": [
            {"tool_name": "nonexistent_tool", "input": {"param1": "value1"}}
        ],
    }

    # Execute batch tool
    result = await batch_tool.call(mock_context, **params)

    # Check that the error message is in the result
    assert "Tool 'nonexistent_tool' not found" in result

    # Check that the error was logged
    mock_context.error.assert_called_once()


@pytest.mark.asyncio
async def test_batch_tool_with_failing_tool(mock_context, batch_tool):
    """Test batch tool with a tool that fails."""
    params = {
        "description": "Test batch with failing tool",
        "invocations": [
            {"tool_name": "tool1", "input": {"param1": "value1"}},
            {"tool_name": "failing_tool", "input": {"param1": "value2"}},
        ],
    }

    # Execute batch tool
    result = await batch_tool.call(mock_context, **params)

    # Check that both tools were called
    assert batch_tool.tools["tool1"].call_count == 1
    assert batch_tool.tools["failing_tool"].call_count == 1

    # Check that the successful tool's result is in the output
    assert "tool1 result" in result

    # Check that the error message is in the result
    assert "Error executing tool 'failing_tool'" in result
    assert "Mock error" in result


@pytest.mark.asyncio
async def test_batch_tool_with_invalid_params(mock_context, batch_tool):
    """Test batch tool with invalid parameters."""
    # Test with missing description
    params1 = {"invocations": [{"tool_name": "tool1", "input": {"param1": "value1"}}]}

    result1 = await batch_tool.call(mock_context, **params1)
    assert "Parameter 'description' is required" in result1

    # Test with missing invocations
    params2 = {"description": "Test batch"}

    result2 = await batch_tool.call(mock_context, **params2)
    assert "Parameter 'invocations' is required" in result2

    # Test with empty invocations list
    params3 = {"description": "Test batch", "invocations": []}

    result3 = await batch_tool.call(mock_context, **params3)
    assert "Parameter 'invocations'" in result3 and "empty" in result3
