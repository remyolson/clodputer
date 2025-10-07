# Installation Guide

Clodputer is currently in active development. Until official packages are published, install it from source using a Python virtual environment.

## Prerequisites

- **macOS 13+** (Ventura or newer)
- **Python 3.9 or later** (`python3 --version`)
- **Claude Code CLI** installed (`which claude`)
- **pip** and **virtualenv** tooling available

## 1. Clone the Repository

```bash
git clone https://github.com/remyolson/clodputer.git
cd clodputer
```

## 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> The commands in this guide assume an activated virtual environment (`(.venv)` prefix).

## 3. Install Clodputer

```bash
pip install -e ".[dev]"
```

This installs both runtime and development dependencies (Click, Pydantic, watchdog, rumps, pytest, ruff, etc.).

## 4. Verify the CLI

```bash
clodputer --version
clodputer doctor
```

- `clodputer --version` prints the current package version.
- `clodputer doctor` runs basic diagnostics (tasks directory, queue integrity, cron/watch status).

## 5. Configure Claude CLI Path

If your Claude CLI binary is not simply `claude` on the PATH, export the location once per shell session:

```bash
export CLODPUTER_CLAUDE_BIN=/Users/you/.claude/local/claude
export CLODPUTER_EXTRA_ARGS="--dangerously-skip-permissions"
```

These environment variables are also recorded in generated cron jobs, so they continue to apply during scheduled runs.

## 6. Create the Tasks Directory

```bash
mkdir -p ~/.clodputer/tasks
```

Place YAML task definitions here (see [Configuration Reference](configuration.md)).

## 7. Optional: Menu Bar App

The menu bar app uses macOS Automation (`osascript`). Grant permission on first launch:

```bash
clodputer menu
```

You should see the Clodputer icon in the menu bar (🟢/🔵/🔴).

## Uninstallation

To remove the editable install:

```bash
pip uninstall clodputer
```

Delete the repository and the `~/.clodputer/` directory if you no longer need local state or archived logs.

---

Next step: follow the [Quick Start Guide](quick-start.md) to create your first automated task.
