# Installation Guide

Clodputer is currently in active development. You can install it via PyPI, the
Homebrew tap, or from source.

## Prerequisites

- **macOS 13+** (Ventura or newer)
- **Python 3.9 or later** (`python3 --version`)
- **Claude Code CLI** installed (`which claude`)
- **pip** and **virtualenv** tooling available

## 1. Install from PyPI

```bash
python3 -m pip install clodputer
clodputer --version
```

This is the easiest option if you simply want the CLI.

## 2. Install via Homebrew

```bash
brew tap remyolson/clodputer https://github.com/remyolson/clodputer.git
brew install clodputer
```

Upgrades follow the usual Homebrew workflow (`brew update && brew upgrade clodputer`).

## 3. Install from Source

Clone the repository when hacking on Clodputer itself:

```bash
git clone https://github.com/remyolson/clodputer.git
cd clodputer
```

### 3.1 Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> The commands in this guide assume an activated virtual environment (`(.venv)` prefix).

### 3.2 Install Clodputer

```bash
pip install -e ".[dev]"
```

This installs both runtime and development dependencies (Click, Pydantic, watchdog, rumps, pytest, ruff, etc.).

### 3.3 Verify the CLI and Run Onboarding

```bash
clodputer --version
clodputer doctor
clodputer init        # guided onboarding
```

**What These Commands Do:**

- `clodputer --version` - Verifies the CLI is installed correctly
- `clodputer doctor` - Runs diagnostics: checks directories, queue, cron/watch status, and Claude CLI path
- `clodputer init` - **Interactive setup wizard** that:
  - Detects and validates your Claude CLI (with timeout protection)
  - Creates directory structure with automatic backups
  - Offers template installation
  - Optionally updates your CLAUDE.md with Clodputer guidance
  - Sets up automation (cron, file watcher)
  - Runs a smoke test to verify everything works
  - Provides diagnostics summary

**Re-running Onboarding:**
- `clodputer init` - Preserves existing state, allows you to modify settings
- `clodputer init --reset` - Clears all state and starts completely fresh

**Need Help?**
- See [Troubleshooting Guide](troubleshooting.md) if you encounter issues
- Check `~/.clodputer/onboarding.log` for detailed setup logs

## 4. Create the Tasks Directory (Optional)

`clodputer init` automatically creates `~/.clodputer/tasks`. Only run the following if you need to pre-create folders in automated scripts:

```bash
mkdir -p ~/.clodputer/tasks
```

Placed YAML task definitions acquire the same schema described in the [Configuration Reference](configuration.md).

## 5. Optional: Menu Bar App

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

After installing, continue with the [Quick Start Guide](quick-start.md) to explore templates, automation, and the dashboard.
