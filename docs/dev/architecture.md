# Architecture Overview

Clodputer is a Python package organised around a sequential task queue. The goal is to run Claude Code tasks safely on macOS using cron schedules and file watcher triggers.

```
┌────────────────────┐
│  YAML Task Configs │  ~/.clodputer/tasks/*.yaml
└────────┬───────────┘
         │
 ┌───────▼────────┐
 │  Config Loader │  (Pydantic validation)
 └───────┬────────┘
         │
 ┌───────▼────────┐
 │   Queue State  │  ~/.clodputer/queue.json (atomic writes)
 │  (QueueManager)│
 └───────┬────────┘
         │
 ┌───────▼────────┐      ┌─────────────────────┐
 │  Task Executor │◄─────┤ Cron / Watcher Trig │
 │ (subprocess +  │      └─────────────────────┘
 │  cleanup)      │
 └───────┬────────┘
         │
 ┌───────▼────────┐
 │ Structured Log │  ~/.clodputer/execution.log
 │ (JSON lines)   │
 └───────┬────────┘
         │
 ┌───────▼────────┐
 │   CLI / Menu   │  Click commands + rumps menubar
 │   Interfaces   │
 └────────────────┘
```

## Key Modules

| Module                    | Responsibility                                                                      |
|---------------------------|--------------------------------------------------------------------------------------|
| `clodputer.config`        | Load and validate YAML configs (Pydantic, env substitution, tool validation).        |
| `clodputer.queue`         | Persistent queue with atomic updates, lockfile management, and corruption recovery.  |
| `clodputer.executor`      | Run Claude CLI commands, parse structured output, handle timeouts/cleanup.          |
| `clodputer.cleanup`       | PID-tracked termination of Claude Code and child MCP processes.                     |
| `clodputer.cron`          | Cron expression validation, install/uninstall helpers, diagnostics.                 |
| `clodputer.watcher`       | Watchdog-based file watcher with daemon mode and queue integration.                 |
| `clodputer.logger`        | JSONL logging, tail helpers, rotation stubs.                                         |
| `clodputer.menubar`       | macOS menu bar app built with rumps.                                                 |
| `clodputer.cli`           | Click-based CLI exposing run/list/status/logs/queue/install/watch/doctor/menu.      |

## Execution Flow

1. **Trigger**: User runs `clodputer run <task>`, cron fires, or the watcher enqueues a task.
2. **Queue Management**: `QueueManager` records the queued item, ensures sequential execution, and recovers from stale lockfiles/corruption.
3. **Execution**:
   - `TaskExecutor` loads the config via `config.load_task_by_name`.
   - Builds the Claude CLI command (respects `CLODPUTER_CLAUDE_BIN`, `allowed_tools`, timeout).
   - Runs subprocess, captures stdout/stderr, parses JSON, logs results, and updates queue state.
   - Cleans up Claude/MCP processes using PID tracking and an orphan sweep.
4. **Logging & Status**:
   - `StructuredLogger` writes events to `~/.clodputer/execution.log`.
   - CLI commands format logs for human consumption (`clodputer status/logs`).
   - The menu bar polls queue/log state for its indicator.

## State Files

| Path                             | Description                                 |
|----------------------------------|---------------------------------------------|
| `~/.clodputer/tasks/`            | Task YAML files.                            |
| `~/.clodputer/queue.json`        | Current queue state (atomic writes).        |
| `~/.clodputer/clodputer.lock`    | PID lock preventing duplicate managers.     |
| `~/.clodputer/execution.log`     | Latest execution summary (JSON lines).      |
| `~/.clodputer/cron.log`          | Cron job output.                            |
| `~/.clodputer/watcher.log`       | File watcher daemon output.                 |
| `~/.clodputer/backups/`          | Cron backups & archived queue files.        |

## Dependencies

- **Click**: CLI entry points.
- **Pydantic 2**: Schema validation with informative error messages.
- **watchdog**: File system events.
- **psutil**: Process inspection/termination.
- **rumps**: Menu bar UI.
- **PyYAML**: Config file parsing.

## Extension Points

- **Task templates** (`templates/`): Seed Claude Code with ready-to-use YAML structures.
- **Context variables**: Extend `TaskSpec.context` for downstream templating.
- **Output handlers**: Extend `on_success`/`on_failure` actions as feature requests arise.
- **Future phases**: Multi-turn sessions, retry policies, Linux support, centralised dashboard.
