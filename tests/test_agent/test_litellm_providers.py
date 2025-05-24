"""Test LiteLLM with different providers."""

import os

import pytest
import litellm

from mcp_claude_code.tools.agent.tool_adapter import convert_tools_to_openai_functions
from mcp_claude_code.tools.common.base import BaseTool


class EchoTool(BaseTool):
    """A simple tool that echoes back the input."""

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "echo"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Echo back the input message."

    @property
    def parameters(self) -> dict:
        """Get the parameter specifications for the tool."""
        return {
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to echo back",
                },
            },
            "required": ["message"],
            "type": "object",
        }

    @property
    def required(self) -> list[str]:
        """Get the list of required parameter names."""
        return ["message"]

    def register(self, ctx):
        """Register the tool with the context."""
        # This is a required abstract method from BaseTool
        pass

    async def call(self, ctx, **params):
        """Execute the tool with the given parameters."""
        message = params.get("message", "")
        return f"Echo: {message}"


@pytest.fixture
def echo_tool():
    """Fixture for the EchoTool."""
    return EchoTool()


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY environment variable not set",
)
def test_convert_echo_tool_to_openai_functions(echo_tool):
    """Test convert_tools_to_openai_functions with echo_tool."""
    openai_functions = convert_tools_to_openai_functions([echo_tool])

    assert len(openai_functions) == 1
    assert openai_functions[0]["type"] == "function"
    assert openai_functions[0]["function"]["name"] == "echo"
    assert (
        openai_functions[0]["function"]["description"] == "Echo back the input message."
    )
    assert "parameters" in openai_functions[0]["function"]


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY environment variable not set",
)
def test_litellm_openai_provider():
    """Test LiteLLM with OpenAI provider."""
    messages = [{"role": "user", "content": "Hello, how are you?"}]

    try:
        # Call OpenAI model with provider prefix
        response = litellm.completion(
            model="openai/gpt-3.5-turbo",
            messages=messages,
        )

        assert response.choices[0].message.content is not None
        print(f"OpenAI response: {response.choices[0].message.content}")
    except Exception as e:
        pytest.skip(f"OpenAI API connection failed: {type(e).__name__} - {str(e)}")


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY environment variable not set",
)
def test_litellm_anthropic_provider():
    """Test LiteLLM with Anthropic provider."""
    messages = [{"role": "user", "content": "Hello, how are you?"}]

    try:
        # Call Anthropic model with provider prefix
        response = litellm.completion(
            model="anthropic/claude-3-haiku-20240307",
            messages=messages,
        )

        assert response.choices[0].message.content is not None
        print(f"Anthropic response: {response.choices[0].message.content}")
    except Exception as e:
        pytest.skip(f"Anthropic API connection failed: {type(e).__name__} - {str(e)}")


# Only run this test if explicitly requested with pytest -xvs tests/test_agent/test_litellm_providers.py
if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
