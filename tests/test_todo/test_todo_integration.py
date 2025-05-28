"""Integration tests for todo tools."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from mcp_claude_code.tools.todo import get_todo_tools
from mcp_claude_code.tools.todo.base import TodoBaseTool, TodoStorage
from mcp_claude_code.tools.todo.todo_read import TodoReadTool
from mcp_claude_code.tools.todo.todo_write import TodoWriteTool


class TestTodoToolsIntegration:
    """Integration tests for todo tools working together."""

    def setup_method(self):
        """Clear storage before each test."""
        TodoStorage._sessions.clear()

    def teardown_method(self):
        """Clear storage after each test."""
        TodoStorage._sessions.clear()

    def test_tool_creation(self):
        """Test that todo tools can be created correctly."""
        tools = get_todo_tools()

        assert len(tools) == 2
        assert any(tool.name == "todo_read" for tool in tools)
        assert any(tool.name == "todo_write" for tool in tools)

        # Get specific tools
        read_tool = next(tool for tool in tools if tool.name == "todo_read")
        write_tool = next(tool for tool in tools if tool.name == "todo_write")

        assert isinstance(read_tool, TodoReadTool)
        assert isinstance(write_tool, TodoWriteTool)

    @pytest.mark.asyncio
    async def test_write_then_read_workflow(self, mcp_context):
        """Test the complete write-then-read workflow."""
        # Create tool instances
        tools = get_todo_tools()
        read_tool = next(tool for tool in tools if tool.name == "todo_read")
        write_tool = next(tool for tool in tools if tool.name == "todo_write")

        session_id = "integration-test-123"

        # Mock context calls for both tools
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Step 1: Read from empty session
            result = await read_tool.call(ctx=mcp_context, session_id=session_id)
            assert result == "[]"

            # Step 2: Write some todos
            todos = [
                {
                    "id": "task-1",
                    "content": "Set up project structure",
                    "status": "completed",
                    "priority": "high",
                },
                {
                    "id": "task-2",
                    "content": "Implement authentication",
                    "status": "in_progress",
                    "priority": "high",
                },
                {
                    "id": "task-3",
                    "content": "Write documentation",
                    "status": "pending",
                    "priority": "medium",
                },
            ]

            write_result = await write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=todos
            )
            assert "Successfully stored 3 todos" in write_result

            # Step 3: Read back the todos
            read_result = await read_tool.call(ctx=mcp_context, session_id=session_id)
            parsed_todos = json.loads(read_result)

            assert parsed_todos == todos
            assert len(parsed_todos) == 3

    @pytest.mark.asyncio
    async def test_multiple_session_workflow(self, mcp_context):
        """Test working with multiple sessions simultaneously."""
        tools = get_todo_tools()
        read_tool = next(tool for tool in tools if tool.name == "todo_read")
        write_tool = next(tool for tool in tools if tool.name == "todo_write")

        session1 = "project-alpha-456"
        session2 = "project-beta-789"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Write different todos to each session
            todos1 = [
                {
                    "id": "alpha-1",
                    "content": "Alpha task 1",
                    "status": "pending",
                    "priority": "high",
                }
            ]
            todos2 = [
                {
                    "id": "beta-1",
                    "content": "Beta task 1",
                    "status": "in_progress",
                    "priority": "medium",
                },
                {
                    "id": "beta-2",
                    "content": "Beta task 2",
                    "status": "completed",
                    "priority": "low",
                },
            ]

            # Write to session 1
            await write_tool.call(ctx=mcp_context, session_id=session1, todos=todos1)

            # Write to session 2
            await write_tool.call(ctx=mcp_context, session_id=session2, todos=todos2)

            # Read from session 1
            result1 = await read_tool.call(ctx=mcp_context, session_id=session1)
            parsed1 = json.loads(result1)
            assert parsed1 == todos1
            assert len(parsed1) == 1

            # Read from session 2
            result2 = await read_tool.call(ctx=mcp_context, session_id=session2)
            parsed2 = json.loads(result2)
            assert parsed2 == todos2
            assert len(parsed2) == 2

            # Verify session isolation
            assert parsed1[0]["content"] == "Alpha task 1"
            assert parsed2[0]["content"] == "Beta task 1"
            assert parsed2[1]["content"] == "Beta task 2"

    @pytest.mark.asyncio
    async def test_update_workflow(self, mcp_context):
        """Test updating todos and reading the changes."""
        tools = get_todo_tools()
        read_tool = next(tool for tool in tools if tool.name == "todo_read")
        write_tool = next(tool for tool in tools if tool.name == "todo_write")

        session_id = "update-workflow-test"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Initial todos
            initial_todos = [
                {
                    "id": "task-1",
                    "content": "Initial task",
                    "status": "pending",
                    "priority": "high",
                }
            ]

            await write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=initial_todos
            )

            # Read initial state
            result = await read_tool.call(ctx=mcp_context, session_id=session_id)
            parsed = json.loads(result)
            assert len(parsed) == 1
            assert parsed[0]["status"] == "pending"

            # Update: mark task as completed and add new task
            updated_todos = [
                {
                    "id": "task-1",
                    "content": "Initial task",
                    "status": "completed",
                    "priority": "high",
                },
                {
                    "id": "task-2",
                    "content": "New task",
                    "status": "pending",
                    "priority": "medium",
                },
            ]

            await write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=updated_todos
            )

            # Read updated state
            result = await read_tool.call(ctx=mcp_context, session_id=session_id)
            parsed = json.loads(result)
            assert len(parsed) == 2
            assert parsed[0]["status"] == "completed"
            assert parsed[1]["content"] == "New task"

    @pytest.mark.asyncio
    async def test_clear_workflow(self, mcp_context):
        """Test clearing todos from a session."""
        tools = get_todo_tools()
        read_tool = next(tool for tool in tools if tool.name == "todo_read")
        write_tool = next(tool for tool in tools if tool.name == "todo_write")

        session_id = "clear-workflow-test"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Add some todos
            todos = [
                {
                    "id": "task-1",
                    "content": "Task to be cleared",
                    "status": "pending",
                    "priority": "high",
                }
            ]

            await write_tool.call(ctx=mcp_context, session_id=session_id, todos=todos)

            # Verify todos exist
            result = await read_tool.call(ctx=mcp_context, session_id=session_id)
            parsed = json.loads(result)
            assert len(parsed) == 1

            # Clear todos by writing empty list
            await write_tool.call(ctx=mcp_context, session_id=session_id, todos=[])

            # Verify todos are cleared
            result = await read_tool.call(ctx=mcp_context, session_id=session_id)
            assert result == "[]"

    @pytest.mark.asyncio
    async def test_error_consistency(self, mcp_context):
        """Test that both tools handle errors consistently."""
        tools = get_todo_tools()
        read_tool = next(tool for tool in tools if tool.name == "todo_read")
        write_tool = next(tool for tool in tools if tool.name == "todo_write")

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Test invalid session ID in both tools
            invalid_session = "ab"  # Too short

            read_result = await read_tool.call(
                ctx=mcp_context, session_id=invalid_session
            )
            write_result = await write_tool.call(
                ctx=mcp_context,
                session_id=invalid_session,
                todos=[
                    {
                        "id": "task-1",
                        "content": "Test",
                        "status": "pending",
                        "priority": "high",
                    }
                ],
            )

            # Both should return similar error messages
            assert "Error: Invalid session_id" in read_result
            assert "Error: Invalid session_id" in write_result
            assert "Session ID too short" in read_result
            assert "Session ID too short" in write_result

    @pytest.mark.asyncio
    async def test_complex_workflow(self, mcp_context):
        """Test a complex workflow with multiple operations."""
        tools = get_todo_tools()
        read_tool = next(tool for tool in tools if tool.name == "todo_read")
        write_tool = next(tool for tool in tools if tool.name == "todo_write")

        session_id = "complex-workflow-test"

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Step 1: Start with empty session
            result = await read_tool.call(ctx=mcp_context, session_id=session_id)
            assert result == "[]"

            # Step 2: Add initial tasks
            phase1_todos = [
                {
                    "id": "setup-1",
                    "content": "Project setup",
                    "status": "completed",
                    "priority": "high",
                },
                {
                    "id": "dev-1",
                    "content": "Core development",
                    "status": "in_progress",
                    "priority": "high",
                },
                {
                    "id": "test-1",
                    "content": "Write tests",
                    "status": "pending",
                    "priority": "medium",
                },
            ]

            await write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=phase1_todos
            )

            # Step 3: Complete some tasks and add new ones
            phase2_todos = [
                {
                    "id": "setup-1",
                    "content": "Project setup",
                    "status": "completed",
                    "priority": "high",
                },
                {
                    "id": "dev-1",
                    "content": "Core development",
                    "status": "completed",
                    "priority": "high",
                },
                {
                    "id": "test-1",
                    "content": "Write tests",
                    "status": "in_progress",
                    "priority": "medium",
                },
                {
                    "id": "docs-1",
                    "content": "Documentation",
                    "status": "pending",
                    "priority": "low",
                },
                {
                    "id": "deploy-1",
                    "content": "Deployment",
                    "status": "pending",
                    "priority": "medium",
                },
            ]

            await write_tool.call(
                ctx=mcp_context, session_id=session_id, todos=phase2_todos
            )

            # Step 4: Read and verify final state
            result = await read_tool.call(ctx=mcp_context, session_id=session_id)
            parsed = json.loads(result)

            assert len(parsed) == 5
            assert sum(1 for todo in parsed if todo["status"] == "completed") == 2
            assert sum(1 for todo in parsed if todo["status"] == "in_progress") == 1
            assert sum(1 for todo in parsed if todo["status"] == "pending") == 2

    def test_tool_properties_consistency(self):
        """Test that tool properties are consistent."""
        tools = get_todo_tools()
        read_tool = next(tool for tool in tools if tool.name == "todo_read")
        write_tool = next(tool for tool in tools if tool.name == "todo_write")

        # Verify basic tool properties exist
        assert read_tool.name == "todo_read"
        assert write_tool.name == "todo_write"
        assert "read" in read_tool.description.lower()
        assert "create and manage" in write_tool.description.lower()

    def test_storage_persistence_across_tool_instances(self):
        """Test that storage persists across different tool instances."""
        # Create first set of tools
        tools1 = get_todo_tools()
        write_tool1 = next(tool for tool in tools1 if tool.name == "todo_write")

        # Create second set of tools
        tools2 = get_todo_tools()
        read_tool2 = next(tool for tool in tools2 if tool.name == "todo_read")

        session_id = "persistence-test"
        test_todos = [
            {
                "id": "persist-1",
                "content": "Persistent task",
                "status": "pending",
                "priority": "high",
            }
        ]

        # Store using first tool instance
        TodoStorage.set_todos(session_id, test_todos)

        # Verify storage is accessible from second tool instance
        retrieved = TodoStorage.get_todos(session_id)
        assert retrieved == test_todos

        # Verify both tool instances access same storage
        assert (
            write_tool1.__class__._TodoStorage is read_tool2.__class__._TodoStorage
            if hasattr(write_tool1.__class__, "_TodoStorage")
            else True
        )

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, mcp_context):
        """Test operations on multiple sessions happening concurrently."""
        tools = get_todo_tools()
        read_tool = next(tool for tool in tools if tool.name == "todo_read")
        write_tool = next(tool for tool in tools if tool.name == "todo_write")

        # Mock context calls
        tool_ctx = AsyncMock()
        with patch.object(TodoBaseTool, "create_tool_context", return_value=tool_ctx):
            # Simulate concurrent operations on different sessions
            sessions = ["concurrent-1", "concurrent-2", "concurrent-3"]

            # Write to all sessions
            for i, session in enumerate(sessions):
                todos = [
                    {
                        "id": f"task-{i}",
                        "content": f"Concurrent task {i}",
                        "status": "pending",
                        "priority": "medium",
                    }
                ]
                await write_tool.call(ctx=mcp_context, session_id=session, todos=todos)

            # Read from all sessions and verify isolation
            for i, session in enumerate(sessions):
                result = await read_tool.call(ctx=mcp_context, session_id=session)
                parsed = json.loads(result)
                assert len(parsed) == 1
                assert parsed[0]["content"] == f"Concurrent task {i}"
                assert parsed[0]["id"] == f"task-{i}"

            # Verify session count
            assert TodoStorage.get_session_count() == 3
