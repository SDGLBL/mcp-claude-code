````markdown
# Debugging with Model Context Protocol Inspector

To debug your MCP project using the inspector tool, run the following command:

```bash
npx @modelcontextprotocol/inspector \
  uv \
  --directory ~/project/mcp-claude-code \
  run \
  claudecode \
  --allow-path \
  {allow path} \
  "--agent-model" \
  "openrouter/google/gemini-2.5-flash-preview" \
  "--agent-max-tokens" \
  "100000" \
  "--agent-api-key" \
  "{api key}" \
  "--enable-agent-tool" \
  "--agent-max-iterations" \
  "30" \
  "--agent-max-tool-uses" \
  "100" \
```
````
