# Installation Guide

This guide covers different installation methods for mcp-claude-code and how to configure it with Claude Desktop.

## Requirements

- Python 3.12 or later
- Claude Desktop application
- Optional: [ripgrep](https://github.com/BurntSushi/ripgrep) for enhanced search performance

## Installation Methods

### Method 1: Using uvx (Recommended)

The simplest way to use mcp-claude-code is with `uvx`, which runs the package without permanent installation:

```bash
uvx --from mcp-claude-code claudecode --install
```

> I highly recommend that you set projects one by one to gain more efficient system prompt generation experience.

This command will automatically configure Claude Desktop for you.

For manual configuration:

```json
{
  "mcpServers": {
    "claude-code": {
      "command": "uvx",
      "args": [
        "--from",
        "mcp-claude-code",
        "claudecode",
        "--allow-path",
        "/path/allow",
        "--project",
        "/path/project1",
        "--project",
        "/path/project2"
      ]
    }
  }
}
```

### Method 2: Using pip/uv

Install the package globally or in a virtual environment:

```bash
# Using pip
pip install mcp-claude-code

# Using uv (recommended)
uv pip install mcp-claude-code
```

Then use the automatic installer:

```bash
claudecode --install --allow-path /path/allow
```

Or configure Claude Desktop manually:

```json
{
  "mcpServers": {
    "claude-code": {
      "command": "claudecode",
      "args": ["--allow-path", "/path/allow"]
    }
  }
}
```

### Method 3: Development Installation

For development or local modifications:

```bash
# Clone the repository
git clone https://github.com/SDGLBL/mcp-claude-code.git
cd mcp-claude-code

# Create virtual environment and install
make venv
make install-dev

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate    # On Windows

# Use the installer
claudecode --install --allow-path /path/allow
```

Or use Python module syntax:

```json
{
  "mcpServers": {
    "claude-code": {
      "command": "python",
      "args": ["-m", "mcp_claude_code.cli", "--allow-path", "/path/allow"]
    }
  }
}
```

## Configuration Options

### Basic Configuration

The minimum required configuration:

```json
{
  "mcpServers": {
    "claude-code": {
      "command": "claudecode",
      "args": ["--allow-path", "/path/allow"]
    }
  }
}
```

### Advanced Configuration

Full configuration with all available options:

```json
{
  "mcpServers": {
    "claude-code": {
      "command": "claudecode",
      "args": [
        "--allow-path",
        "/path/to/project1",
        "--allow-path",
        "/path/to/project2",
        "--project",
        "/path/to/project1",
        "--project",
        "/path/to/project2",
        "--name",
        "custom-claude-code",
        "--transport",
        "stdio",
        "--command-timeout",
        "180",
        "--enable-agent-tool",
        "--agent-model",
        "openai/gpt-4o",
        "--agent-max-tokens",
        "100000",
        "--agent-api-key",
        "your-api-key-here",
        "--agent-base-url",
        "http://localhost:1234/v1",
        "--agent-max-iterations",
        "10",
        "--agent-max-tool-uses",
        "30"
      ]
    }
  }
}
```

### Configuration Parameters

| Parameter                | Type    | Default           | Description                                                                               |
| ------------------------ | ------- | ----------------- | ----------------------------------------------------------------------------------------- |
| `--allow-path`           | string  | current directory | Directory path to allow access (can be specified multiple times)                          |
| `--project`              | string  | -                 | Project path for prompt generation (can be specified multiple times **Highly Recommend**) |
| `--name`                 | string  | "claude-code"     | Name of the MCP server                                                                    |
| `--transport`            | choice  | "stdio"           | Transport protocol ("stdio" or "sse")                                                     |
| `--command-timeout`      | float   | 120.0             | Default timeout for command execution in seconds                                          |
| `--enable-agent-tool`    | flag    | false             | Enable the agent tool functionality                                                       |
| `--agent-model`          | string  | -                 | Model name in LiteLLM format (e.g., "openai/gpt-4o")                                      |
| `--agent-max-tokens`     | integer | -                 | Maximum tokens for agent responses                                                        |
| `--agent-api-key`        | string  | -                 | API key for the LLM provider                                                              |
| `--agent-base-url`       | string  | -                 | Base URL for the LLM provider API endpoint                                                |
| `--agent-max-iterations` | integer | 10                | Maximum number of iterations for agent                                                    |
| `--agent-max-tool-uses`  | integer | 30                | Maximum number of total tool uses for agent                                               |

### Project Paths vs Allow Paths

- **`--allow-path`**: Controls which directories the server can access for file operations
- **`--project`**: Generates project-specific prompts with git info, directory structure, and environment details

The `--project` argument enables automatic generation of comprehensive system prompts that include:

- Git repository information (current branch, recent commits, status)
- Directory structure overview
- Operating system details
- Project-specific context for better assistance

You can specify multiple projects to generate prompts for each one.

## Agent Tool Configuration

The agent tool allows Claude to delegate tasks to specialized sub-agents. It's disabled by default and requires additional configuration.

### Enabling Agent Tool

To enable the agent tool, you need:

1. Add `--enable-agent-tool` to your configuration
2. Configure an LLM provider with API key

### Supported LLM Providers

The agent tool uses LiteLLM format for model specification:

#### OpenAI Models

```bash
--agent-model "openai/gpt-4o"
--agent-model "openai/gpt-4o-mini"
--agent-api-key "your-openai-api-key"
```

#### Anthropic Models

```bash
--agent-model "anthropic/claude-3-5-sonnet-20241022"
--agent-api-key "your-anthropic-api-key"
```

#### Google Models (via OpenRouter)

```bash
--agent-model "openrouter/google/gemini-2.0-flash-exp"
--agent-api-key "your-openrouter-api-key"
```

#### Local/Custom Models

```bash
--agent-model "openai/gpt-4o"  # or any compatible model name
--agent-base-url "http://localhost:1234/v1"
--agent-api-key "local-key"  # often not needed for local
```

### Environment Variables

Instead of command-line arguments, you can use environment variables:

| Environment Variable | Description                          |
| -------------------- | ------------------------------------ |
| `AGENT_MODEL`        | Default model name                   |
| `AGENT_PROVIDER`     | Default provider prefix              |
| `AGENT_MAX_TOKENS`   | Maximum tokens for model responses   |
| `OPENAI_API_KEY`     | OpenAI API key                       |
| `ANTHROPIC_API_KEY`  | Anthropic API key                    |
| `AGENT_TEMPERATURE`  | Model temperature (default: 0.7)     |
| `AGENT_API_TIMEOUT`  | API timeout in seconds (default: 60) |

## Claude Desktop Configuration Locations

The configuration file locations vary by operating system:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`

## Performance Optimization

### Install ripgrep

For faster file searches, install [ripgrep](https://github.com/BurntSushi/ripgrep):

```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
sudo apt install ripgrep

# Windows (using Chocolatey)
choco install ripgrep

# Or download from: https://github.com/BurntSushi/ripgrep/releases
```

### Timeout Configuration

Adjust command timeout for large operations:

```json
{
  "mcpServers": {
    "claude-code": {
      "command": "claudecode",
      "args": ["--command-timeout", "300", "--allow-path", "/path/to/project"]
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the specified paths in `--allow-path` exist and are accessible
2. **Command Not Found**: Make sure the installation method puts `claudecode` in your PATH
3. **Agent Tool Not Working**: Verify the API key and model name are correct
4. **Claude Desktop Not Recognizing Server**: Restart Claude Desktop after configuration changes

### Verification

Test your installation:

```bash
# Check if the command works
claudecode --help

# Test with a simple allowed path
claudecode --allow-path /tmp
```

### Debug Mode

For troubleshooting, you can run the server directly:

```bash
# Run with verbose output
python -m mcp_claude_code.cli --allow-path /path/to/project --transport stdio
```

## Development and Testing

For development work:

```bash
# Install development dependencies
make install-dev

# Run tests
make test

# Run with coverage
make test-cov

# Lint code
make lint

# Format code
make format
```

## Next Steps

After installation:

1. Restart Claude Desktop
2. Verify the server appears in Claude Desktop's MCP servers list
3. Test basic functionality by asking Claude to list files in your project
