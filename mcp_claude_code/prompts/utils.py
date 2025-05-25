import platform
from pathlib import Path

try:
    from git import Repo

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


def get_os_info() -> tuple[str, str, str]:
    """Get the operating system information.
    Returns:
        tuple: A tuple containing the system name, release, and version.
    """
    system = platform.system()  # noqa: F821
    release = platform.release()
    version = platform.version()

    if system == "Darwin":
        system = "MacOS"
    elif system == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("NAME="):
                        name = line.split("=")[1].strip().strip('"')
                        if "Ubuntu" in name:
                            system = "Ubuntu"
                        elif "Debian" in name:
                            system = "Debian"
                        elif "Fedora" in name:
                            system = "Fedora"
                        elif "CentOS" in name:
                            system = "CentOS"
                        elif "Arch Linux" in name:
                            system = "Arch Linux"
                        system = name
        except FileNotFoundError:
            dist = platform.freedesktop_os_release()
            if dist and "NAME" in dist:
                name = dist["NAME"]
                if "Ubuntu" in name:
                    system = "Ubuntu"
                system = name
            system = "Linux"
    elif system == "Java":
        system = "Java"

    return system, release, version


def get_directory_structure(
    path: str, max_depth: int = 3, include_filtered: bool = False
) -> str:
    """Get a directory structure similar to directory_tree tool.

    Args:
        path: The directory path to scan
        max_depth: Maximum depth to traverse (0 for unlimited)
        include_filtered: Whether to include normally filtered directories

    Returns:
        Formatted directory structure as a string
    """
    try:
        dir_path = Path(path)

        if not dir_path.exists() or not dir_path.is_dir():
            return f"Error: {path} is not a valid directory"

        # Define filtered directories (same as directory_tree.py)
        FILTERED_DIRECTORIES = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".idea",
            ".vs",
            ".vscode",
            "dist",
            "build",
            "target",
            ".ruff_cache",
            ".llm-context",
        }

        def should_filter(current_path: Path) -> bool:
            """Check if a directory should be filtered."""
            # Don't filter if it's the explicitly requested path
            if str(current_path.absolute()) == str(dir_path.absolute()):
                return False
            # Filter based on directory name if filtering is enabled
            return current_path.name in FILTERED_DIRECTORIES and not include_filtered

        def build_tree(current_path: Path, current_depth: int = 0) -> list[dict]:
            """Build directory tree recursively."""
            result = []

            try:
                # Sort entries: directories first, then files alphabetically
                entries = sorted(
                    current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name)
                )

                for entry in entries:
                    if entry.is_dir():
                        entry_data = {"name": entry.name, "type": "directory"}

                        # Check if we should filter this directory
                        if should_filter(entry):
                            entry_data["skipped"] = "filtered-directory"
                            result.append(entry_data)
                            continue

                        # Check depth limit (if enabled)
                        if max_depth > 0 and current_depth >= max_depth:
                            entry_data["skipped"] = "depth-limit"
                            result.append(entry_data)
                            continue

                        # Process children recursively
                        entry_data["children"] = build_tree(entry, current_depth + 1)
                        result.append(entry_data)
                    else:
                        # Add files only if within depth limit
                        if max_depth <= 0 or current_depth < max_depth:
                            result.append({"name": entry.name, "type": "file"})

            except Exception:
                # Skip directories we can't read
                pass

            return result

        def format_tree(tree_data: list[dict], level: int = 0) -> list[str]:
            """Format tree data as indented strings."""
            lines = []

            for item in tree_data:
                # Indentation based on level
                indent = "  " * level

                # Format based on type
                if item["type"] == "directory":
                    if "skipped" in item:
                        lines.append(
                            f"{indent}{item['name']}/ [skipped - {item['skipped']}]"
                        )
                    else:
                        lines.append(f"{indent}{item['name']}/")
                        # Add children with increased indentation if present
                        if "children" in item:
                            lines.extend(format_tree(item["children"], level + 1))
                else:
                    # File
                    lines.append(f"{indent}{item['name']}")

            return lines

        # Build and format the tree
        tree_data = build_tree(dir_path)
        formatted_lines = format_tree(tree_data)

        # Add the root directory path as a prefix
        result = f"- {dir_path}/"
        if formatted_lines:
            result += "\n" + "\n".join(f"  {line}" for line in formatted_lines)

        return result

    except Exception as e:
        return f"Error generating directory structure: {str(e)}"


def get_git_info(path: str) -> dict[str, str | None]:
    """Get git information for a repository.

    Args:
        path: Path to the git repository

    Returns:
        Dictionary containing git information
    """
    if not GIT_AVAILABLE:
        return {
            "current_branch": None,
            "main_branch": None,
            "git_status": "GitPython not available",
            "recent_commits": "GitPython not available",
        }

    try:
        repo = Repo(path)

        # Get current branch
        try:
            current_branch = repo.active_branch.name
        except Exception:
            current_branch = "HEAD (detached)"

        # Try to determine main branch
        main_branch = "main"  # default
        try:
            # Check if 'main' exists
            if "origin/main" in [ref.name for ref in repo.refs]:
                main_branch = "main"
            elif "origin/master" in [ref.name for ref in repo.refs]:
                main_branch = "master"
            elif "main" in [ref.name for ref in repo.refs]:
                main_branch = "main"
            elif "master" in [ref.name for ref in repo.refs]:
                main_branch = "master"
        except Exception:
            pass

        # Get git status
        try:
            status_lines = []

            # Check for staged changes
            staged_files = list(repo.index.diff("HEAD"))
            if staged_files:
                for item in staged_files[:25]:  # Limit to first 25
                    change_type = item.change_type
                    status_lines.append(f"{change_type[0].upper()} {item.a_path}")
                if len(staged_files) > 25:
                    status_lines.append(
                        f"... and {len(staged_files) - 25} more staged files"
                    )

            # Check for unstaged changes
            unstaged_files = list(repo.index.diff(None))
            if unstaged_files:
                for item in unstaged_files[:25]:  # Limit to first 25
                    status_lines.append(f"M {item.a_path}")
                if len(unstaged_files) > 25:
                    status_lines.append(
                        f"... and {len(unstaged_files) - 25} more modified files"
                    )

            # Check for untracked files
            untracked_files = repo.untracked_files
            if untracked_files:
                for file in untracked_files[:25]:  # Limit to first 25
                    status_lines.append(f"?? {file}")
                if len(untracked_files) > 25:
                    status_lines.append(
                        f"... and {len(untracked_files) - 25} more untracked files"
                    )

            git_status = (
                "\n".join(status_lines) if status_lines else "Working tree clean"
            )

        except Exception:
            git_status = "Unable to get git status"

        # Get recent commits
        try:
            commits = []
            for commit in repo.iter_commits(max_count=5):
                short_hash = commit.hexsha[:7]
                message = commit.message.split("\n")[0]  # First line only
                commits.append(f"{short_hash} {message}")
            recent_commits = "\n".join(commits)
        except Exception:
            recent_commits = "Unable to get recent commits"

        return {
            "current_branch": current_branch,
            "main_branch": main_branch,
            "git_status": git_status,
            "recent_commits": recent_commits,
        }

    except Exception as e:
        return {
            "current_branch": None,
            "main_branch": None,
            "git_status": f"Error: {str(e)}",
            "recent_commits": f"Error: {str(e)}",
        }
