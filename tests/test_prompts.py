"""Tests for the prompts module to prevent regressions in project system prompt functionality."""

import os
import tempfile
from unittest.mock import Mock, patch

from mcp_claude_code.prompts import register_all_prompts


class TestProjectSystemPrompts:
    """Test the project system prompt functionality to prevent closure bugs."""

    def test_register_multiple_projects_unique_prompts(self):
        """Test that each project gets its own unique system prompt function.

        This test specifically checks for the closure bug where all project
        system prompts would use the last project path from the loop.
        """
        # Create mock server
        mock_server = Mock()
        registered_prompts = {}

        def mock_prompt(name: str, description: str = None):
            """Mock the @mcp_server.prompt decorator"""

            def decorator(func):
                registered_prompts[name] = func
                return func

            return decorator

        mock_server.prompt = mock_prompt

        # Create temporary test directories
        with tempfile.TemporaryDirectory() as temp_dir:
            project1_path = os.path.join(temp_dir, "project1")
            project2_path = os.path.join(temp_dir, "project2")
            project3_path = os.path.join(temp_dir, "claude-code-provider-proxy")

            os.makedirs(project1_path)
            os.makedirs(project2_path)
            os.makedirs(project3_path)

            # Initialize git repos for better test coverage
            for project_path in [project1_path, project2_path, project3_path]:
                git_dir = os.path.join(project_path, ".git")
                os.makedirs(git_dir)

            projects = [project1_path, project2_path, project3_path]

            # Mock the utility functions
            with (
                patch("mcp_claude_code.prompts.get_os_info") as mock_os_info,
                patch(
                    "mcp_claude_code.prompts.get_directory_structure"
                ) as mock_dir_struct,
                patch("mcp_claude_code.prompts.get_git_info") as mock_git_info,
                patch("mcp_claude_code.prompts.PROJECT_SYSTEM_PROMPT") as mock_template,
            ):
                mock_os_info.return_value = ("Darwin", "", "24.5.0")
                mock_dir_struct.return_value = "test-directory-structure"
                mock_git_info.return_value = {
                    "current_branch": "main",
                    "main_branch": "main",
                    "git_status": "clean",
                    "recent_commits": "test-commits",
                }
                mock_template.format.return_value = (
                    "formatted-prompt-{working_directory}"
                )

                # Register all prompts
                register_all_prompts(mock_server, projects)

                # Verify that prompts were registered for each project
                expected_prompt_names = [
                    "System prompt for project1",
                    "System prompt for project2",
                    "System prompt for claude-code-provider-proxy",
                ]

                for name in expected_prompt_names:
                    assert name in registered_prompts, f"Missing prompt: {name}"

                # This is the critical test - each prompt function should use its own project path
                prompt_results = {}
                for name, prompt_func in registered_prompts.items():
                    if name.startswith("System prompt for"):
                        prompt_results[name] = prompt_func()

                # Verify that PROJECT_SYSTEM_PROMPT.format was called with correct working_directory
                # for each project (3 times total)
                assert mock_template.format.call_count == 3

                # Check that each call used a different working_directory
                call_args_list = mock_template.format.call_args_list
                working_directories = []
                for call in call_args_list:
                    kwargs = call[1]  # Get keyword arguments
                    working_directories.append(kwargs["working_directory"])

                # All three projects should have been used
                assert set(working_directories) == set(projects)

                # Verify no project path was used more than once
                assert len(working_directories) == len(set(working_directories))

                # Specifically check that not all prompts use the last project
                # (this was the bug we're fixing)
                last_project = projects[-1]  # claude-code-provider-proxy
                assert not all(wd == last_project for wd in working_directories), (
                    "All prompts are using the last project path - closure bug detected!"
                )

    def test_register_single_project(self):
        """Test that registering a single project works correctly."""
        mock_server = Mock()
        registered_prompts = {}

        def mock_prompt(name: str, description: str = None):
            def decorator(func):
                registered_prompts[name] = func
                return func

            return decorator

        mock_server.prompt = mock_prompt

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = os.path.join(temp_dir, "single-project")
            os.makedirs(project_path)
            os.makedirs(os.path.join(project_path, ".git"))

            with (
                patch("mcp_claude_code.prompts.get_os_info") as mock_os_info,
                patch(
                    "mcp_claude_code.prompts.get_directory_structure"
                ) as mock_dir_struct,
                patch("mcp_claude_code.prompts.get_git_info") as mock_git_info,
                patch("mcp_claude_code.prompts.PROJECT_SYSTEM_PROMPT") as mock_template,
            ):
                mock_os_info.return_value = ("Darwin", "", "24.5.0")
                mock_dir_struct.return_value = "test-directory-structure"
                mock_git_info.return_value = {
                    "current_branch": "main",
                    "main_branch": "main",
                    "git_status": "clean",
                    "recent_commits": "test-commits",
                }
                mock_template.format.return_value = "formatted-prompt"

                register_all_prompts(mock_server, [project_path])

                # Should have one project prompt
                assert "System prompt for single-project" in registered_prompts

                # Call the prompt function
                prompt_func = registered_prompts["System prompt for single-project"]
                prompt_func()

                # Verify it was called with the correct working directory
                mock_template.format.assert_called_once()
                call_kwargs = mock_template.format.call_args[1]
                assert call_kwargs["working_directory"] == project_path

    def test_register_no_projects(self):
        """Test that registering with no projects works correctly."""
        mock_server = Mock()
        registered_prompts = {}

        def mock_prompt(name: str, description: str = None):
            def decorator(func):
                registered_prompts[name] = func
                return func

            return decorator

        mock_server.prompt = mock_prompt

        # Register with None projects
        register_all_prompts(mock_server, None)

        # Should only have non-project prompts
        project_prompts = [
            name
            for name in registered_prompts.keys()
            if name.startswith("System prompt for")
        ]
        assert len(project_prompts) == 0

        # Should still have other prompts
        expected_prompts = [
            "Compact current conversation",
            "Create a new release",
            "Continue todo by session id",
            "Continue latest todo",
        ]
        for prompt_name in expected_prompts:
            assert prompt_name in registered_prompts

    def test_project_basename_in_prompt_name(self):
        """Test that prompt names use basename of project paths."""
        mock_server = Mock()
        registered_prompts = {}

        def mock_prompt(name: str, description: str = None):
            def decorator(func):
                registered_prompts[name] = func
                return func

            return decorator

        mock_server.prompt = mock_prompt

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested project path
            nested_project = os.path.join(temp_dir, "parent", "child", "my-project")
            os.makedirs(nested_project)
            os.makedirs(os.path.join(nested_project, ".git"))

            with (
                patch("mcp_claude_code.prompts.get_os_info"),
                patch("mcp_claude_code.prompts.get_directory_structure"),
                patch("mcp_claude_code.prompts.get_git_info"),
                patch("mcp_claude_code.prompts.PROJECT_SYSTEM_PROMPT") as mock_template,
            ):
                mock_template.format.return_value = "test-prompt"

                register_all_prompts(mock_server, [nested_project])

                # Should use basename in prompt name
                assert "System prompt for my-project" in registered_prompts
                assert "System prompt for parent" not in registered_prompts
                assert "System prompt for child" not in registered_prompts
