# Changelog

All notable changes to the MCP Claude Code project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-05-16

### Added
- Added batch tool availability to dispatch_agent (c7bc6a8)
  - Enhanced agent capabilities by adding BatchTool to available tools
  - Enables batch processing for improved agent performance
  - Allows for concurrent execution of multiple operations

### Changed
- Renamed read_files tool to read with improved functionality (42d8e94)
  - Simplified interface with single file_path parameter
  - Added line number display in output (cat -n format)
  - Added offset and limit parameters for reading specific line ranges
  - Added line truncation for very long lines
  - Improved error handling and parameter validation
- Enforced absolute path requirement in agent prompts (c3fe452)
  - Added validation for absolute paths in dispatch_agent prompts
  - Improved error messages with usage examples
  - Enhanced reliability for filesystem operations
- Renamed edit_file tool to edit throughout documentation and code (10cfe12)
  - Updated all references for consistency
  - Improved parameter handling and validation
  - Enhanced error messages

### Fixed
- Removed outdated docstring section in agent_tool.py (c30ad80)
  - Eliminated obsolete information about args and returns
  - Maintained core tool functionality description
- Updated directory verification tool reference in write.py docs (fb36e12)
  - Changed LS tool reference to directory_tree tool for accuracy
  - Aligned documentation with actual tool naming conventions

### Documentation
- Added example for dispatching multiple agents in batch operations (8ed8769)
  - Demonstrated concurrent agent dispatch for information retrieval
  - Added batch operations as valid use case for agent operations
- Clarified batch tool usage guidelines and added examples (9e14410)
  - Emphasized related changes vs. independent operations
  - Distinguished between simple mechanical changes and complex validations
  - Added practical usage scenarios and examples
- Refactored dispatch_agent documentation (81292c8)
  - Simplified and consolidated usage guidelines
  - Updated concurrency recommendations for batch capabilities
  - Improved readability with clearer section organization

## [0.1.31] - 2025-05-16

### Added
- Added batch tool for parallel tool execution (eade6f7)
  - New tool that enables executing multiple tool invocations in parallel within a single request
  - Significantly improves performance by reducing context usage and latency for multiple operations
  - Supports independent tool operations with proper error handling and result formatting
  - Particularly useful for running multiple searches, file operations, or data gathering in parallel

### Changed
- Renamed tool tags in system prompt for consistency and clarity (030956c)
  - Changed `<think_tool>` to `<think>` and `<grep_ast_tool>` to `<grep_ast>` to maintain consistent naming
  - Improves readability and aligns with the simpler tag naming pattern used elsewhere in documentation

## [0.1.30] - 2025-05-15

### Added
- Added release creation prompt and registration (98fbd45)
  - New prompt template with step-by-step guidance for creating project releases
  - Detailed instructions for version analysis, updates, changelog creation, and tagging
  - Structured approach for consistent release processes
  - Improved documentation for the compact() prompt function

## [0.1.29] - 2025-05-15

### Added
- Added compact conversation prompt and registration (893bef5)
  - New prompt module with detailed instructions for summarizing technical conversations
  - Structured format for capturing user requests, technical concepts, and problem-solving approaches
  - Helps maintain context during technical discussions with structured summaries

### Changed
- Reorganized grep parameters and improved type hints (25c699a)
  - Reordered parameters to make tool_ctx required and first in parameter lists
  - Replaced Optional type hints with modern | None syntax
  - Added explicit type hints for path and include parameters
  - Improved code clarity while maintaining backward compatibility

### Maintenance
- Added claude-code-doc directory to .gitignore (918e88e)
  - Prevents accidental commits of generated documentation files

## [0.1.28] - 2025-05-14

### Added
- Added liteLLM agent_base_url parameter for local LLM support (0f93398)
  - Enables integration with locally hosted models
  - Requires fake API key even when unnecessary
  - Enhanced CLI arguments for configuration

### Changed
- Renamed SearchContentTool to Grep and integrated ripgrep for improved performance (132a603)
  - Added ripgrep integration for significantly faster file content searches
  - Enhanced pattern matching with regex support
  - Maintained backward compatibility through SearchContentTool shim
  - Renamed write_file tool to write and edit_file to edit for consistency
  - Added comprehensive documentation in migration_SearchContentTool_to_Grep.md

### Added
- Added Windows shell execution and script support (d2a8441)
  - Support for CMD, PowerShell, and WSL shells
  - Enhanced command execution for cross-platform compatibility
  - Improved script handling for Windows environments

### Fixed
- Added platform-specific support for temp folders (d1f60cf)
  - Improved cross-platform compatibility
  - Enhanced permissions system for Windows environments

## [0.1.27] - 2025-05-03

### Added
- Added AST-aware code search tool (`grep_ast`) that provides structural context for matches (6a37df6)
  - Shows how code matches fit within functions, classes, and other structures
  - Makes it easier to understand code organization when exploring unfamiliar codebases
  - Added dependency on grep-ast package
  - Includes comprehensive test suite covering various search scenarios

### Documentation
- Updated system prompt with best practices for using the grep_ast tool
- Enhanced README with grep_ast tool description
- Added detailed usage instructions in tool documentation

## [0.1.26] - 2025-04-27

### Fixed
- Fix issue with not starting application due to litellm==1.67.2 (#11)

### Documentation
- Correct formatting and clarify scope requirement in agent prompting guide (3532d4d)

## [0.1.24] - 2025-04-25

### Changed
- Simplified agent tool to support only single string prompt parameter
  - Renamed parameter from "prompts" to "prompt" for improved clarity
  - Removed multi-agent concurrent execution to simplify implementation
  - Updated documentation and tests to match new single-agent design

### Added
- Added logging for agent tool execution results
  - Logs tool name and first 100 characters of result for improved debugging
  - Makes the execution flow more transparent in logs

### Documentation
- Updated system prompt documentation for clarity
  - Clarified confirmation step by changing "before executing it" to "before executing any tool"
  - Enhanced thinking tool guidelines by emphasizing concise and accurate content
  - Refined learning step to specify documentation location in artifact
  - Removed redundant best practices that were covered by other principles
  - Removed deprecated /init command from user commands section
- Updated Google model recommendation to gemini-2.5-flash-preview in documentation

### Refactoring
- Removed --project-dir argument from CLI since project tools were removed

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
