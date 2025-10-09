# Quick Start

This guide walks you from a clean install to running your first task in under 10 minutes using the interactive `clodputer init` onboarding flow.

**What to Expect:**
- ⏱️ **Time**: 5-10 minutes for complete setup
- 🎯 **Goal**: Get Clodputer configured and run a test task
- 🛡️ **Safety**: All setup is guided with validation and backups
- 💡 **Help**: Detailed troubleshooting available at every step

---

## 1. Prerequisites

**Required:**
- macOS 13+ (Ventura or newer)
- Python 3.9 or later - verify with `python3 --version`
- Claude Code CLI installed and authenticated - verify with `which claude`
- pipx (installed in next section if you don't have it)
- Internet access for package installs and task execution

**Optional:**
- Terminal automation permission (`osascript`) for launching the dashboard/menu bar

**Having Issues?**
- See [Troubleshooting Guide](troubleshooting.md) for detailed help with prerequisites
- Common issues: Claude CLI not in PATH, Python version mismatch, permission errors

---

## 2. Install Clodputer

**Using pipx (Recommended):**

```bash
# Install pipx if you don't have it
brew install pipx
pipx ensurepath

# Install clodputer from PyPI
pipx install clodputer

# Verify installation
clodputer --version
```

**Why pipx?**
- Automatic virtualenv isolation (no dependency conflicts)
- Designed specifically for Python CLI applications
- Easy upgrades: `pipx upgrade clodputer`
- Works on macOS, Linux, and Windows
- No need for Xcode Command Line Tools

**Working from source for development?**

Clone the repo, create a virtual environment, and run:

```bash
git clone https://github.com/remyolson/clodputer.git
cd clodputer
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
clodputer --version
```

---

## 3. Run the Guided Onboarding

```bash
clodputer init
```

The interactive wizard will guide you through setup:

**1. Claude CLI Detection**
- Automatically detects your Claude CLI installation
- Validates it works (with timeout protection - won't hang)
- Provides actionable error messages if there are issues

**2. Directory Structure Setup**
- Creates `~/.clodputer/` with tasks, logs, and archive directories
- Sets up state file (`env.json`) with automatic backup/recovery
- All paths validated for security

**3. Intelligent Task Generation (Optional)**
- 🤖 **AI-Powered**: Analyzes your Claude Code MCP setup
- 🎯 **Personalized**: Generates 3 task suggestions tailored to your MCPs
- 📧 **Smart**: Email MCP → email triage tasks, Calendar MCP → meeting prep, etc.
- 🔒 **Safe**: All generated tasks are validated for security (no destructive commands)
- ⚡ **Fast**: 30-60 second generation, or skip to use templates
- **Fallback**: If generation fails or is declined, offers packaged templates instead

**4. CLAUDE.md Update (Optional)**
- If you have a `~/CLAUDE.md` file, offers to add Clodputer guidance
- Shows a diff preview before applying changes
- Creates timestamped backup automatically
- **Note**: Large files (>1MB) will skip diff preview for performance

**5. Automation Setup (Optional)**
- **Cron scheduling**: Set up periodic task execution
- **File watcher**: Monitor directories for changes and trigger tasks
- **Runtime shortcuts**: Add quick aliases for dashboard and menu bar

**6. Smoke Test (Optional)**
- Runs a simple test task to verify your setup works end-to-end
- Checks network connectivity before running (warns if offline)
- Shows clear success/failure status
- Great for catching configuration issues early

**7. Diagnostics Summary**
- Displays health check results for all components
- Reports on task validity, paths, and system readiness

**Need to run onboarding again?**
- `clodputer init` - Re-run onboarding (preserves state)
- `clodputer init --reset` - Wipe state and start completely fresh

**Automatic Features:**
- Every run logged to `~/.clodputer/onboarding.log` (rotates at 10MB, keeps 5 backups)
- State file corruption recovery with automatic backups
- Progress indicators for long-running operations
- All errors include troubleshooting guidance

---

## 4. Inspect Your Workspace

After onboarding completes, review what was created:

**Directory Structure:**
```
~/.clodputer/
├── tasks/              # Your task definitions (YAML files)
├── logs/               # Execution logs and transcripts
├── archive/            # Completed task history
├── env.json           # Persisted Claude CLI path and state
├── env.json.backup    # Automatic backup of state (for recovery)
└── onboarding.log     # Most recent onboarding transcript
```

**State File (`env.json`):**
- Stores Claude CLI path
- Tracks onboarding runs and completion status
- Schema version for future migrations
- Automatically backed up before changes
- Validated on every write to prevent corruption

**Browse Available Templates:**

```bash
# List all packaged templates
clodputer template list

# Export a specific template to your tasks directory
clodputer template export daily-email.yaml

# Export to a custom location
clodputer template export calendar-sync.yaml --destination ~/my-tasks/
```

---

## 5. Run a Task Manually

Execute one of the imported templates to confirm everything works:

```bash
clodputer run <task-name>
```

Use supporting commands to check status:

```bash
clodputer status        # Queue + activity summary
clodputer logs --tail 5 # Recent structured events
clodputer doctor        # Full diagnostics report
```

---

## 6. Enable Automation

If you opted into cron or watcher setup during onboarding you can skip this section—otherwise:

- **Cron**: add/adjust the `schedule` block inside a task YAML, then run `clodputer install`. Preview upcoming runs with `clodputer schedule-preview <task> --count 3`.
- **File watcher**: ensure the `trigger` block is defined, then start monitoring with `clodputer watch --daemon`. Stop it later with `clodputer watch --stop`.

Both automation modes reuse the Claude CLI path and state configured during onboarding—no extra environment variables required.

---

## 7. Explore the UI

- **Terminal dashboard**: `clodputer dashboard`
  - Live queue, metrics, logs, and overlays (`t` task details, `l` log tail, `w` watcher status).
- **Menu bar app**: `clodputer menu`
  - 🟢 idle, 🔵 running, 🔴 error.
  - Quick actions for viewing status, logs, and launching the dashboard.

---

## 8. Diagnostics, Troubleshooting & Cleanup

**Run Diagnostics:**
```bash
clodputer doctor
```
- Validates all task definitions
- Checks cron and watcher configuration
- Verifies paths and queue health
- Reports on Claude CLI accessibility
- **Run this after making configuration changes or if something isn't working**

**Common Issues?**
- Check the **[Troubleshooting Guide](troubleshooting.md)** for comprehensive solutions
- Common topics covered:
  - Claude CLI not detected
  - Permission errors
  - Cron not working on macOS
  - Template import failures
  - Network connectivity issues
  - State file corruption recovery

**Cleanup Commands:**
```bash
# Clear pending jobs (doesn't stop active task)
clodputer queue --clear

# Remove cron entries (temporary disable scheduling)
clodputer uninstall

# Reset onboarding state and start fresh
clodputer init --reset
```

**Getting Help:**
- Always run `clodputer doctor` before reporting issues
- Check `~/.clodputer/onboarding.log` for detailed setup logs
- Review `~/.clodputer/logs/` for task execution logs

---

## 9. Next Steps

- Dive into the [Configuration Reference](configuration.md) for advanced YAML options (context variables, retries, MCP configs).
- Follow the [MCP authentication guide](mcp-authentication.md) to wire external services securely.
- Browse the template catalog under [`templates/`](../../templates/) for ready-made recipes such as
  [`calendar-sync`](../../templates/calendar-sync.yaml) and
  [`todo-triage`](../../templates/todo-triage.yaml).
- Check the [Troubleshooting Guide](troubleshooting.md) if you hit issues, and run `clodputer doctor` before seeking help.

You now have a complete loop: manual execution, scheduled automation, event-driven triggers, monitoring, and diagnostics. Happy automating!
