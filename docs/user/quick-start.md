# Quick Start

This walkthrough creates a simple automation that drafts email summaries and runs it manually, via cron, and through the file watcher.

## 1. Install & Prepare

1. Follow the [Installation Guide](installation.md).
2. Ensure `~/.clodputer/tasks/` exists.
3. Export your Claude CLI path (if needed):
   ```bash
   export CLODPUTER_CLAUDE_BIN=/Users/you/.claude/local/claude
   export CLODPUTER_EXTRA_ARGS="--dangerously-skip-permissions"
   ```

## 2. Create Your First Task

Create `~/.clodputer/tasks/email-summary.yaml`:

```yaml
name: email-summary
enabled: true
priority: normal

task:
  prompt: |
    Summarise today's unread emails and output a short JSON object:
    {"task": "email-summary", "status": "done", "highlights": "..."}
  allowed_tools:
    - Read
    - Write
    - mcp__gmail
  timeout: 600
```

## 3. Run the Task

```bash
clodputer run email-summary
```

You should see:

- Console output showing a ✅ success message.
- `clodputer status` reporting an idle queue and the recent execution.
- `~/.clodputer/execution.log` containing structured JSON events.

## 4. Schedule with Cron

Add a cron expression:

```yaml
schedule:
  type: cron
  expression: "0 8 * * *"
  timezone: America/Los_Angeles
```

Reinstall cron jobs:

```bash
clodputer install
```

Confirm with `crontab -l`. The job writes output to `~/.clodputer/cron.log`.

## 5. Configure a File Watcher

Add a second task (`~/.clodputer/tasks/inbox-watcher.yaml`):

```yaml
name: inbox-watcher
enabled: true
trigger:
  type: file_watch
  path: ~/WatchedInbox
  pattern: "*.md"
  event: created
  debounce: 500
task:
  prompt: |
    Read the newly added Markdown file and output {"file": "...", "status": "processed"}.
  allowed_tools:
    - Read
    - Write
```

Start the watcher in the background:

```bash
clodputer watch --daemon
```

Dropping a `.md` file into `~/WatchedInbox` should enqueue `inbox-watcher` (check `clodputer queue` and `clodputer status`).

Stop the watcher:

```bash
clodputer watch --stop
```

## 6. Explore the Menu Bar

```bash
clodputer menu
```

- 🟢 idle, 🔵 running, 🔴 error.
- `View Status` shows the current queue.
- `Open Logs` launches the execution log.
- `Launch Dashboard` opens a Terminal window running `clodputer status`.

## 7. Diagnostics

Run `clodputer doctor` anytime to verify configuration, cron, watcher, and queue state.

## 8. Next Steps

- Dive into the [Configuration Reference](configuration.md) for advanced options.
- Read the [Troubleshooting Guide](troubleshooting.md) if you hit issues.
- Browse [templates](../../templates/) for ready-made task definitions including the new
  [`calendar-sync`](../../templates/calendar-sync.yaml) and
  [`todo-triage`](../../templates/todo-triage.yaml) recipes.
