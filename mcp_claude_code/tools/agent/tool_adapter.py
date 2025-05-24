"""Tool adapters for converting between MCP tools and OpenAI tools.

This module handles conversion between MCP tool formats and OpenAI function
formats, making MCP tools available to the OpenAI API, and processing tool inputs
and outputs for agent execution.
"""

from openai.types import FunctionParameters
from openai.types.chat import ChatCompletionToolParam
import litellm

from mcp_claude_code.tools.common.base import BaseTool


def convert_tools_to_openai_functions(
    tools: list[BaseTool],
) -> list[ChatCompletionToolParam]:
    """Convert MCP tools to OpenAI function format.

    Args:
        tools: List of MCP tools

    Returns:
        List of tools formatted for OpenAI API
    """
    openai_tools: list[ChatCompletionToolParam] = []
    for tool in tools:
        openai_tool: ChatCompletionToolParam = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": convert_tool_parameters(tool),
            },
        }
        openai_tools.append(openai_tool)
    return openai_tools


def convert_tool_parameters(tool: BaseTool) -> FunctionParameters:
    """Convert tool parameters to OpenAI format.

    Args:
        tool: MCP tool

    Returns:
        Parameter schema in OpenAI format
    """
    # Start with a copy of the parameters
    params = tool.parameters.copy()

    # Ensure the schema has the right format for OpenAI
    if "properties" not in params:
        params["properties"] = {}

    if "type" not in params:
        params["type"] = "object"

    if "required" not in params:
        params["required"] = tool.required

    return params


def supports_parallel_function_calling(model: str) -> bool:
    """Check if a model supports parallel function calling.

    Args:
        model: Model identifier in LiteLLM format (e.g., "openai/gpt-4-turbo-preview")

    Returns:
        True if the model supports parallel function calling, False otherwise
    """
    # Use litellm's built-in parallel function calling support check
    return litellm.supports_parallel_function_calling(model=model)
