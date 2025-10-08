# CLI Reference

This document summarizes the core `clodputer` commands and the most common options. Run `clodputer --help` or `clodputer <command> --help` for full argument details.

| Command | Description | Notable Options |
|---------|-------------|-----------------|
| `clodputer init` | Guided onboarding that detects Claude CLI, prepares directories, copies templates, configures automation, runs smoke tests, and logs a transcript. | `--reset` wipes `~/.clodputer/env.json` and `~/.clodputer/onboarding.log` before re-running. |
| `clodputer run <task>` | Executes a task once immediately, respecting the stored configuration. | `--priority {normal,high}`, `--enqueue-only` |
| `clodputer install` | Generates and installs cron entries for scheduled/interval tasks. | `--dry-run` preview the cron section without applying it. |
| `clodputer uninstall` | Removes the Clodputer-managed cron section. | `--dry-run` prints the current section without modifying the crontab. |
| `clodputer schedule-preview <task>` | Shows the next N run times for a scheduled task. | `--count <int>` number of upcoming runs (default 5). |
| `clodputer watch` | Manages the file-watcher service. | `--daemon` start in background, `--stop`, `--status` |
| `clodputer status` | Displays queue health, today’s stats, and recent executions. | – |
| `clodputer logs` | Tails structured execution events. | `--tail <n>`, `--follow`, `--task <name>`, `--json` |
| `clodputer doctor` | Runs diagnostics (queues, tasks, cron, watcher, onboarding state). Exit code is non-zero if any check fails. | – |
| `clodputer template list` / `template export` | Lists packaged templates or copies one into your workspace. | `template export <file> [destination]` |
| `clodputer dashboard` | Launches the interactive curses dashboard. | – |
| `clodputer menu` | Starts the macOS menu bar companion app. | – |
| `clodputer queue` | Shows or clears queued tasks. | `--clear` |

### Tips

- Most commands rely on the state recorded by `clodputer init` (Claude CLI path, onboarding metadata, template copies). Re-run onboarding any time your environment changes.
- Use `clodputer init --reset` if you need to redo onboarding from scratch; this removes the saved CLI path and onboarding transcript before starting the wizard.
- `clodputer doctor` mirrors the summary that onboarding prints at the end of the guided flow. Run it manually whenever you change automation or migrate to a new machine.

For deeper explanations of task configuration, automation, and troubleshooting, see the rest of the [User Guide](README.md#user-documentation).
