# Quick Start

This guide walks you from a clean install to a running task in a few minutes using the `clodputer init` onboarding flow.

---

## 1. Prerequisites

- macOS 13+ (Ventura or newer)
- Python 3.9 or later (`python3 --version`)
- Claude Code CLI installed and authenticated (`which claude`)
- Internet access for package installs

Optional:

- Terminal automation permission (`osascript`) for launching the dashboard/menu bar.

---

## 2. Install Clodputer

Pick the method that fits your workflow:

```bash
# PyPI
python3 -m pip install clodputer

# —OR— Homebrew tap
brew tap remyolson/clodputer https://github.com/remyolson/clodputer.git
brew install clodputer
```

Working from source? Clone the repo, create a virtual environment, and run:

```bash
pip install -e ".[dev]"
```

Verify the CLI is reachable:

```bash
clodputer --version
```

---

## 3. Run the Guided Onboarding

```bash
clodputer init
```

The wizard will:

- Detect and validate your Claude CLI installation.
- Create the full `~/.clodputer` directory structure (tasks, logs, archive).
- Copy starter templates on request.
- Offer optional automation setup (cron, file watcher, dashboard/menu launcher).
- Run a smoke test and display a concise doctor summary.

Need to re-run onboarding later? Just execute `clodputer init` again. To wipe the saved state and start fresh, pass `--reset`.

Every run is logged to `~/.clodputer/onboarding.log` for future reference.

---

## 4. Inspect Your Workspace

After onboarding completes you can review what was created:

- `~/.clodputer/tasks/` – task definitions copied or created by the wizard.
- `~/.clodputer/env.json` – persisted Claude CLI path and onboarding metadata.
- `~/.clodputer/onboarding.log` – transcript of the most recent onboarding session.

To list available packaged templates at any point:

```bash
clodputer template list
```

Copy an additional template:

```bash
clodputer template export daily-email.yaml
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
