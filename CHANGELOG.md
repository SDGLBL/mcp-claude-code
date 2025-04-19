# Changelog

All notable changes to the MCP Claude Code project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.23] - 2025-04-19

### Removed
- Removed project tools package to streamline architecture
  - Removed `mcp_claude_code/tools/project` directory and related test files
  - Removed project analysis functionality which was redundant with filesystem tools
  - Updated import statements and tool registrations across codebase
  - Updated tests to maintain test coverage without project tools

### Changed
- Simplified system prompt for improved usability
  - Removed redundant sections to improve Claude execution efficiency
  - Updated documentation to reflect current toolset
  - Replaced project analysis examples with code search examples

## [0.1.22] - 2025-04-19

### Changed
- Simplified permissions by removing unnecessary default exclusions from sensitive directories
  - Removed `.git`, `.config`, and `.vscode` from the default sensitive directories list
  - Improves usability while maintaining security for truly sensitive directories like `.ssh` and `.gnupg`

## [0.1.21] - 2025-04-19

### Enhanced
- Enhanced tool descriptions with parameter details in mcp_description method
  - Added support for displaying parameter descriptions from schema definitions
  - Improved formatting with hyphen separator for better readability
  - Updated tests to verify parameter descriptions are properly included
  - Makes tool descriptions more informative for Claude

### Fixed
- Fixed pytest configuration by adding asyncio_default_fixture_loop_scope setting
  - Added explicit configuration in pyproject.toml to address deprecation warnings
  - Set asyncio mode to "strict" for more reliable async tests

### Documentation
- Added project_info section to system prompt template
  - Includes repository name and owner details for better context
  - Improves system's ability to generate accurate project-specific responses

### Changed
- Removed outdated TODO comment in agent tool registration
- Updated .gitignore to exclude aider files and CLAUDE.md

## [0.1.20] - 2025-04-03

### Added
- Added new USEFUL_PROMPTS.md document with practical prompt templates for common scenarios:
  - Summarizing history for continued conversations
  - Automation research summaries
  - Release preparation commands
  - Resuming interrupted conversations

### Changed
- Reduced default values for agent tool limits:
  - agent_max_iterations reduced from 30 to 10
  - agent_max_tool_uses reduced from 100 to 30
- Enhanced system prompt documentation for the dispatch_agent tool:
  - Improved guidelines for when to use the dispatch_agent tool
  - Added detailed examples for effective agent prompting
  - Clarified agent limitations and capabilities
  - Added categorized use case recommendations

### Documentation
- Improved README.md with clearer feature descriptions
- Fixed formatting and alignment in README.md tables
- Added cross-reference to USEFUL_PROMPTS.md in the README
- Added specific guidance for file reading operations in system prompt

## [0.1.19] - 2025-03-28

### Added
- Added Agent Tool for task delegation and concurrent execution
  - Agent Tool enables Claude to delegate complex tasks to specialized sub-agents that can work in parallel, enhancing performance for complex operations like code search, analysis, and multi-step tasks
  - Agents use read-only tools to ensure safety while maintaining full access to information retrieval capabilities
  - Introduced new parameter `--enable-agent-tool` to allow users to control whether the agent tool is registered
  - Added parameters `--agent-max-iterations` (default: 30) and `--agent-max-tool-uses` (default: 100) to control agent behavior
  - Implemented multi-agent support to enable concurrent sub-agent execution for improved performance when handling multiple related tasks
  - Agents return results that are automatically formatted and integrated into Claude's responses
- Added LiteLLM integration to support various model providers beyond OpenAI
  - Command line support for specifying the model name, API key, and token limits
  - Support for Anthropic, OpenAI, Google, and other LLM providers
  - Simplified configuration through environment variables or command-line arguments

### Enhanced
- Enhanced system prompt with best practices and dispatch agent usage guidelines
- Improved agent tool implementation with better parameter validation and error handling
- Increased max_tool_uses limit from 15 to 30 for improved agent flexibility
- Optimized agent implementation to avoid redundant checks and improve performance

### Changed
- Restricted agent tool to use only read-only variants of filesystem tools for security
- Simplified agent tool implementation to focus on multi-agent operation
- Refactored system prompt handling and improved user prompt support
- Updated parameter validation to support both string and array inputs for prompts

### Fixed
- Fixed JSON serialization error in agent tool error handling
- Fixed redundant type checks and improved test environment handling
- Improved path description in read_files schema for better clarity
- Updated type annotations to use built-in generics syntax

### Documentation
- Added detailed documentation for the agent tool in INSTALL.md, explaining setup and configuration options
- Added debugging guide for Model Context Protocol Inspector
- Updated installation instructions with LLM model and token configuration options
- Clarified cwd parameter restrictions in shell tool documentation

## [0.1.18] - 2025-03-24

### Enhanced
- Significantly improved performance of `search_content` and `content_replace` tools
- Implemented parallel processing for file searching with batched execution
- Optimized file finding strategy using more efficient directory traversal
- Added semaphore-based concurrency control to avoid overwhelming the system

### Changed
- Replaced recursive directory traversal with more efficient `pathlib.Path.rglob()` method
- Restructured file search logic to filter allowed paths more efficiently
- Changed file pattern matching to use `fnmatch` for more consistent behavior

## [0.1.17] - 2025-03-24

### Enhanced
- Enhanced `search_content` tool to use regular expression pattern matching instead of simple substring matching
- Added comprehensive test suite for regex search functionality
- Improved code search capabilities with pattern matching support

### Changed
- Modified search implementation to use `re.search()` instead of the `in` operator
- Maintained backward compatibility with existing string search patterns

## [0.1.16] - 2025-03-23

### Added
- Added Jupyter notebook support with `read_notebook` and `edit_notebook` tools
- Implemented reading of notebook cells with their outputs (text, error messages, etc.)
- Added capabilities for editing, inserting, and deleting cells in Jupyter notebooks
- Added comprehensive test suite for the notebook operations

### Changed
- Updated tools registration to include the new Jupyter notebook tools
- Enhanced README.md with Jupyter notebook functionality documentation

## [0.1.15] - 2025-03-23

### Added
- Added support for file paths in `search_content` and `content_replace` tools
- Extended functionality to search within and modify a single file directly
- Implemented smarter path handling to detect file vs directory inputs

### Changed
- Updated docstrings to clarify that `path` parameter now accepts both file and directory paths
- Enhanced tool parameter descriptions for improved clarity

### Improved
- Added extensive test coverage for the new file path functionality
- Improved error messaging for file operations

## [0.1.14] - 2025-03-23

### Added
- Enhanced `directory_tree` tool with depth limits and filtering capabilities
- Added parameter `depth` to control traversal depth (default: 3, 0 or -1 for unlimited)
- Added parameter `include_filtered` to optionally include commonly filtered directories
- Added statistics summary to directory tree output

### Changed
- Improved directory tree output format from JSON to more readable indented text
- Added filtering for common development directories (.git, node_modules, etc.)
- Enhanced directory tree structure to show skipped directories with reason

## [0.1.13] - 2025-03-23

### Changed
- Improved README instructions regarding the placement of the system prompt in Claude Desktop
- Clarified that the system prompt must be placed in the "Project instructions" section for optimal performance

## [0.1.12] - 2025-03-22

### Changed
- Modified permissions system to allow access to `.git` folders by default
- Updated tests to reflect the new permission behavior

## [0.1.11] - 2025-03-22

### Changed
- Improved documentation in file_operations.py to clarify that the `path` parameter refers to an absolute path rather than a relative path
- Enhanced developer experience by providing clearer API documentation for FileOperations class methods


## [0.1.10] - 2025-03-22

### Added
- Enhanced release workflow to reliably extract and display release notes

### Changed
- Improved error handling and fallback mechanism for the release process

## [0.1.9] - 2025-03-22

### Fixed
- Fixed GitHub Actions workflow to properly display release notes from CHANGELOG.md
- Added fallback mechanism when release notes aren't found in CHANGELOG.md

## [0.1.8] - 2025-03-22

### Added
- Added "think" tool based on Anthropic's research to enhance Claude's complex reasoning abilities
- Updated documentation with guidance on when and how to use the think tool

## [0.1.7] - 2025-03-22

### Fixed
- Added validation in `edit_file` to ensure `oldText` parameter is not empty

## [0.1.6] - 2025-03-22

### Fixed
- Fixed GitHub Actions workflow permissions for creating releases

## [0.1.5] - 2025-03-22

### Changed
- Updated GitHub Actions to latest versions (v3 to v4 for artifacts, v3 to v4 for checkout, v4 to v5 for setup-python)

## [0.1.4] - 2025-03-22

### Added
- Added UVX support for zero-install usage

### Changed
- Simplified README.md to focus only on configuration with uvx usage
- Updated command arguments in documentation for improved clarity

## [0.1.3] - 2025-03-21

### Fixed
- Fixed package structure to include all subpackages
- Updated build configuration to properly include all modules

## [0.1.2] - 2025-03-21

### Added
- Published to PyPI for easier installation
- Improved package metadata

## [0.1.1] - 2025-03-21

### Added
- Initial public release
- Complete MCP server implementation with Claude Code capabilities
- Tools for code understanding, modification, and analysis
- Security features for safe file operations
- Comprehensive test suite
- Documentation in README

### Changed
- Improved error handling in file operations
- Enhanced permission validation

### Fixed
- Version synchronization between package files

## [0.1.0] - 2025-03-15

### Added
- Initial development version
- Basic MCP server structure
- Core tool implementations