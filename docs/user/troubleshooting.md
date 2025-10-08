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

## Onboarding Issues

### Claude CLI not detected during `clodputer init`

- **Symptom**: `clodputer init` prompts you to enter the Claude CLI path, but it's not automatically detected.
- **Causes**:
  - Claude CLI not in your system PATH
  - Claude CLI installed in a non-standard location
- **Solutions**:
  1. Check if Claude CLI is installed:
     ```bash
     which claude
     ```
  2. If installed but not detected, provide the full path when prompted during `clodputer init`
  3. If not installed, follow the [installation guide](installation.md) to install Claude CLI first
  4. Common installation locations:
     - `~/.claude/local/claude`
     - `/opt/homebrew/bin/claude`
     - `/usr/local/bin/claude`

### Permission errors during setup

- **Symptom**: "Permission denied" errors when creating directories or files
- **Solutions**:
  1. Ensure you have write permissions to your home directory:
     ```bash
     ls -la ~ | grep .clodputer
     ```
  2. If `.clodputer` exists with wrong permissions:
     ```bash
     chmod -R u+w ~/.clodputer
     ```
  3. On macOS, grant Terminal "Full Disk Access" in System Settings > Privacy & Security

### Template import failures

- **Symptom**: Template files not appearing in `~/.clodputer/tasks/` after onboarding
- **Solutions**:
  1. Check if templates were skipped during onboarding - you can import them manually:
     ```bash
     clodputer template list
     clodputer template export <name>
     ```
  2. Verify the tasks directory exists:
     ```bash
     ls -la ~/.clodputer/tasks/
     ```
  3. Re-run onboarding with reset to start fresh:
     ```bash
     clodputer init --reset
     ```

### Cron installation fails on macOS with permission error

- **Symptom**: `clodputer init` fails to install cron jobs with "permission denied" or "Operation not permitted"
- **Cause**: macOS requires explicit permission for cron to access files
- **Solutions**:
  1. Grant Terminal "Full Disk Access" in System Settings > Privacy & Security > Full Disk Access
  2. Restart Terminal after granting permission
  3. Re-run the onboarding:
     ```bash
     clodputer init
     ```
  4. Alternatively, skip cron during onboarding and install manually later:
     ```bash
     clodputer install
     ```

### CLAUDE.md path validation errors

- **Symptom**: Error message "Path must be within your home directory" when providing a CLAUDE.md path
- **Cause**: Security validation prevents paths outside your home directory
- **Solutions**:
  1. Use a path within your home directory (e.g., `~/Documents/CLAUDE.md`)
  2. CLAUDE.md should typically be in your home directory or a subdirectory
  3. Avoid using absolute paths like `/etc/CLAUDE.md` or relative paths with `..`

## Logs & Support Files

| File                               | Purpose                               |
|------------------------------------|---------------------------------------|
| `~/.clodputer/execution.log`       | Structured JSON log (latest state).   |
| `~/.clodputer/cron.log`            | Cron job output.                      |
| `~/.clodputer/watcher.log`         | File watcher daemon output.           |
| `~/.clodputer/backups/`            | Cron backups / archived queue files.  |

When reporting issues, include relevant snippets from these logs. For development discussions, open a GitHub issue with steps to reproduce.
