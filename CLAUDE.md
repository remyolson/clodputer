# Claude Code Integration Guide for Clodputer

## Overview

Clodputer is designed to be **Claude Code's primary automation tool**. This guide shows you how to programmatically create and manage background tasks during conversations with users.

## Philosophy: Claude Code is the Primary User

When a user asks you to "check my email daily" or "backup my files every night", you should be able to:
1. Create the task programmatically (no YAML editing required)
2. Test it immediately
3. Schedule it for the user
4. All in <30 seconds

## Quick Start: Creating Tasks Programmatically

### Method 1: Quick-Create (Recommended for Simple Tasks)

```bash
# Simple task with name and prompt
clodputer create-task \
  --name daily-email-summary \
  --prompt "Check Gmail and summarize unread emails" \
  --schedule "0 8 * * *" \
  --tools mcp__gmail,Read,Write

# Response (with --format json):
{
  "status": "created",
  "task_id": "daily-email-summary",
  "path": "~/.clodputer/tasks/daily-email-summary.yaml"
}
```

### Method 2: JSON Input (Recommended for Complex Tasks)

```bash
# Create task from JSON
clodputer create-task --json '{
  "name": "advanced-task",
  "enabled": true,
  "priority": "high",
  "schedule": {
    "type": "cron",
    "expression": "0 9 * * *",
    "timezone": "America/Los_Angeles",
    "catch_up": "run_once"
  },
  "task": {
    "prompt": "Complex task with multiple steps...",
    "allowed_tools": ["Read", "Write", "mcp__gmail", "mcp__google-calendar"],
    "timeout": 1800,
    "max_retries": 3
  }
}' --format json
```

### Method 3: Pipe from Generated JSON

```bash
# Generate JSON programmatically, then pipe to create-task
echo '{
  "name": "my-task",
  "task": {"prompt": "Do something useful"}
}' | clodputer create-task --stdin --format json
```

## Task Discovery & Querying

### List All Tasks

```bash
# Get all tasks as JSON
clodputer list --format json

# Filter by status
clodputer list --filter enabled --format json
clodputer list --filter scheduled --format json
```

### Inspect Specific Task

```bash
# Get full task details with metrics
clodputer inspect daily-email-summary --format json

# Response includes:
# - Complete task configuration
# - Execution metrics (success rate, avg duration)
# - Recent run history
```

### Search Tasks

```bash
# Search by keyword in name, description, or prompt
clodputer search "email" --format json
```

## Task Modification

```bash
# Modify schedule
clodputer modify daily-email-summary --schedule "0 9 * * *"

# Add tools
clodputer modify daily-email-summary --add-tool mcp__google-calendar

# Update prompt
clodputer modify daily-email-summary --prompt "New improved prompt text here"

# Multiple changes at once
clodputer modify daily-email-summary \
  --priority high \
  --timeout 1800 \
  --enable \
  --format json
```

## Task State Persistence

Tasks can persist state between runs for incremental processing:

### Set State

```bash
# Set entire state object
clodputer state set daily-email-summary --json '{
  "last_processed_email_id": "msg_12345",
  "processed_count": 50,
  "last_run_summary": "Processed 5 urgent emails"
}'

# Set individual key
clodputer state set daily-email-summary \
  --key last_processed_email_id \
  --value "msg_67890"
```

### Get State

```bash
# Get all state
clodputer state get daily-email-summary --format json

# Get specific key
clodputer state get daily-email-summary --key last_processed_email_id
```

### Use Case: Incremental Email Processing

```bash
# Task prompt can reference state:
# "Process emails newer than {{state.last_processed_email_id}}.
#  Update state with the latest email ID processed."
```

## Execution Results & Health Monitoring

### Get Task Results

```bash
# Get latest execution result
clodputer results daily-email-summary --latest --format json

# Get last 10 executions
clodputer results daily-email-summary --limit 10 --format json
```

### Check System Health

```bash
# Health check for all tasks
clodputer health-check --format json

# Response shows:
# - Tasks with recent failures
# - Last execution status for each task
# - Error details for failed tasks
```

## Example: Complete Workflow

Here's a complete example of Claude Code creating a task during a conversation:

```bash
# User: "Can you check my email every morning and draft responses to urgent messages?"

# Step 1: Check if similar task exists
existing=$(clodputer search "email" --format json)

# Step 2: Create the task
clodputer create-task --json '{
  "name": "daily-email-responses",
  "description": "Check email daily and draft responses to urgent messages",
  "enabled": true,
  "priority": "normal",
  "schedule": {
    "type": "cron",
    "expression": "0 8 * * *",
    "timezone": "America/Los_Angeles"
  },
  "task": {
    "prompt": "Read unread emails from the last 24 hours using Gmail MCP. For urgent messages (marked urgent or from VIP senders), draft appropriate responses. Save drafts using Gmail MCP. Return JSON with summary of actions taken.",
    "allowed_tools": ["mcp__gmail", "Read", "Write"],
    "timeout": 900
  }
}' --format json

# Step 3: Test immediately
clodputer run daily-email-responses

# Step 4: Verify and respond to user
result=$(clodputer results daily-email-responses --latest --format json)
echo "✅ Task 'daily-email-responses' created and tested successfully!"
echo "   It will run every day at 8am Pacific time."
```

## Best Practices for Claude Code

1. **Always use `--format json`** for programmatic parsing
2. **Test tasks immediately** after creation with `clodputer run <task>`
3. **Check existing tasks** before creating to avoid duplicates
4. **Use state persistence** for incremental processing workflows
5. **Monitor task health** periodically with `health-check`
6. **Handle errors gracefully** - tasks may fail, check results before confirming to user

## Common Patterns

### Daily Summary Tasks

```bash
clodputer create-task \
  --name daily-summary \
  --prompt "Summarize today's events from calendar and email" \
  --schedule "0 18 * * *" \
  --tools mcp__gmail,mcp__google-calendar,Read,Write
```

### Incremental Data Processing

```bash
# Task uses state to track progress
clodputer create-task --json '{
  "name": "process-feed",
  "task": {
    "prompt": "Process RSS feed items newer than {{state.last_item_id}}. Update state with latest item ID.",
    "allowed_tools": ["Read", "Write", "WebFetch"]
  }
}'

# Initialize state
clodputer state set process-feed --json '{"last_item_id": null}'
```

### Error Recovery with Retry

```bash
clodputer create-task --json '{
  "name": "api-sync",
  "task": {
    "prompt": "Sync data with external API",
    "max_retries": 3,
    "retry_backoff_seconds": 300
  }
}'
```

## Task Lifecycle Management

```bash
# Create → Test → Monitor → Modify → Health Check

# 1. Create
clodputer create-task --json '{...}'

# 2. Test
clodputer run <task>

# 3. Monitor results
clodputer results <task> --latest --format json

# 4. Modify if needed
clodputer modify <task> --schedule "0 10 * * *"

# 5. Check health periodically
clodputer health-check --format json
```

## Integration with User's CLAUDE.md

This Clodputer integration guide is separate from the user's personal CLAUDE.md file (typically at `~/CLAUDE.md`). When helping users, you can reference both:

- **This file** (`/path/to/clodputer/CLAUDE.md`): Technical API reference for Clodputer
- **User's CLAUDE.md** (`~/CLAUDE.md`): Personal context, preferences, and workflows

## Troubleshooting

### Task Not Running

```bash
# Check if task is enabled
clodputer inspect <task> --format json | jq '.config.enabled'

# Check recent failures
clodputer results <task> --latest --format json

# View system health
clodputer health-check --format json
```

### State Issues

```bash
# View current state
clodputer state get <task> --format json

# Reset state
clodputer state delete <task>

# List all task states
clodputer state list --format json
```

### Execution History

```bash
# Recent executions across all tasks
clodputer logs --tail 20 --json

# Task-specific logs
clodputer logs --task <task-name> --tail 10 --json
```

## API Reference Summary

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `create-task` | Create new task | `--json`, `--name`, `--prompt`, `--schedule` |
| `modify` | Update task config | `--schedule`, `--prompt`, `--add-tool`, `--enable` |
| `list` | List all tasks | `--format json`, `--filter <status>` |
| `inspect` | Get task details | `--format json` |
| `search` | Find tasks by keyword | `--format json` |
| `results` | Get execution results | `--latest`, `--format json` |
| `health-check` | System health status | `--format json` |
| `state get` | Read task state | `--format json`, `--key <name>` |
| `state set` | Write task state | `--json`, `--key <name> --value <val>` |
| `state delete` | Clear task state | `--key <name>` (optional) |
| `run` | Execute task now | `--priority <normal\|high>` |

---

**Key Takeaway**: Claude Code can create, manage, and monitor Clodputer tasks entirely through CLI commands, no YAML editing required. Always use `--format json` for programmatic workflows.
