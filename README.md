# Clodputer

**Autonomous Claude Code Automation System**

[![Status](https://img.shields.io/badge/status-in%20development-yellow)](https://github.com/remyolson/clodputer)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Your AI assistant that works while you sleep.

Clodputer is a lightweight macOS automation framework that enables Claude Code to work autonomously through cron schedules and file watchers.

## ⚠️ Project Status

**Developer preview.** Core phases (queue, cron, watcher, menu bar) are complete. Installation is source-based while packaging is finalised.

See [docs/planning](docs/planning/) for complete technical specifications and design decisions.

## Quick Overview

**What**: Lightweight automation tool for Claude Code
**Why**: Enable "set it and forget it" automation
**How**: On-demand spawning, sequential queue, aggressive cleanup

### Key Use Cases

- **Daily Email Management**: Draft responses at 8 AM automatically
- **Project Assignment Queue**: Drop project files, Claude executes autonomously
- **Todo List Automation**: Tag tasks with `@claude`, they get done

## Features

- ✅ Sequential task queue with atomic persistence
- ✅ Cron scheduling (`clodputer install` / `uninstall`)
- ✅ File watcher daemon (`clodputer watch`)
- ✅ YAML configuration (Pydantic validation, env substitution)
- ✅ PID-tracked cleanup preventing MCP leaks
- ✅ Structured logging + CLI viewers (`status`, `logs`)
- ✅ macOS menu bar indicator (`clodputer menu`)
- ✅ Diagnostics (`clodputer doctor`)

## Architecture Highlights

- **Sequential execution**: One task at a time (simple, reliable)
- **Production-grade safety**: PID tracking, atomic writes, backups
- **AI-native design**: Claude Code generates YAML configs
- **macOS-first**: Using native tools (cron, watchdog)

## Documentation

- User docs: [docs/user/](docs/user/) – installation, quick start, configuration, troubleshooting.
- Developer docs: [docs/dev/](docs/dev/) – architecture, testing, packaging, release checklist.
- Planning archive: [docs/planning/](docs/planning/) – A+ grade specifications.

## Engineer Review

> "**A+ Plan. This is the Green Light.** The project is exceptionally well-prepared for implementation. The level of detail in your specifications now rivals what I would expect from a seasoned team in a professional environment."

> "My confidence in this project is extremely high. My final recommendation is unequivocal: **Stop planning and start building.**"

— Expert Engineer Review, October 2025

## 🚀 For Engineers: Getting Started

**If you're implementing this project**, start here:

1. **Read**: [CONTRIBUTING.md](CONTRIBUTING.md) - Complete onboarding guide
2. **Follow**: [docs/implementation/PROGRESS.md](docs/implementation/PROGRESS.md) - Implementation tracker
3. **Reference**: [docs/planning/](docs/planning/) - A+ grade technical specifications

**Quick setup**:
```bash
# Install dependencies
pip install -e ".[dev]"

# Read the plan
open docs/planning/00-START-HERE.md

# Start implementing
open docs/implementation/PROGRESS.md
```

**First task**: Complete the "tracer bullet" (Phase 0 in PROGRESS.md) - prove core interaction works end-to-end.

## Installation

### pipx (Recommended)

```bash
# Install pipx if you don't have it
brew install pipx
pipx ensurepath

# Install clodputer
pipx install git+https://github.com/remyolson/clodputer.git

# Verify installation
clodputer --version
```

**Why pipx?** It automatically handles virtualenv isolation and is designed specifically for Python CLI tools. Works on macOS, Linux, and Windows.

### PyPI (Coming Soon)

Once published, installation will be even simpler:

```bash
pipx install clodputer
```

### From Source (For Development)

```bash
git clone https://github.com/remyolson/clodputer.git
cd clodputer
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

See the [installation guide](docs/user/installation.md) for full details. After installation, run `clodputer init` for guided first-time setup.

## CLI Overview

| Command | Description |
|---------|-------------|
| `clodputer init` | Guided onboarding that sets up everything automatically. |
| `clodputer run <task>` | Enqueue (and optionally execute) a task. |
| `clodputer list` | List configured tasks and their triggers. |
| `clodputer status` | Show queue state and recent executions. |
| `clodputer logs` | Tail execution logs (`--json` for raw events). |
| `clodputer queue` | Inspect or clear the task queue. |
| `clodputer install` | Install cron jobs for scheduled tasks. |
| `clodputer uninstall` | Remove Clodputer-managed cron jobs. |
| `clodputer watch` | Manage the file watcher daemon. |
| `clodputer menu` | Launch the macOS menu bar app. |
| `clodputer doctor` | Run diagnostics. |

## Getting Started in 60 Seconds

After installing Clodputer, the guided onboarding sets up everything automatically:

```bash
clodputer init
```

This single command:
- Detects your Claude CLI installation
- Creates all necessary directories (`~/.clodputer/tasks`, `logs`, `archive`)
- Copies starter templates
- Optionally configures cron scheduling and file watching
- Runs a smoke test to verify everything works
- Displays a diagnostics summary

See the [Quick Start Guide](docs/user/quick-start.md) for the complete walkthrough.

### Example Workflows

Once onboarding completes, you can explore these common patterns:

**Daily Email Summary (Scheduled)**
```bash
clodputer template export daily-email.yaml
clodputer run daily-email           # Manual test
clodputer install                    # Enable cron scheduling
clodputer schedule-preview daily-email --count 3
```

**Project File Watcher (Event-Driven)**
```bash
clodputer template export file-watcher.yaml
# Edit ~/.clodputer/tasks/file-watcher.yaml to set your watched directory
clodputer watch --daemon             # Start monitoring
echo "# New Project" > ~/WatchedProjects/demo.md
clodputer status                     # See queued task
clodputer watch --stop               # Stop monitoring
```

These flows demonstrate the "Daily Email Management" and "Project Assignment Queue" scenarios from the planning docs, showing how cron and file triggers work end-to-end.

### Advanced Setup (Manual Configuration)

For users who prefer manual configuration or need to customize beyond what `clodputer init` provides, you can still configure everything by hand:

<details>
<summary>Click to expand manual setup instructions</summary>

1. **Install from source**
   ```bash
   git clone https://github.com/remyolson/clodputer.git
   cd clodputer
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Set environment variables** (optional, only if Claude CLI isn't in your PATH)
   ```bash
   export CLODPUTER_CLAUDE_BIN=/Users/you/.claude/local/claude
   export CLODPUTER_EXTRA_ARGS="--dangerously-skip-permissions"
   ```

3. **Create directories and copy templates**
   ```bash
   mkdir -p ~/.clodputer/tasks
   clodputer template export daily-email.yaml
   ```

4. **Run diagnostics**
   ```bash
   clodputer doctor
   ```

</details>

## Tech Stack

- **Python 3.9+**: Orchestration
- **Click**: CLI framework
- **Pydantic**: Config validation
- **psutil**: Process management (PID-tracked cleanup)
- **watchdog**: File watching
- **rumps**: macOS menu bar
- **PyYAML**: Configuration parsing

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

- Read [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/dev/contributing.md](docs/dev/contributing.md).
- Run `ruff check`, `black`, and `pytest` before submitting PRs.

## Acknowledgments

Special thanks to the expert engineer who provided comprehensive technical review and feedback throughout the planning phase.

---

**Status**: Planning complete (A+ grade). Implementation starting October 2025.
