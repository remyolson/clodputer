# CLAUDE.md Addition for Clodputer

**Add this section to `/Users/ro/CLAUDE.md` once Clodputer is installed**

---

## Clodputer: Autonomous Task Automation

Clodputer enables you to create autonomous tasks that run automatically via cron schedules or file watchers.

### Creating Automated Tasks

When a user asks you to create an automated task (e.g., "I want you to draft email responses every morning at 8 AM"), follow these steps:

1. **Determine task type**:
   - **Scheduled**: Runs on a cron schedule (e.g., daily, hourly)
   - **File-triggered**: Runs when files appear/change in a directory
   - **Manual**: Runs only when explicitly invoked

2. **Create task configuration file** in `~/.clodputer/tasks/[task-name].yaml`

3. **Use this YAML schema**:
```yaml
name: task-name                     # Unique identifier (lowercase, hyphens)
description: Human-readable description
enabled: true                       # Set to false to disable without deleting

# For scheduled tasks:
schedule:
  type: cron
  expression: "0 8 * * *"           # Standard cron expression
  timezone: America/Los_Angeles     # User's timezone

# OR for file-triggered tasks:
trigger:
  type: file_watch
  path: ~/todos/claude-assignments  # Directory to watch
  pattern: "*.md"                   # File pattern to match
  event: created                    # created, modified, or deleted
  debounce: 1000                    # Wait 1s before triggering

# OR for manual tasks:
trigger:
  type: manual

priority: normal                    # normal or high

task:
  prompt: |                         # Single comprehensive prompt
    [Write detailed instructions here]

    Important: This prompt must be self-contained and complete.
    Claude Code will execute this in one go, so include all context.

  allowed_tools:                    # Whitelist of tools
    - Read
    - Write
    - Edit
    - Bash
    - mcp__gmail
    - mcp__google-calendar
    # Add other tools as needed

  permission_mode: acceptEdits      # acceptEdits (auto-approve changes)

  timeout: 3600                     # Max execution time (seconds)

on_success:
  - log: "{{name}} completed successfully"
  - notify: false                   # Don't alert on success

on_failure:
  - log: "{{name}} failed: {{error}}"
  - notify: true                    # Alert user on failure

created: 2025-10-07T11:30:00Z       # ISO 8601 timestamp
created_by: claude-code
```

4. **After creating the config**, tell the user:
   - "I've created the task configuration at ~/.clodputer/tasks/[name].yaml"
   - If scheduled: "Run `clodputer install` to activate the cron job"
   - If file-watch: "Run `clodputer watch --daemon` to start monitoring"
   - "You can test it manually with: `clodputer run [task-name]`"

### Task Prompt Guidelines

**Critical**: Tasks run as single-turn executions. Write prompts that:

✅ **Good prompts**:
- Include all context and instructions in one prompt
- Specify exact file paths and locations
- List all steps to complete
- Include success criteria
- Reference user's preferences (email, writing style, etc.)

❌ **Avoid**:
- Prompts that require follow-up questions
- References to "previous conversation"
- Waiting for user input
- Multi-step workflows that need human approval between steps

**Example - Good Prompt**:
```yaml
prompt: |
  Read all unread emails from the past 24 hours using the Gmail MCP.

  For each email that requires a response:
  1. Search email history with this sender for context
  2. Analyze my writing style from sent emails to this person
  3. Draft a response that:
     - Matches my tone and style
     - Addresses all points raised
     - Is professional but friendly
  4. Save to ~/email-responses/YYYY-MM-DD-[subject-slug].md

  After processing all emails:
  - Move all files from ~/email-responses/ (except today's) to ~/email-responses/archive/
  - Log summary: "Drafted X responses, archived Y old drafts"

  My email: olson.remy@gmail.com
  My writing style: Professional but casual, brief, action-oriented
```

### Common Task Templates

**Daily Email Management**:
```yaml
name: email-management
schedule:
  type: cron
  expression: "0 8 * * *"
task:
  prompt: |
    [Email management prompt as above]
  allowed_tools: [Read, Write, Bash, mcp__gmail]
```

**Project Assignment Watcher**:
```yaml
name: project-assignments
trigger:
  type: file_watch
  path: ~/todos/claude-assignments
  pattern: "*.md"
  event: created
task:
  prompt: |
    A new project file has been created at {{filepath}}.

    1. Read the file to understand the project requirements
    2. Execute each task listed in the file sequentially
    3. As you complete each task, update its status:
       - Change "🟡 pending" to "🔵 in_progress" when starting
       - Change to "🟢 complete" when done
       - Change to "🔴 blocked" if you cannot complete (with reason)
    4. Provide final summary at end of file
  allowed_tools: [Read, Write, Edit, Bash, Grep, Glob]
```

**Weekly Research Summary**:
```yaml
name: weekly-research
schedule:
  type: cron
  expression: "0 9 * * 1"  # Monday at 9 AM
task:
  prompt: |
    Research the following topics and create a summary document:

    Topics:
    - Latest AI/ML developments (papers, tools, news)
    - Claude Code updates and community discussions
    - Relevant business/startup news for Mero

    For each topic:
    1. Search using DuckDuckGo or Google Search MCP
    2. Read top 3-5 articles using Crawl4AI
    3. Summarize key points in 2-3 paragraphs

    Save to: ~/Documents/research-summaries/YYYY-MM-DD-weekly.md

    Format:
    # Weekly Research Summary - [Date]

    ## AI/ML Developments
    [Summary]

    ## Claude Code Updates
    [Summary]

    ## Business News
    [Summary]
  allowed_tools: [Read, Write, mcp__google-search, mcp__crawl4ai]
```

### Clodputer CLI Commands

Users can manage tasks with these commands:

- `clodputer status` - Show running task, queue, recent history
- `clodputer logs` - View execution logs
- `clodputer run <task-name>` - Manually trigger a task
- `clodputer queue` - Show current queue
- `clodputer list` - List all configured tasks
- `clodputer install` - Install cron jobs from configs
- `clodputer watch --daemon` - Start file watchers in background

### Important Notes

1. **Single-turn only**: Tasks execute as one comprehensive prompt. No back-and-forth.

2. **Sequential execution**: Only one task runs at a time. Others wait in queue.

3. **Aggressive cleanup**: Each task spawns fresh Claude Code instance, then kills it + all MCPs.

4. **macOS only**: Clodputer is designed for macOS. Uses native cron and fswatch.

5. **Notifications**: User gets macOS notification only on task failures.

6. **Logs**: Check `~/.clodputer/execution.log` for current status and history.

7. **No cost tracking**: Assume user has Claude Code Max or similar. Tasks fail gracefully if token limits hit.

### When User Asks for Automation

**User**: "I want you to automatically do X every [timeframe]"

**Your Response**:
1. Clarify requirements (what exactly, when, where to save results)
2. Create task config YAML file
3. Explain next steps (install cron, test manually)
4. Offer to create additional tasks if helpful

**Example**:
```
User: "I want you to draft email responses every morning at 8 AM"

Claude: I'll create an automated task for daily email management.

[Creates ~/.clodputer/tasks/email-management.yaml]

I've created the task configuration. Here's what will happen:
- Every day at 8 AM, Clodputer will trigger this task
- It will read your unread emails from the past 24 hours
- Draft responses based on email history and your writing style
- Save drafts to ~/email-responses/YYYY-MM-DD-[subject].md
- Archive old drafts to keep the folder clean

To activate:
1. Run: `clodputer install` (sets up the cron job)
2. Test now: `clodputer run email-management`
3. Check logs: `clodputer logs`

The task will start running automatically tomorrow at 8 AM.
```

### Troubleshooting

If user reports task failures:

1. Check logs: `clodputer logs`
2. Verify task config syntax: `cat ~/.clodputer/tasks/[name].yaml`
3. Test manually: `clodputer run [name]`
4. Check queue: `clodputer queue`
5. Verify cron installed: `crontab -l | grep clodputer`

Common issues:
- **Permission denied**: Check file paths in prompt are accessible
- **MCP not available**: Verify MCP configured in ~/.mcp.json
- **Timeout**: Increase `timeout` in task config
- **Task never runs**: Check cron is installed (`clodputer install`)

---

## Summary

Clodputer lets you create autonomous automation by:
1. Writing comprehensive single-turn prompts
2. Configuring triggers (cron schedule or file watch)
3. Saving as YAML in ~/.clodputer/tasks/
4. Installing with `clodputer install`

Always write self-contained prompts that include full context. Tasks run independently without user interaction.
