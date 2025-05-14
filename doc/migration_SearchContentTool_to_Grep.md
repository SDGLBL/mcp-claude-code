# Migration from SearchContentTool to Grep

## Overview

The `SearchContentTool` has been renamed to `Grep` to better align with its functionality and to provide enhanced performance through the integration with the high-performance [ripgrep](https://github.com/BurntSushi/ripgrep) tool.

## Key Changes

- Renamed `SearchContentTool` to `Grep`
- Updated parameter names (`file_pattern` changed to `include`)
- Added automatic ripgrep integration for improved performance
- Maintained backward compatibility for existing code

## Migration Steps

### Import Changes

Change your imports from:

```python
from mcp_claude_code.tools.filesystem.search_content import SearchContentTool
```

To:

```python
from mcp_claude_code.tools.filesystem.grep import Grep
```

### Parameter Changes

The `file_pattern` parameter has been renamed to `include` to better reflect its purpose:

```python
# Old
result = await search_content.call(ctx, pattern="search term", path="/path/to/dir", file_pattern="*.py")

# New
result = await grep.call(ctx, pattern="search term", path="/path/to/dir", include="*.py")
```

### Backward Compatibility

For backward compatibility, a shim implementation of `SearchContentTool` is provided that extends `Grep`. This allows existing code to continue working without modification, but it will issue a deprecation warning.

The `Grep` tool also continues to support the `file_pattern` parameter for backward compatibility, but it's recommended to use the new `include` parameter in new code.

## Performance Improvements

The `Grep` tool automatically detects if [ripgrep](https://github.com/BurntSushi/ripgrep) is installed on the system:

- If ripgrep is installed, the tool will use it to perform searches, providing significant performance improvements, especially for large codebases
- If ripgrep is not installed, the tool will fall back to the original Python implementation

### Benefits of ripgrep

Ripgrep provides several advantages over the original Python implementation:

1. **Speed**: ripgrep is significantly faster than Python's regex implementation, especially for large codebases
2. **Memory efficiency**: ripgrep is designed to be memory-efficient and uses streaming processing
3. **Smart filtering**: ripgrep automatically respects `.gitignore` files and ignores binary files
4. **Advanced regex support**: ripgrep's regex engine has better performance characteristics
5. **Parallel processing**: ripgrep can utilize multiple CPU cores for searching

## How to Install ripgrep

For optimal performance, it's recommended to install ripgrep on your system:

### macOS

```bash
brew install ripgrep
```

### Ubuntu/Debian

```bash
apt-get install ripgrep
```

### Windows

```bash
# Using chocolatey
choco install ripgrep

# Using scoop
scoop install ripgrep
```

### From Source

For other platforms or to build from source, see the [ripgrep installation instructions](https://github.com/BurntSushi/ripgrep#installation).

## Implementation Details

The `Grep` tool uses the `--json` output format from ripgrep to parse results reliably. This provides structured data that includes file paths, line numbers, and matching text.

If ripgrep is not available, the tool falls back to a pure Python implementation that maintains the same interface and functionality but with lower performance.
