# CLI Reference

This document summarizes the core `clodputer` commands and the most common options. Run `clodputer --help` or `clodputer <command> --help` for full argument details.

| Command | Description | Notable Options |
|---------|-------------|-----------------|
| `clodputer init` | **Interactive setup wizard** that: (1) detects & validates Claude CLI with timeout protection, (2) creates directory structure with automatic backups, (3) offers template installation, (4) optionally updates CLAUDE.md, (5) configures automation (cron/watcher), (6) runs smoke test with network check, (7) shows diagnostics summary. All logged to `onboarding.log` with rotation. | `--reset` clears all state (`env.json`, logs) and starts completely fresh. |
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

- Most commands rely on state from `clodputer init` (Claude CLI path, directories, templates). Re-run onboarding when your environment changes.
- Use `clodputer init --reset` to completely restart onboarding from scratch - clears all saved state.
- `clodputer doctor` runs the same diagnostics shown at the end of onboarding. **Run this first when troubleshooting issues.**
- All onboarding runs are logged to `~/.clodputer/onboarding.log` (rotates at 10MB, keeps 5 backups).
- State file (`~/.clodputer/env.json`) has automatic backup/recovery - safe from corruption.
- Check the **[Troubleshooting Guide](troubleshooting.md)** for common issues and solutions.

For deeper explanations of task configuration, automation, and troubleshooting, see the rest of the [User Guide](README.md#user-documentation).
