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
- Developer docs: [docs/dev/](docs/dev/) – architecture, testing, contribution, release checklist.
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

```bash
git clone https://github.com/remyolson/clodputer.git
cd clodputer
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Export your Claude CLI path if it is not simply `claude`:

```bash
export CLODPUTER_CLAUDE_BIN=/Users/you/.claude/local/claude
export CLODPUTER_EXTRA_ARGS="--dangerously-skip-permissions"
```

See the [installation guide](docs/user/installation.md) for full details.

## CLI Overview

| Command | Description |
|---------|-------------|
| `clodputer run <task>` | Enqueue (and optionally execute) a task. |
| `clodputer list` | List configured tasks and their triggers. |
| `clodputer status` | Show queue state and recent executions. |
| `clodputer logs` | Tail formatted execution logs. |
| `clodputer queue` | Inspect or clear the task queue. |
| `clodputer install` | Install cron jobs for scheduled tasks. |
| `clodputer uninstall` | Remove Clodputer-managed cron jobs. |
| `clodputer watch` | Manage the file watcher daemon. |
| `clodputer menu` | Launch the macOS menu bar app. |
| `clodputer doctor` | Run diagnostics. |

## First Two Example Runs

The following walkthroughs mirror the templates and workflows defined in the planning package—mostly Phase 1/2 items from [05-finalized-specification.md](docs/planning/05-finalized-specification.md) and [09-safety-features.md](docs/planning/09-safety-features.md).

### Example 1: Daily Email Summary (Scheduled)

1. **Clone & install**
   ```bash
   git clone https://github.com/remyolson/clodputer.git
   cd clodputer
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   export CLODPUTER_CLAUDE_BIN=/Users/you/.claude/local/claude
   export CLODPUTER_EXTRA_ARGS="--dangerously-skip-permissions"
   ```
2. **Seed the task**
   ```bash
   mkdir -p ~/.clodputer/tasks
   cp templates/daily-email.yaml ~/.clodputer/tasks/email-summary.yaml
   ```
   The template aligns with the “Daily Email Management” use case in the planning docs.
3. **Manual smoke test**
   ```bash
   clodputer run email-summary
   clodputer status
   clodputer logs --tail 5
   ```
   Expect a ✅ entry with JSON output recorded in `~/.clodputer/execution.log`.
4. **Install cron automation**
   ```bash
   clodputer install
   crontab -l
   tail -f ~/.clodputer/cron.log
   ```
   Cron output demonstrates the scheduling flow described in [08-installation-and-integration.md](docs/planning/08-installation-and-integration.md).

### Example 2: Project File Watcher (Event-Driven)

1. **Create a watched directory**
   ```bash
   mkdir -p ~/WatchedProjects
   ```
2. **Seed the watcher task**
   ```bash
   cp templates/file-watcher.yaml ~/.clodputer/tasks/project-watcher.yaml
   sed -i '' 's|~/Projects/Inbox|~/WatchedProjects|' ~/.clodputer/tasks/project-watcher.yaml
   ```
3. **Start the watcher**
   ```bash
   clodputer watch --daemon
   clodputer watch --status
   ```
4. **Trigger a file event**
   ```bash
   echo "# New Project" > ~/WatchedProjects/demo.md
   sleep 2
   clodputer queue
   clodputer status
   ```
   You should see the task enqueued with metadata containing the file path—matching the Phase 2 watcher design.
5. **Stop the watcher**
   ```bash
   clodputer watch --stop
   ```

These two flows cover the “Daily Email Management” and “Project Assignment Queue” scenarios from the planning archive, demonstrating how cron and file triggers work end-to-end.

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
