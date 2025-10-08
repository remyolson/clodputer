# Quick Start

This guide walks through installing Clodputer, creating your first automated task, and exploring the core tooling (cron, file watcher, dashboard).

---

## 1. Prerequisites

- macOS 13+ (Ventura or newer)
- Python 3.9 or later (`python3 --version`)
- Claude Code CLI installed and authenticated (`which claude`)
- Internet access for package installation

Optional but recommended:

- `~/.clodputer/secrets.env` for MCP credentials (see [MCP authentication best practices](mcp-authentication.md)).
- `osascript` permissions for the menu bar dashboard.

---

## 2. Install Clodputer

Pick one of the installation methods:

### PyPI

```bash
python3 -m pip install clodputer
```

### Homebrew tap

```bash
brew tap remyolson/clodputer https://github.com/remyolson/clodputer.git
brew install clodputer
```

### From source (for contributors)

```bash
git clone https://github.com/remyolson/clodputer.git
cd clodputer
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

After installation, point Clodputer at your Claude CLI if it is not simply `claude`:

```bash
export CLODPUTER_CLAUDE_BIN=/Users/you/.claude/local/claude
export CLODPUTER_EXTRA_ARGS="--dangerously-skip-permissions"
```

---

## 3. Bootstrap Your Workspace

1. Create the tasks directory:
   ```bash
   mkdir -p ~/.clodputer/tasks
   ```

2. (Optional) Create the secrets file used by MCP integrations:
   ```bash
   install -m 600 /dev/null ~/.clodputer/secrets.env
   # Example contents
   cat >> ~/.clodputer/secrets.env <<'EOF'
   GMAIL_REFRESH_TOKEN=...
   NOTION_API_KEY=...
   EOF
   ```

3. Copy a starter template. The repository root exposes templates as symlinks for easy browsing:
   ```bash
   cp templates/daily-email.yaml ~/.clodputer/tasks/email-summary.yaml
   ```

The packaged versions live under `src/clodputer/templates/` and ship with the Python package to keep `pip install clodputer` users in sync.

---

## 4. Run Your First Task

Execute the imported template:

```bash
clodputer run email-summary
```

You should see:

- A ✅ status line in the terminal.
- `clodputer status` reporting an idle queue and the recent execution.
- Structured JSON events in `~/.clodputer/execution.log`.

---

## 5. Schedule with Cron

1. Open `~/.clodputer/tasks/email-summary.yaml` and add a schedule:
   ```yaml
   schedule:
     type: cron
     expression: "0 8 * * *"
     timezone: America/Los_Angeles
   ```

2. Install or refresh cron jobs:
   ```bash
   clodputer install
   ```

3. Inspect the crontab section and upcoming runs:
   ```bash
   crontab -l
   clodputer schedule-preview email-summary --count 3
   tail -f ~/.clodputer/cron.log
   ```

---

## 6. Watch a Folder for Changes

1. Create another task (`~/.clodputer/tasks/inbox-watcher.yaml`):
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
       Read the newly added Markdown file and output
       {"file": "...", "status": "processed"}.
     allowed_tools:
       - Read
       - Write
   ```

2. Start the watcher in the background:
   ```bash
   mkdir -p ~/WatchedInbox
   clodputer watch --daemon
   ```

3. Drop a `.md` file into `~/WatchedInbox`. Check activity:
   ```bash
   clodputer queue
   clodputer status
   tail -f ~/.clodputer/watcher.log
   ```

4. Stop the watcher when finished:
   ```bash
   clodputer watch --stop
   ```

---

## 7. Explore the UI

- **Terminal dashboard**: `clodputer dashboard`
  - Live queue, metrics, logs, and overlays (`t` task details, `l` log tail, `w` watcher status).
- **Menu bar app**: `clodputer menu`
  - 🟢 idle, 🔵 running, 🔴 error.
  - Quick actions for viewing status, logs, and launching the dashboard.

---

## 8. Diagnostics & Cleanup

- Run `clodputer doctor` after making configuration changes. It validates tasks, cron, watcher paths, and queue health.
- `clodputer queue --clear` clears pending jobs (does not stop the active task).
- `clodputer uninstall` removes cron entries if you need to disable scheduling temporarily.

---

## 9. Next Steps

- Dive into the [Configuration Reference](configuration.md) for advanced YAML options (context variables, retries, MCP configs).
- Follow the [MCP authentication guide](mcp-authentication.md) to wire external services securely.
- Browse the template catalog under [`templates/`](../../templates/) for ready-made recipes such as
  [`calendar-sync`](../../templates/calendar-sync.yaml) and
  [`todo-triage`](../../templates/todo-triage.yaml).
- Check the [Troubleshooting Guide](troubleshooting.md) if you hit issues, and run `clodputer doctor` before seeking help.

You now have a complete loop: manual execution, scheduled automation, event-driven triggers, monitoring, and diagnostics. Happy automating!
