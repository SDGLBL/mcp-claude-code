# Changelog

All notable changes to the MCP Claude Code project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-01-07

### Added
- **Persistent Shell Session Support** (32769b5)
  - New BashSession class for managing persistent shell environments with tmux
  - SessionManager and SessionStorage for comprehensive session lifecycle management
  - Session-based execution mode with environment persistence and working directory tracking
  - Support for interactive commands with `is_input` and `blocking` parameters
  - Command history tracking and session isolation
- **Resource Management and Cleanup** (4c4a59d)
  - Background cleanup thread for periodic session expiration checks every 2 minutes
  - Signal handlers for graceful shutdown (SIGTERM, SIGINT)
  - Atexit handler for cleanup during normal termination
  - Reduced default session TTL from 30 to 5 minutes for aggressive cleanup
  - Session storage metrics and logging for cleanup operations
- **Enhanced Cross-Platform Support** (184c2f7)
  - New CommandExecutor class for Windows-compatible shell command execution
  - Automatic platform detection with tmux availability checking
  - Support for multiple shell types (cmd, powershell, wsl) on Windows
  - Platform-specific command formatting and execution logic
- **Project System Prompt Enhancements** (363f06f)
  - Factory function `create_project_system_prompt` for generating project-specific prompts
  - Manual project system prompt registration for on-demand access
  - Improved code organization and flexibility in prompt generation

### Changed
- **BREAKING CHANGE: Shell Execution Architecture** (bf3233a)
  - Replaced CommandExecutor with BashSessionExecutor for all shell operations
  - All shell tools now use persistent sessions by default
  - Updated run_command tool interface with new session parameters
  - CommandResult now includes additional execution metadata
- **BREAKING CHANGE: Tool Parameter Handling** (bc52019)
  - Migrated all tool parameters to TypedDict and Unpack for improved type safety
  - Consolidated parameter type definitions at module level
  - Enhanced IDE support and runtime type checking
  - Removed redundant parameter validation in favor of Pydantic handling
- **Session ID Handling Improvements** (4263df1, 154a817)
  - Changed default session_id from None to empty string for consistency
  - Simplified session_id validation logic
  - Removed PROMPT_TEST echo command from session initialization
  - More predictable session handling behavior

### Removed
- **Metadata System Simplification** (2cae74e)
  - Removed complex PS1 metadata system for command tracking
  - Eliminated CmdOutputMetadata class and PS1 prompt generation/parsing
  - Simplified CommandResult class to focus on core output
  - Improved reliability across different shell environments
- **DocumentContext Removal** (db23971)
  - Removed DocumentContext class and all related functionality
  - Simplified codebase by removing redundant path tracking
  - Permission management now handled solely by PermissionManager
- **Legacy Command Executor** (bf3233a)
  - Removed old CommandExecutor in favor of unified BashSessionExecutor
  - Consolidated shell execution logic into session-based approach

### Enhanced
- **Command Output Isolation** (46c6c42)
  - Prevented command output accumulation in persistent sessions
  - Added automatic screen clearing and history management
  - Ensured clean execution context for sequential commands
- **Platform-Specific Tool Registration** (184c2f7)
  - Automatic selection of appropriate run_command implementation
  - Seamless fallback between tmux-based and Windows-compatible execution
  - Maintained consistent tool interface across platforms

### Refactoring
- **Improved Shell Execution Mode** (f862a6f)
  - Added subprocess execution mode to BashSessionExecutor
  - Enhanced flexibility in execution strategy selection
- **Code Quality and Type Safety** (bc52019)
  - Comprehensive migration to modern Python type annotations
  - Improved developer experience with better IDE support
  - Reduced boilerplate validation code

## [0.3.4] - 2025-05-29

### Added
- New release script and process improvements (49c7deb)

### Refactored
- **Tool Handler Architecture** (b1f5bda)
  - Simplified tool handler methods by using `get_context()` dependency injection
  - Removed explicit MCPContext parameter from all tool handler signatures
  - Improved code organization and reduced boilerplate across all tool implementations
  - Maintained functionality while making handler signatures cleaner and more consistent

- **FastMCP Migration** (90a1419)
  - Updated all imports from `mcp.server.fastmcp` to `fastmcp` for improved consistency
  - Refactored tool parameter definitions to use pydantic Field annotations
  - Replaced deprecated parameter schema definitions with typed parameters
  - Enhanced type safety with TypedDict for complex parameter types
  - Added validation constraints through Field annotations

- **Test Suite Cleanup** (801efbf)
  - Removed obsolete parameter schema validation tests following pydantic migration
  - Cleaned up deprecated mcp_description method tests
  - Simplified test suites to focus on core functionality rather than schema validation
  - Retained essential tool property assertions for name and description validation

## [0.3.2] - 2025-05-26

### Fixed
- **Project System Prompt Closure Bug** 
  - Fixed critical closure bug in project system prompt registration where all prompts incorrectly used the last project path instead of their respective project paths
  - Multiple projects configured in MCP settings now correctly generate unique system prompts for each project
  - Replaced problematic closure with factory function pattern to ensure proper variable capture
  - Resolves issue where system prompts for all projects would reference 'claude-code-provider-proxy' regardless of the actual project being used

### Added
- **Comprehensive Test Suite for Project System Prompts**
  - Added `tests/test_prompts.py` with 4 comprehensive test cases to prevent regression
  - Tests cover multiple project registration, single project registration, no projects scenario, and project basename handling
  - Includes specific test case that detects the closure bug to prevent future regressions
  - Mock-based testing approach ensures reliable verification of prompt generation functionality

## [0.3.1] - 2025-05-25

### Fixed
- **Todo ID Validation Compatibility** (da8295d)
  - Fixed todo ID validation to accept numeric IDs (integers and floats) in addition to strings
  - Resolves JSON parsing compatibility issue where numeric strings are automatically converted to integers
  - All IDs are now normalized to strings for consistent internal storage
  - Improved validation error messages for better debugging experience

### Maintenance
- **Code Quality Improvements** (626ebec)
  - Removed unused imports and functions across multiple modules
  - Simplified validation.py by removing deprecated functions
  - Fixed linting issues including f-string formatting
  - Updated dependencies in uv.lock file
- **Documentation Updates** (fc688ec)
  - Updated example documentation with latest functionality demonstrations
  - Added cross-references to tutorial documentation for version 0.3 features

## [0.3.0] - 2025-05-25

### Added
- **TODO Management System** (3f146ed)
  - Added TodoReadTool and TodoWriteTool for session-based task tracking
  - Implemented TodoStorage class for in-memory session-based storage
  - Support for todo items with status (pending/in_progress/completed) and priority (high/medium/low)
  - Session ID validation and isolation for secure multi-session support
  - Comprehensive test suite covering unit, integration, and validation scenarios
- **Project Path Support and Prompt System** (2833d07)
  - Added new `--project` CLI argument to specify project paths for prompt generation
  - Refactored prompts into separate modules under `mcp_claude_code/prompts/`
  - Added PROJECT_SYSTEM_PROMPT for project-specific system prompt generation
  - Added utility functions for directory structure and git information extraction
  - Enhanced GitPython dependency for improved git integration
- **MultiEdit Tool for Atomic Multi-File Operations** (2cd71bb)
  - Implemented atomic multi-edit operations with transaction semantics
  - Sequential edit application where each edit operates on previous results
  - Strict validation including exact string matching and expected replacement counts
  - File creation capability when first edit has empty old_string
  - Comprehensive diff generation and error handling
- **Comprehensive Tutorial Documentation** (d71aea7)
  - Added new TUTORIAL.md with detailed instructions for advanced features
  - Project-specific system prompt application via Claude Desktop UI
  - Automated commands for context management and task continuity
  - Practical workflow scenarios and TODO management integration

### Enhanced
- **TODO System Improvements** (f5c2766)
  - Added latest session tracking and auto-continue functionality
  - Renamed `continue_from_last_todo_list` to `continue_todo_by_session_id` for clarity
  - Added `continue_latest_todo` function for automatic session detection
  - Enhanced TodoStorage with timestamp tracking for session management
  - Added `find_latest_active_session` method for locating recent sessions
- **Project TODO Reminder System** (ab3438d)
  - Implemented formatted todo list reminders for active sessions
  - Added empty state handling with PROJECT_TODO_EMPTY_REMINDER
  - Status indicators ([ ], [~], [✓]) and priority indicators (🔴, 🟡, 🟢)
  - Session isolation and comprehensive test coverage (569 lines)
- **Tool Documentation and Usability** (Multiple commits)
  - Enhanced agent tool description with detailed usage guidelines (a989b39, 223c9d1)
  - Improved batch tool description with usage examples and scenarios (70266ff)
  - Enhanced grep_ast tool description with AST context examples (81b6658)
  - Updated thinking tool description with detailed use cases (c829dbf)
  - Clarified filesystem tool documentation for better user experience (ce6b09f, 9d5f144)

### Changed
- **Tool Renaming and Consistency** (Multiple commits)
  - Renamed Jupyter notebook tools: 'read_notebook' → 'notebook_read', 'edit_notebook' → 'notebook_edit' (1be13ea)
  - Renamed 'edit_file' tool to 'edit' for consistency (8404eee)
  - Updated all references and documentation to reflect new naming conventions
- **Installation and Documentation Improvements** (Multiple commits)
  - Completely rewrote installation guide with detailed instructions (56f28c3)
  - Updated INSTALL.md with improved project path configuration instructions (d71aea7, 8053705)
  - Added recommendation for setting projects individually for better system prompt generation
  - Simplified path parameter documentation and emphasized project path importance

### Removed
- **Deprecated Tools and Features** (a1ee681)
  - **BREAKING CHANGE**: Removed `run_script` and `script_tool` functionality
  - Deleted implementation files and removed tool registration
  - Functionality consolidated into core `run_command` tool
- **Deprecated File Operations** (d893f8b)
  - Removed GetFileInfoTool and all related references
  - Cleaned up batch tool and filesystem tool integrations
- **Outdated Documentation** (Multiple commits)
  - Removed deprecated documentation files (USEFUL_PROMPTS.md, debug.md, migration guides) (8163f08)
  - Removed outdated system prompt documentation file (4eb866a)
  - Cleaned up redundant installation steps and outdated recommendations (42e7a69, 8be1a90)

### Refactoring
- **Code Quality and Formatting** (49b4013)
  - Applied consistent code formatting and style improvements across codebase
  - Normalized whitespace, standardized quote usage, improved parameter alignment
  - Enhanced docstring formatting and removed unnecessary code complexity
- **Configuration and Structure** (155992d)
  - Reorganized pyproject.toml configuration sections for better organization
  - Moved pytest.ini_options section and removed redundant configurations
- **Tool Parameter Clarity** (6a14807)
  - Clarified session_id description to specify timestamp in seconds
  - Updated tool descriptions for better developer guidance

### Documentation
- **Enhanced Installation and Configuration** (d71aea7, 56f28c3)
  - Multiple installation methods (uvx, pip/uv, development)
  - Detailed configuration options with practical examples
  - Agent tool setup instructions and performance optimization tips
  - Troubleshooting section and development procedures
- **README Updates** (8ca5e04)
  - Added todo_write and todo_read commands to feature table
  - Updated tool references and removed outdated recommendations
- **Cross-Reference Integration**
  - Added cross-references between installation and tutorial documents
  - Improved parameter table formatting and descriptions

## [0.2.2] - 2025-05-23

### Added
- Added command timeout configuration with `--command-timeout` CLI parameter (099401c)
  - Configurable timeout for shell command execution with default of 120 seconds
  - Increased default timeout from 30s to 120s for more reliable long-running operations
  - Enhanced shell tool reliability for complex command execution scenarios

### Enhanced
- Improved error handling for network-related command execution (099401c)
  - Added `handle_connection_errors` decorator to gracefully handle client disconnections
  - Prevents MCP server crashes when running network-related commands that could cause disconnections
  - Enhanced connection stability for shell tools (run_command, run_script, script_tool)
  - Improved ToolContext logging to silently handle connection errors

### Changed
- Optimized system prompt format and removed redundant instructions (f57e015)
  - Removed outdated sections from system prompt to improve efficiency
  - Leveraged Claude 4's enhanced capabilities to reduce unnecessary guidance
  - Streamlined prompt structure for better performance and clarity

### Fixed
- Cleaned up code formatting by removing trailing whitespace (099401c)
  - Improved code quality and consistency across the codebase
  - Applied consistent formatting standards

## [0.2.1] - 2025-05-18

### Fixed
- Added proper single quote escaping for shell commands (2313d99)
  - Fixed command execution failures when commands contain single quotes
  - Modified `_execute_command` method to escape single quotes by replacing them with `'\''`
  - Added logging for original and escaped commands to assist with debugging
  - Added comprehensive tests for various quote patterns in shell commands
  - Tests verify proper handling of commands containing single quotes, double quotes, and mixed quote patterns

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
