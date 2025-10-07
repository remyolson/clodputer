# Troubleshooting

This guide highlights common errors and quick fixes. Run `clodputer doctor` after resolving issues to verify the system state.

## CLI Errors

### `Claude CLI not found at 'claude'. Set CLODPUTER_CLAUDE_BIN to the correct executable.`

- Export the binary path:
  ```bash
  export CLODPUTER_CLAUDE_BIN=/Users/you/.claude/local/claude
  ```
- Re-run the command or reinstall cron jobs (`clodputer install`) to capture the new environment.

### `Missing environment variable for placeholder: '{{ env.API_KEY }}'`

- Define the variable in your shell before running Clodputer:
  ```bash
  export API_KEY=your-secret
  ```

### `Validation error in ~/.clodputer/tasks/foo.yaml`

- Errors are listed per field:
  ```
  Validation error in foo.yaml:
    - task.prompt: Field required
    - task.allowed_tools: Unknown allowed_tools: CustomTool. Built-in tools are limited to [...]
  ```
- Fix the indicated field or rename custom MCP tools to use the `mcp__` prefix.

### Queue/Lock Issues

- `clodputer doctor` reports a stale lock:
  ```bash
  clodputer queue --clear
  ```
  or delete `~/.clodputer/clodputer.lock` if no Clodputer processes are running.

- Corrupted queue:
  - The loader automatically moves `queue.json` to `queue.corrupt-YYYYMMDDTHHMMSS` and rebuilds a fresh queue. Review the archived file if you need to recover entries.

## Cron Issues

- Job not firing?
  - Confirm cron is running: `clodputer doctor`.
  - Check `~/.clodputer/cron.log` for errors (exit code 127 usually means missing environment variables).
  - Reinstall with the correct `CLODPUTER_CLAUDE_BIN` exports in place.

- Restore original crontab:
  ```bash
  clodputer uninstall
  crontab path/to/backup.bak   # optional manual restore
  ```

## File Watcher Issues

- Watcher daemon not running:
  ```bash
  clodputer watch --status
  ```
  Use `--daemon` to start in the background or `--stop` to terminate.

- Events not triggering:
  - Ensure the watched directory exists.
  - Confirm the file pattern matches (e.g., `.txt` vs `.md`).
  - Increase `debounce` for large files to avoid premature triggers.

## Menu Bar Issues

- No icon or button unresponsive:
  - Ensure rumps is installed (`pip install -e ".[dev]"`).
  - macOS may require Automation permission for Terminal/Script Editor on first use.

## Logs & Support Files

| File                               | Purpose                               |
|------------------------------------|---------------------------------------|
| `~/.clodputer/execution.log`       | Structured JSON log (latest state).   |
| `~/.clodputer/cron.log`            | Cron job output.                      |
| `~/.clodputer/watcher.log`         | File watcher daemon output.           |
| `~/.clodputer/backups/`            | Cron backups / archived queue files.  |

When reporting issues, include relevant snippets from these logs. For development discussions, open a GitHub issue with steps to reproduce.
