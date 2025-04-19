## Getting Started

### Usage

#### Configuring Claude Desktop

You can run it with `uvx run mcp-claude-code` without installation. Configure Claude Desktop to use this server by adding the following to your Claude Desktop configuration file:

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
        "/path/to/your/project"
      ]
    }
  }
}
```

Make sure to replace `/path/to/your/project` with the actual path to the project you want Claude to access.

#### Advanced Configuration Options

You can customize the server using other options:

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
        "/path/to/project",
        "--name",
        "custom-claude-code",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

#### LLM Model and Token Configuration

You can customize the agent behavior by specifying the LLM model and token limits:

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
        "/path/to/project",
        "--enable-agent-tool",
        "--agent-model",
        "{litellm-model-name}",
        "--agent-max-tokens",
        "100000",
        "--agent-api-key",
        "{your-api-key}",
        "--agent-max-tool-uses"
        "30",
        "--agent-max-iterations",
        "10"
      ]
    }
  }
}
```

The available LLM configuration options are:

- `--agent-model`: Specify the model name in LiteLLM format (e.g., 'openai/gpt-4o', 'anthropic/claude-3-sonnet')
- `--agent-max-tokens`: Specify the maximum tokens for agent responses
- `--agent-api-key`: Specify the API key for the LLM provider (for development/testing only)
- `--agent-max-iterations`: Maximum number of iterations for agent (default: 10)
- `--agent-max-tool-uses`: Maximum number of total tool uses for agent (default: 30)
- `--enable-agent-tool`: Enable the agent tool (disabled by default)

The model name uses the LiteLLM format with provider prefixes. Examples:

- OpenAI models: `openai/gpt-4o`, `openai/gpt-4o-mini`
- Anthropic models: `anthropic/claude-3.7-sonnet`
- Google models: `openrouter/google/gemini-2.5-flash-preview` (Recommended)

If you don't specify these options, the agent will use the following environment variables:

- `AGENT_MODEL`: Default model name (falls back to "openai/gpt-4o")
- `AGENT_PROVIDER`: Default provider prefix
- `AGENT_MAX_TOKENS`: Maximum tokens for model responses
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`: API keys for respective providers

#### Agent Tool Configuration

The agent tool allows Claude to delegate tasks to specialized sub-agents. By default, the agent tool is disabled. You can enable and configure it using these options:

- `--enable-agent-tool`: Enable the agent tool functionality
- `--agent-max-iterations`: Control the maximum number of back-and-forth interactions an agent can have (default: 10)
- `--agent-max-tool-uses`: Control the maximum number of tool calls an agent can make (default: 30)

Enabling the agent tool can improve Claude's ability to handle complex tasks by allowing it to delegate to specialized sub-agents. However, it requires setting up an LLM provider with a valid API key.

### Configuring Claude Desktop System Prompt

To get the best experience with Claude Code, you need to add the provided system prompt to your Claude Desktop client. This system prompt guides Claude through a structured workflow for code modifications and project management.

Follow these steps:

1. Locate the system prompt file in this repository at `doc/system_prompt`
2. Open your Claude Desktop client
3. Create a new project or open an existing one
4. Navigate to the "Project instructions" section in the Claude Desktop sidebar
5. Copy the contents of `doc/system_prompt` and paste it into the "Project instructions" section
6. Replace `{project_path}` with the actual absolute path to your project

The system prompt provides Claude with:

- A structured workflow for analyzing and modifying code
- Best practices for project exploration and analysis
- Guidelines for development, refactoring, and quality assurance
- Special formatting instructions for mathematical content

This step is crucial as it enables Claude to follow a consistent approach when helping you with code modifications.
