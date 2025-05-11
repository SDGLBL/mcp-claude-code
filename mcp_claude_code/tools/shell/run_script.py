"""Run script tool implementation.

This module provides the RunScriptTool for executing scripts with interpreters.
"""

import os
from typing import Any, final, override

from mcp.server.fastmcp import Context as MCPContext
from mcp.server.fastmcp import FastMCP

from mcp_claude_code.tools.common.context import create_tool_context
from mcp_claude_code.tools.shell.base import ShellBaseTool
from mcp_claude_code.tools.shell.command_executor import CommandExecutor


@final
class RunScriptTool(ShellBaseTool):
    """Tool for executing scripts with interpreters."""
    
    def __init__(self, permission_manager: Any, command_executor: CommandExecutor) -> None:
        """Initialize the run script tool.
        
        Args:
            permission_manager: Permission manager for access control
            command_executor: Command executor for running scripts
        """
        super().__init__(permission_manager)
        self.command_executor: CommandExecutor = command_executor
        
    @property
    @override
    def name(self) -> str:
        """Get the tool name.
        
        Returns:
            Tool name
        """
        return "run_script"
        
    @property
    @override
    def description(self) -> str:
        """Get the tool description.
        
        Returns:
            Tool description
        """
        return """Execute a script with the specified interpreter.

Args:
    script: The script content to execute
    cwd: Working directory for script execution. MUST be a subdirectory of one of the allowed paths, not a parent directory. Specify the most specific path possible.
    shell_type: Optional shell to use (e.g., "cmd", "powershell", "wsl", "bash")

    interpreter: The interpreter to use (bash, python, etc.)
    use_login_shell: Whether to use login shell (loads ~/.zshrc, ~/.bashrc, etc.)

Returns:
    The output of the script
"""
        
    @property
    @override
    def parameters(self) -> dict[str, Any]:
        """Get the parameter specifications for the tool.
        
        Returns:
            Parameter specifications
        """
        return {
            "properties": {
                "script": {
                    "title": "Script",
                    "type": "string"
                },
                "cwd": {
                    "title": "Cwd",
                    "type": "string"
                },
                "shell_type": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"}
                    ],
                    "default": None,
                    "title": "Shell Type"
                },
                "interpreter": {
                    "default": "bash",
                    "title": "Interpreter",
                    "type": "string"
                },
                "use_login_shell": {
                    "default": True,
                    "title": "Use Login Shell",
                    "type": "boolean"
                }
            },
            "required": ["script", "cwd"],
            "title": "run_scriptArguments",
            "type": "object"
        }
        
    @property
    @override
    def required(self) -> list[str]:
        """Get the list of required parameter names.
        
        Returns:
            List of required parameter names
        """
        return ["script", "cwd"]
    
    @override
    async def prepare_tool_context(self, ctx: MCPContext) -> Any:
        """Create and prepare the tool context.
        
        Args:
            ctx: MCP context
            
        Returns:
            Prepared tool context
        """
        tool_ctx = create_tool_context(ctx)
        tool_ctx.set_tool_info(self.name)
        return tool_ctx
        
    @override
    async def call(self, ctx: MCPContext, **params: Any) -> str:
        """Execute the tool with the given parameters.
        
        Args:
            ctx: MCP context
            **params: Tool parameters
            
        Returns:
            Tool result
        """
        tool_ctx = await self.prepare_tool_context(ctx)
        
        # Extract parameters
        script = params.get("script")
        cwd = params.get("cwd")
        shell_type = params.get("shell_type")
        interpreter = params.get("interpreter", "bash")
        use_login_shell = params.get("use_login_shell", True)
        
        # Validate required parameters
        if not script:
            await tool_ctx.error("Parameter 'script' is required but was None")
            return "Error: Parameter 'script' is required but was None"
            
        if script.strip() == "":
            await tool_ctx.error("Parameter 'script' cannot be empty")
            return "Error: Parameter 'script' cannot be empty"
            
        # Validate interpreter
        if not interpreter:
            interpreter = "bash"  # Use default if None
        elif interpreter.strip() == "":
            await tool_ctx.error("Parameter 'interpreter' cannot be empty")
            return "Error: Parameter 'interpreter' cannot be empty"
            
        # Validate required cwd parameter
        if not cwd:
            await tool_ctx.error("Parameter 'cwd' is required but was None")
            return "Error: Parameter 'cwd' is required but was None"
            
        if cwd.strip() == "":
            await tool_ctx.error("Parameter 'cwd' cannot be empty")
            return "Error: Parameter 'cwd' cannot be empty"
        
        await tool_ctx.info(f"Executing script with interpreter: {interpreter}")
        
        # Check if working directory is allowed
        if not self.is_path_allowed(cwd):
            await tool_ctx.error(f"Working directory not allowed: {cwd}")
            return f"Error: Working directory not allowed: {cwd}"
            
        # Check if working directory exists
        if not os.path.isdir(cwd):
            await tool_ctx.error(f"Working directory does not exist: {cwd}")
            return f"Error: Working directory does not exist: {cwd}"
            
        # Execute the script
        result = await self.command_executor.execute_script(
            script=script,
            interpreter=interpreter,
            cwd=cwd,
            shell_type=shell_type,
            timeout=30.0,
            use_login_shell=use_login_shell
        )
        
        # Report result
        if result.is_success:
            await tool_ctx.info("Script executed successfully")
        else:
            await tool_ctx.error(f"Script execution failed with exit code {result.return_code}")
            
        # Format the result
        if result.is_success:
            # For successful scripts, just return stdout unless stderr has content
            if result.stderr:
                return f"Script executed successfully.\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            return result.stdout
        else:
            # For failed scripts, include all available information
            return result.format_output()
            
    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this run script tool with the MCP server.
        
        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.
        
        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure
        
        @mcp_server.tool(name=self.name, description=self.mcp_description)
        async def run_script(ctx: MCPContext, script: str, cwd: str, shell_type: str | None = None, interpreter: str = "bash", use_login_shell: bool = True) -> str:
            return await tool_self.call(ctx, script=script, cwd=cwd, shell_type=shell_type, interpreter=interpreter, use_login_shell=use_login_shell)
