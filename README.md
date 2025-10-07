# Clodputer

**Autonomous Claude Code Automation System**

[![Status](https://img.shields.io/badge/status-in%20development-yellow)](https://github.com/remyolson/clodputer)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Your AI assistant that works while you sleep.

Clodputer is a lightweight macOS automation framework that enables Claude Code to work autonomously through cron schedules and file watchers.

## ⚠️ Project Status

**Currently in development.** Planning phase complete (A+ grade from expert engineer review). Implementation in progress.

See [docs/planning](docs/planning/) for complete technical specifications and design decisions.

## Quick Overview

**What**: Lightweight automation tool for Claude Code
**Why**: Enable "set it and forget it" automation
**How**: On-demand spawning, sequential queue, aggressive cleanup

### Key Use Cases

- **Daily Email Management**: Draft responses at 8 AM automatically
- **Project Assignment Queue**: Drop project files, Claude executes autonomously
- **Todo List Automation**: Tag tasks with `@claude`, they get done

## Features (Planned)

- ✅ Cron-scheduled tasks
- ✅ File watcher triggers
- ✅ YAML configuration with Pydantic validation
- ✅ PID-tracked process cleanup (prevents MCP leaks)
- ✅ Atomic queue writes (prevents corruption)
- ✅ Secret management (environment variable substitution)
- ✅ Menu bar status indicator
- ✅ `clodputer doctor` diagnostics command
- ✅ Structured JSON logging

## Architecture Highlights

- **Sequential execution**: One task at a time (simple, reliable)
- **Production-grade safety**: PID tracking, atomic writes, backups
- **AI-native design**: Claude Code generates YAML configs
- **macOS-first**: Using native tools (cron, watchdog)

## Documentation

Complete planning documentation available in [docs/planning/](docs/planning/):

- **[00-START-HERE.md](docs/planning/00-START-HERE.md)** - Navigation guide (start here!)
- **[05-finalized-specification.md](docs/planning/05-finalized-specification.md)** - Complete technical spec
- **[10-implementation-details.md](docs/planning/10-implementation-details.md)** - Library choices & code examples
- **[09-safety-features.md](docs/planning/09-safety-features.md)** - Safety mechanisms
- **[SUMMARY.md](docs/planning/SUMMARY.md)** - Executive summary

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

_Coming soon. Will be available via pip/homebrew once Phase 1 is complete._

## Development

This project follows the "tracer bullet" implementation approach:
1. **Days 1-2**: Prove core interaction (Task Executor end-to-end)
2. **Week 1**: Queue manager + logging + CLI
3. **Week 2**: Automation triggers (cron + file watcher)
4. **Week 3**: Polish + open source release

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

_Contribution guidelines coming soon._

## Acknowledgments

Special thanks to the expert engineer who provided comprehensive technical review and feedback throughout the planning phase.

---

**Status**: Planning complete (A+ grade). Implementation starting October 2025.
