# Tutorial: Advanced Prompting and Workflow Management

Welcome to the advanced tutorial for MCP-Claude-Code! This guide will walk you through the new features I've designed to enhance your interaction with Claude 4, focusing on automated prompt generation, project-specific system prompts, and cross-conversational task continuity.

## 1. Introduction: Leveraging Claude 4's Power

The recent updates to this project are built upon the advanced capabilities of Claude 4. To fully harness its potential, I've re-engineered my prompting strategies and tool integrations. This tutorial will show you how to:

- Use dynamically applied system prompts tailored to your project directly from the Claude Desktop UI.
- Employ automated commands to manage conversation context and TODO lists, also accessible via the UI.
- Seamlessly continue tasks across different chat sessions.

The core idea is to make your interaction with Claude more efficient, context-aware, and aligned with your development workflow.

## 2. Essential Setup: Applying Project-Specific System Prompts via UI

The previous method of manually configuring a `doc/system_prompt` file is now deprecated. I've introduced a more dynamic and effective way to provide Claude with the necessary project context at the beginning of each conversation, directly through the Claude Desktop interface.

**Why Project-Specific System Prompts?**
A tailored system prompt gives Claude a better understanding of your project's structure, coding conventions, goals, and any specific constraints. This leads to more relevant and accurate responses.

**How to Apply (Using Claude Desktop UI):**

1.  **Select Your Project:** In Claude Desktop, choose the project you'll be working on (e.g., `mcp-claude-code`).
2.  **Access Registered Prompts:**
    - Once inside your project's chat window, click the **`+`** button (often found near the message input area).
    - From the menu that appears, select the option corresponding to this tool suite (e.g., **"Add from claude-code"** if your MCP server is named `claude-code`).
3.  **Apply the System Prompt:**
    - A submenu will display the available automated prompts I've registered.
    - Choose the **"System prompt for [your-project-name]"** option (e.g., "System prompt for mcp-claude-code").
    - Selecting this will automatically apply the tailored system prompt for your current project to the conversation.

**Best Practice:** Always start new project-related conversations by applying the project-specific system prompt using this UI method. This ensures Claude starts with the optimal context.

## 3. Automated In-Conversation Prompts & Commands (via UI)

The same UI mechanism used for applying system prompts also provides access to several automated commands. These commands trigger specific actions related to context management and task tracking.

To use them:

1.  Click the **`+`** button in your project chat.
2.  Select **"Add from claude-code"** (or your server's name).
3.  Choose the desired automated command from the submenu.

Here are the commands I've made available:

### 3.1. Compress Current Context

- **Purpose:** When a conversation becomes very long, the context window can fill up. This command helps condense the existing conversation while retaining key information.
- **How to Use (UI):** Select "Compact current conversation" from the submenu.
- **Benefit:** Allows for longer, more focused interactions.

### 3.2. Continue Latest TODO

- **Purpose:** This feature is crucial for task continuity. If a session ends or is interrupted before all tasks are completed, this command allows you to quickly pick up where you left off in a new session.
- **How to Use (UI):** Select "Continue latest todo" from the submenu.
- **Benefit:** Ensures that no tasks are forgotten and allows for seamless continuation of work.

### 3.3. Continue TODO by Session ID

- **Purpose:** If you need to refer back to or continue tasks from a specific, known past session, and not just the most recent one.
- **How to Use (UI):** Select "Continue todo by session id" from the submenu. Claude will likely then ask for the specific session ID.
- **Benefit:** Provides granular control over accessing historical task lists. The `session_id` is a timestamp in seconds.

### 3.4. Create a New Release

- **Purpose:** To assist in automating parts of the software release process, such as drafting release notes.
- **How to Use (UI):** Select "Create a new release" from the submenu.
- **Benefit:** Saves time and helps maintain consistency in your release documentation.

### 3.5. System Prompt for [Project] (Recap)

- **Purpose:** As covered in Section 2, this applies the tailored system prompt for your project.
- **How to Use (UI):** Select "System prompt for [your-project-name]" from the submenu.
- **Benefit:** Ensures Claude starts with the best possible understanding of your project.

## 4. Workflow Scenarios: Putting It All Together

Let's look at how these UI-driven features can be combined.

### Scenario A: Starting a New Task in a Project

1.  In Claude Desktop, open your project (e.g., `mcp-claude-code`).
2.  Click `+` -> "Add from claude-code" -> "System prompt for mcp-claude-code" to apply the system prompt.
3.  **You (typing in chat):** "I need to implement a new feature: user authentication. Let's break this down into TODOs."
4.  _(Work proceeds. As you define tasks, you can use the `todo_write` tool, or Claude might use it based on your discussion, to record them. The `CHANGELOG.md` mentions `todo_write` and `todo_read` tools )_

### Scenario B: Continuing an Interrupted Task in a New Conversation

_You had to stop working yesterday, and some TODOs were left unfinished._

1.  Open your project in Claude Desktop.
2.  Apply the project-specific system prompt: Click `+` -> "Add from claude-code" -> "System prompt for mcp-claude-code".
3.  Load unfinished tasks: Click `+` -> "Add from claude-code" -> "Continue latest todo".
4.  _(Claude retrieves and displays the pending tasks from the previous session.)_
5.  **You (typing in chat):** "Okay, let's continue with the first item: 'Implement password hashing'."

### Scenario C: Managing a Very Long Conversation

_You've been discussing a complex module for several hours._

1.  If the context feels too large, compress it: Click `+` -> "Add from claude-code" -> "Compact current conversation".
2.  _(Claude processes and provides a summary or a compressed representation. )_
3.  **You (typing in chat):** "Great, now based on this, let's refine the API for the `OrderProcessor` module."

### Scenario D: Creating Release Notes

_You've completed a sprint and are ready to release a new version._

1.  Open your project in Claude Desktop.
2.  Apply the project-specific system prompt.
3.  Initiate release creation: Click `+` -> "Add from claude-code" -> "Create a new release".
4.  _(Claude might ask for specific commits or use completed TODOs from the recent sessions to draft the notes, based on the logic I implemented in `create_release.py` )_

## 5. Understanding TODO Management Integration

The automated prompt features, especially those related to TODO lists ("Continue latest todo," "Continue todo by session id"), are tightly integrated with the project's TODO management tools (`todo_write` and `todo_read`).

- When you discuss tasks, create plans, or outline steps with Claude, these can be saved as TODO items associated with your current session using the `todo_write` tool (often invoked by Claude based on the conversation).
- The UI commands for retrieving TODOs use `todo_read` to fetch these stored tasks.
- This system ensures that tasks are tracked persistently and can be easily retrieved, even if your conversation with Claude is interrupted or spans multiple sessions. The underlying storage uses session IDs to keep things organized.

## 6. Conclusion

By utilizing the project-specific system prompts and the suite of automated commands—all accessible through the Claude Desktop UI's `+` menu—you can significantly improve your productivity and the quality of interactions with Claude 4. I've designed these tools to make Claude a more intuitive and powerful assistant in your development lifecycle.

Experiment with these features, and adapt them to your personal workflow. Happy coding!
