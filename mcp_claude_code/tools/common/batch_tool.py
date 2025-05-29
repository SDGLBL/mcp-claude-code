"""Batch tool implementation for MCP Claude Code.

This module provides the BatchTool that allows for executing multiple tools in
parallel or serial depending on their characteristics.
"""

import asyncio
from typing import Annotated, Any, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.common.base import BaseTool
from mcp_claude_code.tools.common.context import create_tool_context


class InvocationItem(TypedDict):
    """A single tool invocation item.

    Attributes:
        tool_name: The name of the tool to invoke
        input: The input to pass to the tool
    """

    tool_name: Annotated[
        str,
        Field(
            description="The name of the tool to invoke",
            min_length=1,
        ),
    ]
    input: Annotated[
        dict[str, Any],
        Field(
            description="The input to pass to the tool",
        ),
    ]


Description = Annotated[
    str,
    Field(
        description="A short (3-5 word) description of the batch operation",
        min_length=1,
    ),
]

Invocations = Annotated[
    list[InvocationItem],
    Field(
        description="The list of tool invocations to execute (required -- you MUST provide at least one tool invocation)",
        min_length=1,
    ),
]


class BatchToolParams(TypedDict):
    """Parameters for the BatchTool.

    Attributes:
        description: A short (3-5 word) description of the batch operation
        invocations: The list of tool invocations to execute (required -- you MUST provide at least one tool invocation)
    """

    description: Description
    invocations: Invocations


@final
class BatchTool(BaseTool):
    """Tool for executing multiple tools in a single request.

    Executes a list of tool invocations in parallel when possible, or
    otherwise serially. Returns the collected results from all invocations.
    """

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "batch"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Batch execution tool that runs multiple tool invocations in a single request.

Tools are executed in parallel when possible, and otherwise serially.
Takes a list of tool invocations (tool_name and input pairs).
Returns the collected results from all invocations.
Use this tool when you need to run multiple independent tool operations at once -- it is awesome for speeding up your workflow, reducing both context usage and latency.
Each tool will respect its own permissions and validation rules.
The tool's outputs are NOT shown to the user; to answer the user's query, you MUST send a message with the results after the tool call completes, otherwise the user will not see the results.

<batch_example>
When dispatching multiple agents to find necessary information.
batch(
  description="Update import statements across modules",
  invocations=[
    {tool_name: "dispatch_agent", input: {prompt: "Search for all instances of 'logger' configuration in /app/config directory"}},
    {tool_name: "dispatch_agent", input: {prompt: "Find all test files that reference 'UserService' in /app/tests"}},
  ]
)

Common scenarios for effective batching:
1. Reading multiple related files in one operation
2. Performing a series of simple mechanical changes
3. Running multiple diagnostic commands
4. Dispatch multiple agents to complete the task

To make a batch call, provide the following:
1. description: A short (3-5 word) description of the batch operation
2. invocations: List of invocation [{"tool_name": "...", "input": "..."}], tool_name: The name of the tool to invoke,newText: The input to pass to the tool


Available tools in batch call:
Tool: dispatch_agent,read,directory_tree,grep,grep_ast,run_command,notebook_read
Not available: think,write,edit,multi_edit,notebook_edit
"""

    def __init__(self, tools: dict[str, BaseTool]) -> None:
        """Initialize the batch tool.

        Args:
            tools: Dictionary mapping tool names to tool instances
        """
        self.tools = tools

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[BatchToolParams],
    ) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = create_tool_context(ctx)
        tool_ctx.set_tool_info(self.name)

        # Extract parameters
        description = params.get("description")
        invocations: list[dict[str, Any]] = params.get("invocations", list())

        # Validate required parameters
        if not description:
            await tool_ctx.error(
                "Parameter 'description' is required but was None or empty"
            )
            return "Error: Parameter 'description' is required but was None or empty"

        if not invocations:
            await tool_ctx.error(
                "Parameter 'invocations' is required but was None or empty"
            )
            return "Error: Parameter 'invocations' is required but was None or empty"

        if not isinstance(invocations, list) or len(invocations) == 0:
            await tool_ctx.error("Parameter 'invocations' must be a non-empty list")
            return "Error: Parameter 'invocations' must be a non-empty list"

        await tool_ctx.info(
            f"Executing batch operation: {description} ({len(invocations)} invocations)"
        )

        # Execute all tool invocations in parallel
        tasks: list[asyncio.Future[dict[str, Any]]] = []
        invocation_map: dict[
            asyncio.Future[dict[str, Any]], dict[str, Any]
        ] = {}  # Map task Future to invocation

        for i, invocation in enumerate(invocations):
            # Extract tool name and input from invocation
            tool_name: str = invocation.get("tool_name", "")
            tool_input: dict[str, Any] = invocation.get("input", {})

            # Validate tool invocation
            if not tool_name:
                error_message = f"Tool name is required in invocation {i}"
                await tool_ctx.error(error_message)
                # Add direct result for this invocation
                tasks.append(asyncio.Future())
                tasks[-1].set_result(
                    {"invocation": invocation, "result": f"Error: {error_message}"}
                )
                invocation_map[tasks[-1]] = invocation
                continue

            # Check if the tool exists
            if tool_name not in self.tools:
                error_message = f"Tool '{tool_name}' not found"
                await tool_ctx.error(error_message)
                # Add direct result for this invocation
                tasks.append(asyncio.Future())
                tasks[-1].set_result(
                    {"invocation": invocation, "result": f"Error: {error_message}"}
                )
                invocation_map[tasks[-1]] = invocation
                continue

            # Create a task for this tool invocation
            try:
                tool = self.tools[tool_name]
                await tool_ctx.info(f"Creating task for tool: {tool_name}")

                # Create coroutine for this tool execution
                async def execute_tool(
                    tool_obj: BaseTool, tool_name: str, tool_input: dict[str, Any]
                ):
                    try:
                        await tool_ctx.info(f"Executing tool: {tool_name}")
                        result = await tool_obj.call(ctx, **tool_input)
                        await tool_ctx.info(f"Tool '{tool_name}' execution completed")
                        return {
                            "invocation": {"tool_name": tool_name, "input": tool_input},
                            "result": result,
                        }
                    except Exception as e:
                        error_message = f"Error executing tool '{tool_name}': {str(e)}"
                        await tool_ctx.error(error_message)
                        return {
                            "invocation": {"tool_name": tool_name, "input": tool_input},
                            "result": f"Error: {error_message}",
                        }

                # Schedule the task
                task = asyncio.create_task(execute_tool(tool, tool_name, tool_input))
                tasks.append(task)
                invocation_map[task] = invocation
            except Exception as e:
                error_message = f"Error scheduling tool '{tool_name}': {str(e)}"
                await tool_ctx.error(error_message)
                # Add direct result for this invocation
                tasks.append(asyncio.Future())
                tasks[-1].set_result(
                    {"invocation": invocation, "result": f"Error: {error_message}"}
                )
                invocation_map[tasks[-1]] = invocation

        # Wait for all tasks to complete
        await tool_ctx.info(f"Waiting for {len(tasks)} tool executions to complete")
        results: list[dict[str, Any]] = []

        # As tasks complete, collect their results
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                invocation = invocation_map[task]
                tool_name: str = invocation.get("tool_name", "unknown")
                error_message = f"Unexpected error in tool '{tool_name}': {str(e)}"
                await tool_ctx.error(error_message)
                results.append(
                    {"invocation": invocation, "result": f"Error: {error_message}"}
                )

        # Format the results
        formatted_results = self._format_results(results)
        await tool_ctx.info(
            f"Batch operation '{description}' completed with {len(results)} results"
        )

        return formatted_results

    def _format_results(self, results: list[dict[str, dict[str, Any]]]) -> str:
        """Format the results from multiple tool invocations.

        Args:
            results: List of tool invocation results

        Returns:
            Formatted results string
        """
        formatted_parts: list[str] = []
        for i, result in enumerate(results):
            invocation: dict[str, Any] = result["invocation"]
            tool_name: str = invocation.get("tool_name", "unknown")

            # Add the result header
            formatted_parts.append(f"### Result {i + 1}: {tool_name}")
            # Add the result content - use multi-line code blocks for code outputs
            if "\n" in result["result"]:
                formatted_parts.append(f"```\n{result['result']}\n```")
            else:
                formatted_parts.append(result["result"])
            # Add a separator
            formatted_parts.append("")

        return "\n".join(formatted_parts)

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this batch tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.description)
        async def batch(
            ctx: MCPContext,
            description: Description,
            invocations: Invocations,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(
                ctx, description=description, invocations=invocations
            )
