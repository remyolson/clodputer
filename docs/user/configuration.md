# Configuration Reference

All tasks live in `~/.clodputer/tasks/*.yaml`. Each file defines one task that can be triggered manually, on a schedule, or via the file watcher.

```yaml
name: example-task
description: Optional human readable summary
enabled: true            # Disable without deleting
priority: normal         # or "high"

schedule:                 # Optional cron trigger
  type: cron
  expression: "0 8 * * *"
  timezone: America/New_York

trigger:                  # Optional file watcher trigger
  type: file_watch
  path: ~/Watched
  pattern: "*.md"
  event: created          # created | modified | deleted
  debounce: 500           # milliseconds

task:
  prompt: |
    Instructions Claude Code executes in a single turn.
  allowed_tools:
    - Read
    - Write
    - mcp__gmail
  disallowed_tools: []
  permission_mode: acceptEdits   # acceptEdits | rejectEdits | prompt
  timeout: 3600                  # seconds
  context:
    output_dir: ~/Reports
  mcp_config: ~/.clodputer/mcp-overrides.json

on_success:
  - log: "{{name}} completed"
  - notify: false

on_failure:
  - log: "{{name}} failed: {{error}}"
  - notify: true
```

## Sections

### Metadata

| Field        | Required | Description                                 |
|--------------|----------|---------------------------------------------|
| `name`       | ✅       | Unique identifier (used by CLI and queue).  |
| `description`| ❌       | Human-readable summary.                     |
| `enabled`    | ✅       | Toggle without deleting the file.           |
| `priority`   | ✅       | `normal` (default) or `high`.               |

### Scheduling (`schedule`)

- `expression` must be valid cron syntax (`*/5 * * * *`, `0 8 * * *`, etc.).
- `timezone` is optional; defaults to system timezone if omitted.
- Use `clodputer install` to rewrite the user crontab. A backup is stored in `~/.clodputer/backups/`.

### File Watcher (`trigger`)

| Field    | Required | Notes                                         |
|----------|----------|-----------------------------------------------|
| `path`   | ✅       | Directory to watch (no recursion in MVP).     |
| `pattern`| ✅       | Glob pattern (`*.md`, `*.json`).              |
| `event`  | ✅       | `created`, `modified`, or `deleted`.          |
| `debounce`| ✅      | Delay between repeated events (ms).           |

Start the watcher in the background with `clodputer watch --daemon`. Logs are stored in `~/.clodputer/watcher.log`.

### Interval Trigger (`trigger.type: interval`)

| Field    | Required | Notes                                                 |
|----------|----------|-------------------------------------------------------|
| `seconds`| ✅       | Must be a multiple of 60 (minimum 60, maximum 86400). |

Interval triggers are converted into cron entries when you run `clodputer install`. Use `clodputer schedule-preview <task>` to see the next occurrences after installation.

### Task Definition (`task`)

- **Prompt** should produce deterministic JSON where possible (easy to parse downstream).
- **Tool validation**:
  - Built-in tools: `Read`, `Write`, `Edit`, `Bash`, `Search`, `Terminal`, `List`, `Delete`, `Code`, `FileSystem`.
  - Custom MCP tools must be prefixed with `mcp__` (e.g., `mcp__gmail`).
  - The loader rejects unknown names with suggestions.
- **Permission mode** mirrors Claude Code CLI.
- **Timeout** is in seconds and defaults to 3600.
- **max_retries** controls automatic retries (default 0).
- **retry_backoff_seconds** multiplies by 2^attempt for exponential backoff.
- **Context** values are injected into prompts using `{{ context.key }}` (manually referenced in your prompt text).
- **Environment variables**: Use `{{ env.VAR_NAME }}`; they must exist in the current shell.

### Handlers (`on_success` / `on_failure`)

Each entry is a small action dictionary. Supported keys:

| Key     | Description                                                          |
|---------|----------------------------------------------------------------------|
| `log`   | Adds a line to the structured log (placeholders like `{{name}}`).   |
| `notify`| macOS notification (`true` or `false`).                              |

Additional keys can be added in future releases.

## Template Library

Ready-made examples live in [`templates/`](../../templates/):

- `daily-email.yaml`: Morning email digest.
- `calendar-sync.yaml`: Sync Google Calendar events into Notion.
- `todo-triage.yaml`: Prioritise tasks whenever `inbox.md` changes.
- `file-watcher.yaml`: Project folder watcher.
- `manual-task.yaml`: Manual or infrequent tasks.

Copy and customise them to speed up onboarding.

## Best Practices

- Keep prompts single-turn, deterministic, and idempotent.
- Use high priority sparingly; all tasks run sequentially.
- Validate with `clodputer doctor` after editing configs.
- Store secrets in environment variables; never commit credentials. See
  [MCP authentication best practices](mcp-authentication.md) for guidance.
- Archive or disable tasks instead of deleting so history remains consistent.

## Global Settings (`~/.clodputer/config.yaml`)

You can tune queue behaviour globally:

```yaml
queue:
  max_parallel: 1          # Reserved for future parallel execution
  cpu_percent: 85          # Defer tasks if CPU usage exceeds this threshold
  memory_percent: 85       # Defer tasks if memory usage exceeds this threshold
```

These defaults are applied automatically if the file is absent.

## Troubleshooting

Common error messages are documented in the [Troubleshooting Guide](troubleshooting.md).
