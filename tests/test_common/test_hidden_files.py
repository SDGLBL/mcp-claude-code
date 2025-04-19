"""Tests for hidden files (.dot files) in the permissions module."""

import os
from pathlib import Path


from mcp_claude_code.tools.common.permissions import PermissionManager


class TestHiddenFilePermissions:
    """Test permission handling for hidden files and directories."""

    def test_dotfile_exclusion_behavior(self, temp_dir: str):
        """Test that dotfiles are properly handled in the permission system.

        This test verifies that files with dots in their names are not incorrectly
        excluded just because they contain a substring that matches an excluded pattern.
        """
        manager = PermissionManager()
        manager.add_allowed_path(temp_dir)

        # Create test paths
        problem_path = os.path.join(temp_dir, ".github-workflow-example.yml")
        actual_github_dir = os.path.join(temp_dir, ".github", "workflows", "ci.yml")
        gitignore_file = os.path.join(temp_dir, ".gitignore")
        git_related_file = os.path.join(temp_dir, "git-tutorial.md")

        # Test paths with the fixed implementation
        # The workflow example and gitignore files should be allowed
        assert manager.is_path_allowed(problem_path), (
            "Should allow .github-workflow-example.yml"
        )
        assert manager.is_path_allowed(gitignore_file), "Should allow .gitignore"
        assert manager.is_path_allowed(git_related_file), "Should allow git-tutorial.md"

        # Since .git is now allowed by default, this should also be allowed
        assert manager.is_path_allowed(actual_github_dir), (
            "Should allow actual .github directory"
        )

    def test_various_hidden_files(self, temp_dir: str):
        """Test a variety of hidden files and paths to ensure correct behavior."""
        manager = PermissionManager()
        manager.add_allowed_path(temp_dir)

        # Files that should be allowed (not matching default exclusions)
        allowed_paths = [
            os.path.join(temp_dir, ".hidden_file.txt"),
            os.path.join(temp_dir, "subdir", ".config-example.yml"),
            os.path.join(temp_dir, ".env-sample"),
            os.path.join(temp_dir, ".gitconfig-user"),
            os.path.join(temp_dir, ".github-actions-example.json"),
            os.path.join(temp_dir, ".git", "config"),  # .git now allowed
        ]

        # Files that should be excluded (matching default exclusions)
        excluded_paths = [
            # os.path.join(temp_dir, ".git", "config"), # .git now allowed
            # os.path.join(temp_dir, ".vscode", "settings.json"), # .vscode now allowed
            os.path.join(temp_dir, ".env"),
            os.path.join(temp_dir, "logs", "app.log"),
        ]

        # Test allowed paths
        for path in allowed_paths:
            assert manager.is_path_allowed(path), f"Should allow: {path}"

        # Test excluded paths
        for path in excluded_paths:
            assert not manager.is_path_allowed(path), f"Should exclude: {path}"

    def test_path_component_matching(self, temp_dir: str):
        """Test that path component matching works correctly."""
        manager = PermissionManager()
        manager.add_allowed_path(temp_dir)

        # Add a custom exclusion pattern
        manager.add_exclusion_pattern("exclude_me")

        # Paths with the pattern as a full component (should be excluded)
        full_component_paths = [
            os.path.join(temp_dir, "exclude_me"),
            os.path.join(temp_dir, "exclude_me", "file.txt"),
            os.path.join(temp_dir, "subdir", "exclude_me", "config.json"),
        ]

        # Paths with the pattern as part of a component (should be allowed)
        partial_component_paths = [
            os.path.join(temp_dir, "exclude_me_not.txt"),
            os.path.join(temp_dir, "not_exclude_me", "file.txt"),
            os.path.join(temp_dir, "prefix_exclude_me_suffix.json"),
        ]

        # Test full component paths (should be excluded)
        for path in full_component_paths:
            assert not manager.is_path_allowed(path), (
                f"Should exclude full component: {path}"
            )

        # Test partial component paths (should be allowed)
        for path in partial_component_paths:
            assert manager.is_path_allowed(path), (
                f"Should allow partial component: {path}"
            )

    def test_wildcard_patterns(self, temp_dir: str):
        """Test that wildcard patterns work correctly."""
        manager = PermissionManager()
        manager.add_allowed_path(temp_dir)

        # Default patterns include "*.log", "*.key", etc.

        # Files matching wildcard patterns (should be excluded)
        wildcard_matches = [
            os.path.join(temp_dir, "server.log"),
            os.path.join(temp_dir, "private.key"),
            os.path.join(temp_dir, "certificate.crt"),
            os.path.join(temp_dir, "database.sqlite"),
        ]

        # Files not matching wildcard patterns (should be allowed)
        wildcard_non_matches = [
            os.path.join(temp_dir, "logfile.txt"),  # Doesn't end with .log
            os.path.join(temp_dir, "key_material.txt"),  # Doesn't end with .key
            os.path.join(temp_dir, "log_analysis.py"),  # Doesn't end with .log
        ]

        # Test wildcard matching paths (should be excluded)
        for path in wildcard_matches:
            assert not manager.is_path_allowed(path), (
                f"Should exclude wildcard match: {path}"
            )

        # Test non-matching paths (should be allowed)
        for path in wildcard_non_matches:
            assert manager.is_path_allowed(path), f"Should allow non-matching: {path}"

    def test_real_world_project_paths(self, temp_dir: str):
        """Test with realistic project paths that might be problematic."""
        manager = PermissionManager()
        base_dir = "/Users/lijie/project/mcp-claude-code"
        manager.add_allowed_path(base_dir)

        # These should all be allowed with the fixed implementation
        allowed_project_paths = [
            f"{base_dir}/.github-workflow-example.yml",
            f"{base_dir}/.gitignore",
            f"{base_dir}/.python-version",
            f"{base_dir}/.editorconfig",
            f"{base_dir}/.pre-commit-config.yaml",
            f"{base_dir}/.env.sample",
            f"{base_dir}/.devcontainer/config.json",
        ]

        # These should still be excluded (matching system exclusions)
        excluded_project_paths = [
            # f"{base_dir}/.git/HEAD", # .git now allowed
            # f"{base_dir}/.vscode/settings.json", # .vscode now allowed
            f"{base_dir}/.env",
            f"{base_dir}/logs/debug.log",
            f"{base_dir}/__pycache__/module.pyc",
        ]

        # Mock the permissions check to avoid actual filesystem access
        # This simulates what would happen with the real project paths
        def mock_is_allowed(path):
            path_obj = Path(path).resolve()
            # Skip the actual "is path in allowed_paths" check for testing
            return not manager._is_path_excluded(path_obj)

        # Test allowed project paths
        for path in allowed_project_paths:
            assert mock_is_allowed(path), f"Should allow project path: {path}"

        # Test excluded project paths
        for path in excluded_project_paths:
            assert not mock_is_allowed(path), f"Should exclude project path: {path}"
