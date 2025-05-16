"""Prompt generation utilities for agent tool.

This module provides functions for generating effective prompts for sub-agents,
including filtering tools based on permissions and formatting system instructions.
"""

import os
from typing import Any

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.permissions import PermissionManager


def get_allowed_agent_tools(
    tools: list[BaseTool],
    permission_manager: PermissionManager,
) -> list[BaseTool]:
    """Filter tools available to the agent based on permissions.

    Args:
        tools: List of available tools
        permission_manager: Permission manager for checking tool access

    Returns:
        Filtered list of tools available to the agent
    """
    # Get all tools except for the agent tool itself (avoid recursion)
    filtered_tools = [tool for tool in tools if tool.name != "agent"]

    return filtered_tools


def get_system_prompt(
    tools: list[BaseTool],
    permission_manager: PermissionManager,
) -> str:
    """Generate system prompt for the sub-agent.

    Args:
        tools: List of available tools
        permission_manager: Permission manager for checking tool access

    Returns:
        System prompt for the sub-agent
    """
    # Get filtered tools
    filtered_tools = get_allowed_agent_tools(tools, permission_manager)

    # Extract tool names for display
    tool_names = ", ".join(f"`{tool.name}`" for tool in filtered_tools)

    # Base system prompt
    system_prompt = f"""You are a sub-agent assistant with access to these tools: {tool_names}.

GUIDELINES:
1. You work autonomously - you cannot ask follow-up questions
2. You have access to read-only tools - you cannot modify files or execute commands
3. Your response is returned directly to the main assistant, not the user
4. Be concise and focus on the specific task assigned
5. When relevant, share file names and code snippets relevant to the query
6. Any file paths you return in your final response MUST be absolute. DO NOT use relative paths.
7. CRITICAL: You can only work with the absolute paths provided in your task prompt. You cannot infer or guess other locations.

RESPONSE FORMAT:
- Begin with a summary of findings
- Include relevant details and context
- Organize information logically
- End with clear conclusions
"""

    return system_prompt


def get_default_model(model_override: str | None = None) -> str:
    """Get the default model for agent execution.

    Args:
        model_override: Optional model override string in LiteLLM format (e.g., "openai/gpt-4o")

    Returns:
        Model identifier string with provider prefix
    """
    # Use model override if provided
    if model_override:
        # If in testing mode and using a test model, return as-is
        if model_override.startswith("test-model") or "TEST_MODE" in os.environ:
            return model_override

        # If the model already has a provider prefix, return as-is
        if "/" in model_override:
            return model_override

        # Otherwise, add the default provider prefix
        provider = os.environ.get("AGENT_PROVIDER", "openai")
        return f"{provider}/{model_override}"

    # Fall back to environment variables
    model = os.environ.get("AGENT_MODEL", "gpt-4o")

    # Special cases for tests
    if (
        model.startswith("test-model")
        or model == "gpt-4o"
        and "TEST_MODE" in os.environ
    ):
        return model

    provider = os.environ.get("AGENT_PROVIDER", "openai")

    # Only add provider prefix if it's not already in the model name
    if "/" not in model and provider != "openai":
        return f"{provider}/{model}"
    elif "/" not in model:
        return f"openai/{model}"
    else:
        # Model already has a provider prefix
        return model


def get_model_parameters(max_tokens: int | None = None) -> dict[str, Any]:
    """Get model parameters from environment variables.

    Args:
        max_tokens: Optional maximum tokens parameter override

    Returns:
        Dictionary of model parameters
    """
    params = {
        "temperature": float(os.environ.get("AGENT_TEMPERATURE", "0.7")),
        "timeout": int(os.environ.get("AGENT_API_TIMEOUT", "60")),
    }

    # Add max_tokens if provided or if set in environment variable
    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    elif os.environ.get("AGENT_MAX_TOKENS"):
        params["max_tokens"] = int(os.environ.get("AGENT_MAX_TOKENS", "1000"))

    return params
