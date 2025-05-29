"""TodoWrite tool implementation.

This module provides the TodoWrite tool for creating and managing a structured task list for a session.
"""

from typing import Annotated, Literal, TypedDict, Unpack, final, override

from fastmcp import Context as MCPContext
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from pydantic import Field

from mcp_claude_code.tools.todo.base import TodoBaseTool, TodoStorage


class TodoItem(TypedDict):
    """A single todo item."""

    content: Annotated[
        str,
        Field(
            description="Description of the task to be completed",
            min_length=1,
        ),
    ]
    status: Annotated[
        Literal["pending", "in_progress", "completed"],
        Field(description="Current status of the task"),
    ]
    priority: Annotated[
        Literal["high", "medium", "low"],
        Field(description="Priority level of the task"),
    ]
    id: Annotated[
        str,
        Field(description="Unique identifier for the task", min_length=3),
    ]


SessionId = Annotated[
    str | int | float,
    Field(
        description="Unique identifier for the Claude Desktop session (generate using timestamp command)",
    ),
]

Todos = Annotated[
    list[TodoItem],
    Field(
        description="The complete todo list to store for this session",
        min_length=1,
    ),
]


class TodoWriteToolParams(TypedDict):
    """Parameters for the TodoWriteTool.

    Attributes:
        session_id: Unique identifier for the Claude Desktop session (generate using timestamp command)
        todos: The complete todo list to store for this session
    """

    session_id: SessionId
    todos: Todos


@final
class TodoWriteTool(TodoBaseTool):
    """Tool for creating and managing a structured task list for a session."""

    @property
    @override
    def name(self) -> str:
        """Get the tool name.

        Returns:
            Tool name
        """
        return "todo_write"

    @property
    @override
    def description(self) -> str:
        """Get the tool description.

        Returns:
            Tool description
        """
        return """Use this tool to create and manage a structured task list for your current coding session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.
It also helps the user understand the progress of the task and overall progress of their requests.

## When to Use This Tool
Use this tool proactively in these scenarios:

1. Complex multi-step tasks - When a task requires 3 or more distinct steps or actions
2. Non-trivial and complex tasks - Tasks that require careful planning or multiple operations
3. User explicitly requests todo list - When the user directly asks you to use the todo list
4. User provides multiple tasks - When users provide a list of things to be done (numbered or comma-separated)
5. After receiving new instructions - Immediately capture user requirements as todos. Feel free to edit the todo list based on new information.
6. After completing a task - Mark it complete and add any new follow-up tasks
7. When you start working on a new task, mark the todo as in_progress. Ideally you should only have one todo as in_progress at a time. Complete existing tasks before starting new ones.

## When NOT to Use This Tool

Skip using this tool when:
1. There is only a single, straightforward task
2. The task is trivial and tracking it provides no organizational benefit
3. The task can be completed in less than 3 trivial steps
4. The task is purely conversational or informational

NOTE that you should use should not use this tool if there is only one trivial task to do. In this case you are better off just doing the task directly.

## Examples of When to Use the Todo List

<example>
User: I want to add a dark mode toggle to the application settings. Make sure you run the tests and build when you're done!
Assistant: I'll help add a dark mode toggle to your application settings. Let me create a todo list to track this implementation.
*Creates todo list with the following items:*
1. Create dark mode toggle component in Settings page
2. Add dark mode state management (context/store)
3. Implement CSS-in-JS styles for dark theme
4. Update existing components to support theme switching
5. Run tests and build process, addressing any failures or errors that occur
*Begins working on the first task*

<reasoning>
The assistant used the todo list because:
1. Adding dark mode is a multi-step feature requiring UI, state management, and styling changes
2. The user explicitly requested tests and build be run afterward
3. The assistant inferred that tests and build need to pass by adding \"Ensure tests and build succeed\" as the final task
</reasoning>
</example>

<example>
User: Help me rename the function getCwd to getCurrentWorkingDirectory across my project
Assistant: Let me first search through your codebase to find all occurrences of 'getCwd'.
*Uses grep or search tools to locate all instances of getCwd in the codebase*
Assistant: I've found 15 instances of 'getCwd' across 8 different files. Let me create a todo list to track these changes.
*Creates todo list with specific items for each file that needs updating*

<reasoning>
The assistant used the todo list because:
1. First, the assistant searched to understand the scope of the task
2. Upon finding multiple occurrences across different files, it determined this was a complex task with multiple steps
3. The todo list helps ensure every instance is tracked and updated systematically
4. This approach prevents missing any occurrences and maintains code consistency
</reasoning>
</example>


<example>
User: I need to implement these features for my e-commerce site: user registration, product catalog, shopping cart, and checkout flow.
Assistant: I'll help implement these features. First, let's add all the features to the todo list.
*Creates a todo list breaking down each feature into specific tasks based on the project architecture*
Assistant: Let's start with user registration. This will involve creating database models, API endpoints, and frontend forms that integrate with your existing authentication system.

<reasoning>
The assistant used the todo list because:
1. The user provided multiple complex features to implement in a comma separated list
2. The todo list helps organize these large features into manageable tasks
3. This approach allows for tracking progress across the entire implementation
</reasoning>
</example>

<example>
User: Can you help optimize my React application? It's rendering slowly and has performance issues.</user>
Assistant: I'll help optimize your React application. First, let me examine your codebase to identify potential performance bottlenecks.
*Reviews component structure, render patterns, state management, and data fetching*
Assistant: After analyzing your codebase, I've identified several performance issues. Let me create a todo list to track our optimization efforts.
*Creates todo list with items like: 1) Implement memoization for expensive calculations in ProductList, 2) Add virtualization for long lists in Dashboard, 3) Optimize image loading in Gallery component, 4) Fix state update loops in ShoppingCart, 5) Review bundle size and implement code splitting*
Let's start by implementing memoization for the expensive calculations in your ProductList component.</assistant>

<reasoning>
The assistant used the todo list because:
1. First, the assistant examined the codebase to identify specific performance issues
2. Based on this analysis, it identified multiple optimization opportunities
3. Performance optimization is a non-trivial task requiring multiple steps
4. The todo list helps methodically track improvements across different components
5. This systematic approach ensures all performance bottlenecks are addressed
</reasoning>
</example>

## Examples of When NOT to Use the Todo List

<example>
User: How do I print 'Hello World' in Python?
Assistant: In Python, you can print \"Hello World\" with this simple code:

python
print(\"Hello World\")

This will output the text \"Hello World\" to the console when executed.</assistant>

<reasoning>
The assistant did not use the todo list because this is a single, trivial task that can be completed in one step. There's no need to track multiple tasks or steps for such a straightforward request.
</reasoning>
</example>

<example>
User: What does the git status command do?
Assistant: The git status command shows the current state of your working directory and staging area. It displays which changes have been staged, which haven't, and which files aren't being tracked by Git. This is a fundamental command for understanding the current state of your repository before making commits.

<reasoning>
The assistant did not use the todo list because this is an informational request with no actual coding task to complete. The user is simply asking for an explanation, not for the assistant to perform multiple steps or tasks.
</reasoning>
</example>

<example>
User: Can you add a comment to the calculateTotal function to explain what it does?
Assistant: Sure, let me add a comment to the calculateTotal function to explain what it does.
* Uses the Edit tool to add a comment to the calculateTotal function *

<reasoning>
The assistant did not use the todo list because this is a single, straightforward task confined to one location in the code. Adding a comment doesn't require tracking multiple steps or systematic organization.
</reasoning>
</example>

<example>
User: Run npm install for me and tell me what happens.
Assistant: I'll run the npm install command for you.

*Executes: npm install*

The command completed successfully. Here's the output:
[Output of npm install command]

All dependencies have been installed according to your package.json file.

<reasoning>
The assistant did not use the todo list because this is a single command execution with immediate results. There are no multiple steps to track or organize, making the todo list unnecessary for this straightforward task.
</reasoning>
</example>

## Task States and Management

1. **Task States**: Use these states to track progress:
   - pending: Task not yet started
   - in_progress: Currently working on (limit to ONE task at a time)
   - completed: Task finished successfully
   - cancelled: Task no longer needed

2. **Task Management**:
   - Update task status in real-time as you work
   - Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
   - Only have ONE task in_progress at any time
   - Complete current tasks before starting new ones
   - Cancel tasks that become irrelevant

3. **Task Breakdown**:
   - Create specific, actionable items
   - Break complex tasks into smaller, manageable steps
   - Use clear, descriptive task names

When in doubt, use this tool. Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully."""

    @override
    async def call(
        self,
        ctx: MCPContext,
        **params: Unpack[TodoWriteToolParams],
    ) -> str:
        """Execute the tool with the given parameters.

        Args:
            ctx: MCP context
            **params: Tool parameters

        Returns:
            Tool result
        """
        tool_ctx = self.create_tool_context(ctx)
        self.set_tool_context_info(tool_ctx)

        # Extract parameters
        session_id = params.get("session_id")
        todos = params.get("todos")

        # Validate required parameters for direct calls (not through MCP framework)
        if session_id is None:
            await tool_ctx.error("Parameter 'session_id' is required but was None")
            return "Error: Parameter 'session_id' is required but was None"

        if todos is None:
            await tool_ctx.error("Parameter 'todos' is required but was None")
            return "Error: Parameter 'todos' is required but was None"

        session_id = str(session_id)

        # Validate session ID
        is_valid, error_msg = self.validate_session_id(session_id)
        if not is_valid:
            await tool_ctx.error(f"Invalid session_id: {error_msg}")
            return f"Error: Invalid session_id: {error_msg}"

        # Normalize todos list (auto-generate missing fields)
        todos = self.normalize_todos_list(todos)

        # Validate todos list
        is_valid, error_msg = self.validate_todos_list(todos)
        if not is_valid:
            await tool_ctx.error(f"Invalid todos: {error_msg}")
            return f"Error: Invalid todos: {error_msg}"

        await tool_ctx.info(f"Writing {len(todos)} todos for session: {session_id}")

        try:
            # Store todos in memory
            TodoStorage.set_todos(session_id, todos)

            # Log storage stats
            session_count = TodoStorage.get_session_count()
            await tool_ctx.info(
                f"Successfully stored todos. Total active sessions: {session_count}"
            )

            # Provide feedback about the todos
            if todos:
                status_counts = {}
                priority_counts = {}

                for todo in todos:
                    status = todo.get("status", "unknown")
                    priority = todo.get("priority", "unknown")

                    status_counts[status] = status_counts.get(status, 0) + 1
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1

                # Create summary
                summary_parts = []
                if status_counts:
                    status_summary = ", ".join(
                        [f"{count} {status}" for status, count in status_counts.items()]
                    )
                    summary_parts.append(f"Status: {status_summary}")

                if priority_counts:
                    priority_summary = ", ".join(
                        [
                            f"{count} {priority}"
                            for priority, count in priority_counts.items()
                        ]
                    )
                    summary_parts.append(f"Priority: {priority_summary}")

                summary = (
                    f"Successfully stored {len(todos)} todos for session {session_id}.\n"
                    + "; ".join(summary_parts)
                )

                return summary
            else:
                return f"Successfully cleared todos for session {session_id} (stored empty list)."

        except Exception as e:
            await tool_ctx.error(f"Error storing todos: {str(e)}")
            return f"Error storing todos: {str(e)}"

    @override
    def register(self, mcp_server: FastMCP) -> None:
        """Register this todo write tool with the MCP server.

        Creates a wrapper function with explicitly defined parameters that match
        the tool's parameter schema and registers it with the MCP server.

        Args:
            mcp_server: The FastMCP server instance
        """
        tool_self = self  # Create a reference to self for use in the closure

        @mcp_server.tool(name=self.name, description=self.description)
        async def todo_write(
            ctx: MCPContext,
            session_id: SessionId,
            todos: Todos,
        ) -> str:
            ctx = get_context()
            return await tool_self.call(ctx, session_id=session_id, todos=todos)
