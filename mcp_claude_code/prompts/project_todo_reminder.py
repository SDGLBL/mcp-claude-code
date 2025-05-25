from typing import Any

# Import TodoStorage to access todo data
from mcp_claude_code.tools.todo.base import TodoStorage


PROJECT_TODO_EMPTY_REMINDER = """<system-reminder>This is a reminder that your todo list is currently empty. DO NOT mention this to me explicitly because i have already aware. If you are working on tasks that would benefit from a todo list please use the todo_write tool to create one. If not, please feel free to ignore.</system-reminder>"""


PROJECT_TODO_REMINDER = """<system-reminder>
This is a reminder that you have a to-do list for this project. The to-do list session ID is: {session_id}. You can use the todo_write tool to add new to-dos to the list.

The to-do list is shown below, so you do not need to read it using the todo_read tool before your next time using the todo_write tool:

{todo_list}

</system-reminder>"""


def format_todo_list_concise(todos: list[dict[str, Any]]) -> str:
    """Format a todo list in a concise format for inclusion in prompts.

    Args:
        todos: List of todo items

    Returns:
        Formatted string representation of the todo list
    """
    if not todos:
        return "No todos found."

    formatted_lines = []
    for todo in todos:
        status = todo.get("status", "unknown")
        priority = todo.get("priority", "medium")
        content = todo.get("content", "No content")
        todo_id = todo.get("id", "no-id")

        # Handle empty strings as well as missing values
        if not content or not str(content).strip():
            content = "No content"
        if not todo_id or not str(todo_id).strip():
            todo_id = "no-id"

        # Create status indicator
        status_indicator = {
            "pending": "[ ]",
            "in_progress": "[~]",
            "completed": "[✓]",
        }.get(status, "[?]")

        # Create priority indicator
        priority_indicator = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            priority, "⚪"
        )

        formatted_lines.append(
            f"{status_indicator} {priority_indicator} {content} (id: {todo_id})"
        )

    return "\n".join(formatted_lines)


def has_unfinished_todos(todos: list[dict[str, Any]]) -> bool:
    """Check if there are any unfinished todos in the list.

    Args:
        todos: List of todo items

    Returns:
        True if there are unfinished todos, False otherwise
    """
    if not todos:
        return False

    for todo in todos:
        status = todo.get("status", "pending")
        if status in ["pending", "in_progress"]:
            return True

    return False


def get_project_todo_reminder(session_id: str | None = None) -> str:
    """Get the appropriate todo reminder for a session.

    Args:
        session_id: Session ID to check todos for. If None, finds the latest active session.

    Returns:
        Either PROJECT_TODO_EMPTY_REMINDER or PROJECT_TODO_REMINDER with formatted content
    """
    # If no session_id provided, try to find the latest active session
    if session_id is None:
        session_id = TodoStorage.find_latest_active_session()
        if session_id is None:
            # No active sessions found
            return PROJECT_TODO_EMPTY_REMINDER

    # Get todos for the session
    todos = TodoStorage.get_todos(session_id)

    # Check if we have unfinished todos
    if not has_unfinished_todos(todos):
        return PROJECT_TODO_EMPTY_REMINDER

    # Format the todo list and return the reminder with content
    formatted_todos = format_todo_list_concise(todos)
    return PROJECT_TODO_REMINDER.format(
        session_id=session_id, todo_list=formatted_todos
    )
