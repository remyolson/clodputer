# Installation Guide

Clodputer is currently in active development. The recommended installation method is **pipx**, which handles virtualenv isolation automatically.

## Prerequisites

- **macOS 13+** (Ventura or newer)
- **Python 3.9 or later** (`python3 --version`)
- **Claude Code CLI** installed (`which claude`)
- **pipx** (installation instructions below)

## 1. Install via pipx (Recommended)

### Step 1: Install pipx

If you don't have pipx yet:

```bash
# Using Homebrew
brew install pipx
pipx ensurepath

# Or using pip
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

After installation, restart your terminal or run `source ~/.zshrc` (or `~/.bashrc`) to update your PATH.

### Step 2: Install Clodputer

```bash
# Install from PyPI
pipx install clodputer

# Verify installation
clodputer --version
```

**Why pipx?**
- ✅ Automatic virtualenv isolation (no dependency conflicts)
- ✅ Designed specifically for Python CLI applications
- ✅ Easy upgrades: `pipx upgrade clodputer`
- ✅ Works on macOS, Linux, and Windows
- ✅ No need for Xcode Command Line Tools

### Upgrading

```bash
pipx upgrade clodputer
```

### Uninstalling

```bash
pipx uninstall clodputer
```

## 2. Install from Source (For Development)

Clone the repository when hacking on Clodputer itself:

```bash
git clone https://github.com/remyolson/clodputer.git
cd clodputer
```

### 2.1 Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> The commands in this guide assume an activated virtual environment (`(.venv)` prefix).

### 2.2 Install Clodputer

```bash
pip install -e ".[dev]"
```

This installs both runtime and development dependencies (Click, Pydantic, watchdog, rumps, pytest, ruff, etc.).

### 2.3 Verify the CLI and Run Onboarding

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
  - **🤖 AI-powered task generation** - Analyzes your MCPs and generates personalized task suggestions
  - Offers packaged templates as fallback
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

## 3. Create the Tasks Directory (Optional)

`clodputer init` automatically creates `~/.clodputer/tasks`. Only run the following if you need to pre-create folders in automated scripts:

```bash
mkdir -p ~/.clodputer/tasks
```

Placed YAML task definitions acquire the same schema described in the [Configuration Reference](configuration.md).

## 4. Optional: Menu Bar App

The menu bar app uses macOS Automation (`osascript`). Grant permission on first launch:

```bash
clodputer menu
```

You should see the Clodputer icon in the menu bar (🟢/🔵/🔴).

## Complete Uninstallation

### Remove Clodputer

```bash
# If installed with pipx
pipx uninstall clodputer

# If installed from source
pip uninstall clodputer
```

### Clean Up Data (Optional)

Delete the `~/.clodputer/` directory if you no longer need local state or archived logs:

```bash
rm -rf ~/.clodputer
```

After installing, continue with the [Quick Start Guide](quick-start.md) to explore templates, automation, and the dashboard.
