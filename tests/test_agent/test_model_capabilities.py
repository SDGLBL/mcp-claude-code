"""Tests for model capability checking functions."""

from unittest.mock import patch

from mcp_claude_code.tools.agent.tool_adapter import (
    supports_parallel_function_calling,
)


class TestModelCapabilities:
    """Tests for model capability checking functions."""

    @patch("litellm.supports_parallel_function_calling")
    def test_supports_parallel_function_calling(self, mock_litellm_supports_parallel):
        """Test that supports_parallel_function_calling properly calls litellm."""
        # Set up the mock
        mock_litellm_supports_parallel.return_value = True

        # Test with a model that supports parallel function calling
        assert supports_parallel_function_calling("gpt-4-turbo-preview") is True
        mock_litellm_supports_parallel.assert_called_with(model="gpt-4-turbo-preview")

        # Test with a provider-prefixed model
        mock_litellm_supports_parallel.reset_mock()
        mock_litellm_supports_parallel.return_value = True
        assert supports_parallel_function_calling("openai/gpt-4-turbo-preview") is True
        mock_litellm_supports_parallel.assert_called_with(
            model="openai/gpt-4-turbo-preview"
        )

        # Test with a model that doesn't support parallel function calling
        mock_litellm_supports_parallel.reset_mock()
        mock_litellm_supports_parallel.return_value = False
        assert supports_parallel_function_calling("gpt-4") is False
        mock_litellm_supports_parallel.assert_called_with(model="gpt-4")
