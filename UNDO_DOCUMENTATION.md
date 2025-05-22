# Undo Functionality for MCP Claude Code

This document describes the new undo functionality added to the MCP Claude Code server, which allows reverting recent file modifications made through the `write` and `edit` tools.

## Overview

The undo system tracks file operations and provides the ability to revert changes made during the current session. It supports:

- **Write operations**: Creating new files or overwriting existing files
- **Edit operations**: Making precise text replacements in files
- **History tracking**: Maintaining a configurable number of operations per file
- **Memory management**: Automatic cleanup of old operations

## Features

### Core Functionality
- Automatic tracking of all file modifications
- Configurable maximum number of operations per file (default: 10)
- Memory-efficient storage with size limits
- Thread-safe operation recording
- Detailed operation metadata and timestamps

### Supported Operations
- **File Creation**: Undo will delete the created file
- **File Overwrite**: Undo will restore the previous content
- **Text Editing**: Undo will revert specific text changes

## Configuration

### Server Configuration
The undo functionality can be configured when starting the MCP server:

```bash
# Enable undo with default settings (10 operations per file)
python -m mcp_claude_code.cli

# Configure maximum undo operations per file
python -m mcp_claude_code.cli --max-undo-operations 20

# Disable undo functionality
python -m mcp_claude_code.cli --disable-undo
```

### Programmatic Configuration
When creating a `ClaudeCodeServer` instance:

```python
from mcp_claude_code.server import ClaudeCodeServer

server = ClaudeCodeServer(
    name="my-server",
    undo_enabled=True,          # Enable/disable undo
    max_undo_operations=15,     # Max operations per file
)
```

## Usage

### Available Tools

#### 1. `undo` - Revert Last Operation
Reverts the most recent modification to a file:

```python
# Undo the last operation on a file
result = await undo_tool.call(ctx, file_path="/path/to/file.txt")
```

#### 2. `undo` with History Listing
View available undo operations for a file:

```python
# List undo history without performing undo
result = await undo_tool.call(
    ctx, 
    file_path="/path/to/file.txt",
    list_history=True
)

# List history with content previews
result = await undo_tool.call(
    ctx, 
    file_path="/path/to/file.txt", 
    list_history=True,
    show_content=True
)
```

### Example Workflow

```python
# 1. Write a new file
await write_tool.call(ctx, file_path="/tmp/example.txt", content="Hello, World!")
# Result: File created

# 2. Edit the file
await edit_tool.call(
    ctx,
    file_path="/tmp/example.txt",
    old_string="World",
    new_string="Universe"
)
# Result: File now contains "Hello, Universe!"

# 3. Check undo history
history = await undo_tool.call(
    ctx,
    file_path="/tmp/example.txt",
    list_history=True
)
# Result: Shows 2 operations (write and edit)

# 4. Undo the last edit
await undo_tool.call(ctx, file_path="/tmp/example.txt")
# Result: File reverted to "Hello, World!"

# 5. Undo the file creation
await undo_tool.call(ctx, file_path="/tmp/example.txt")  
# Result: File deleted (undoing creation)
```

## Technical Details

### Architecture
- **UndoManager**: Core component managing operation history
- **UndoOperation**: Individual operation records with metadata
- **DocumentContext**: Integration point with existing file tracking
- **UndoTool**: MCP tool interface for undo operations

### Storage
- Operations are stored in memory during the session
- Each file maintains its own operation history
- Old operations are automatically removed when limits are exceeded
- No persistent storage - history is lost when server restarts

### Memory Usage
- Content is stored as strings in memory
- Each operation stores both previous and new content
- Memory usage scales with file sizes and operation count
- Configurable limits prevent unbounded growth

### Security
- Undo operations respect the same permission boundaries as write/edit
- Path validation prevents directory traversal attacks
- Operations can only be undone for allowed file paths

## Limitations

1. **Session-only**: Undo history is not persisted between server restarts
2. **Memory-based**: Large files or many operations consume memory
3. **Text files only**: Binary files are not supported for undo
4. **Single-user**: No coordination between multiple concurrent users
5. **Sequential only**: Can only undo operations in reverse chronological order

## Error Handling

### Common Error Cases
- **File not found**: If a file is deleted externally, undo may fail
- **Permission denied**: Undo respects the same file permissions as write/edit
- **No history**: Attempting to undo when no operations are recorded
- **Disabled functionality**: When undo is disabled server-wide

### Error Messages
- `"No undo operations available for: {file_path}"`
- `"Undo functionality is disabled on this server"`
- `"Access denied - path outside allowed directories: {file_path}"`
- `"Failed to undo operation for {file_path}: {error_details}"`

## Best Practices

1. **Configure appropriate limits**: Balance memory usage with undo depth
2. **Monitor memory usage**: For servers handling large files
3. **Regular cleanup**: Consider restarting server periodically for long-running instances
4. **Test undo paths**: Verify undo works in your specific use cases
5. **Document usage**: Make users aware of undo availability and limitations

## Future Enhancements

Potential improvements for future versions:
- Persistent undo history across server restarts
- Compressed storage for large file operations
- Selective undo (not just last operation)
- Undo for additional tool types
- Multi-user undo coordination
- Configurable retention policies
