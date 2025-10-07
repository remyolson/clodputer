# Clodputer: Autonomous Claude Code Automation System

**Status**: Planning Phase
**Created**: October 7, 2025
**Goal**: Enable Claude Code to execute tasks autonomously via scheduled jobs and event triggers

---

## Quick Overview

Clodputer is a lightweight automation framework that enables Claude Code to work autonomously. Instead of manually running Claude Code for every task, Clodputer lets you:

- **Schedule tasks** to run automatically (e.g., "draft email responses every morning at 8 AM")
- **Trigger tasks** when files change (e.g., "execute project when new file appears in todo folder")
- **Chain multi-step workflows** with conversation continuity (e.g., "read tasks, execute them sequentially, update status")

Think of it as "cron jobs + file watchers + Claude Code = autonomous AI assistant."

---

## Key Use Cases

### 1. Daily Email Management
- **Trigger**: Cron job at 8:00 AM daily
- **Task**: Read unread emails, draft contextual responses, save to files
- **Value**: Wake up to ready-to-send email drafts every morning

### 2. Project Assignment Queue
- **Trigger**: New markdown file in `~/todos/claude-assignments/`
- **Task**: Read project file, execute tasks, update status in-file
- **Value**: Drop project files in folder, Claude does the work autonomously

### 3. Todo List Automation
- **Trigger**: Todo item tagged with `@claude`
- **Task**: Execute tagged task, update completion status
- **Value**: Farm out tasks to Claude by adding a tag

---

## Planning Documents

**For Engineer Review - Start Here**: [00-START-HERE.md](00-START-HERE.md) ⭐

### Complete Document Index

**Core Planning** (Read First):
- **[00-START-HERE.md](00-START-HERE.md)** - Navigator for engineer review ⭐
- **[SUMMARY.md](SUMMARY.md)** - Executive summary of all decisions
- **[05-finalized-specification.md](05-finalized-specification.md)** - Complete technical spec
- **[10-implementation-details.md](10-implementation-details.md)** - Library choices & repo structure
- **[09-safety-features.md](09-safety-features.md)** - Safety mechanisms (critical)

**User Experience**:
- **[06-user-experience.md](06-user-experience.md)** - Overall UX design (CLI + menu bar)
- **[07-menu-bar-ui.md](07-menu-bar-ui.md)** - Menu bar interface details
- **[08-installation-and-integration.md](08-installation-and-integration.md)** - CLAUDE.md integration

**Supporting**:
- **[CLAUDE-MD-ADDITION.md](CLAUDE-MD-ADDITION.md)** - Text added to CLAUDE.md

**Archive** (Historical/Intermediate):
- Decision-making process docs preserved in `/archive/` for context

**Total**: 10 core documents, ~105KB of final planning documentation

---

## Current Status

**🎉 Planning Complete - Engineer Approved (A+ Grade - Exceptional)**:
- ✅ Research on Claude Code capabilities
- ✅ Analysis of existing tools and frameworks
- ✅ Technical architecture finalized
- ✅ All key decisions made and documented
- ✅ Complete technical specification with implementation details
- ✅ Menu bar UI designed
- ✅ Safety features documented and enhanced
- ✅ Installation process defined
- ✅ **Engineer review completed - "Ready for execution"**
- ✅ **All feedback integrated (PID cleanup, atomic writes, secrets, diagnostics)**

**🚀 Next Phase: Implementation**:
1. Set up new GitHub repository
2. Build Phase 1 MVP (core + cron + file watcher)
3. Test with real use cases (email management, project files)
4. Iterate based on real-world usage
5. Prepare for open source release

**Timeline**: 3 weeks to polished MVP (1 week core + 1 week automation + 1 week polish)

---

## Recommended MVP Scope

Based on research, here's what I recommend for the initial release:

**Included** ✅:
- Cron-scheduled tasks (daily email management)
- File watcher (project assignment queue, using watchdog)
- YAML configuration with Pydantic validation
- JSON output parsing
- Consolidated logging with rotation
- On-demand instance spawning (simple, fault-isolated)
- PID-tracked process cleanup (prevents MCP leaks)
- Atomic queue writes (prevents corruption)
- Secret management (environment variable substitution)
- Menu bar status indicator
- `clodputer doctor` diagnostics command
- macOS-first implementation

**Deferred to Later** ⏸️:
- Multi-turn conversations (validate need first)
- Session pooling (add only if latency is problematic)
- Advanced error handling (retry logic, alerting)
- Cost tracking (manual monitoring initially)
- Web dashboard (CLI-only for MVP)

**Timeline**: 1-2 weeks for functional MVP, 1-2 months for polished open source release.

---

## Why This Approach?

### Simple & Lightweight
- Python + cron, not a heavy framework
- Minimal dependencies (all Python libraries)
- Easy to understand, debug, and extend

### Claude Code Native
- Uses official headless mode API
- Inherits all configured MCP servers automatically
- Leverages session management, tool controls, permissions

### Open Source Ready
- Clear value proposition for community
- Easy installation and setup
- Shareable task templates
- MIT/Apache 2.0 license

### Fills a Gap
- No existing tool does "simple Claude Code automation"
- Proven demand from community discussions
- Not competing with heavy agent frameworks

---

## Key Decisions Made

All architectural and design decisions have been finalized:

✅ **Architecture**: On-demand spawning with sequential queue
✅ **UI**: Menu bar icon with terminal-based dashboard
✅ **Installation**: Homebrew with auto-CLAUDE.md integration
✅ **Execution**: Single-turn tasks (multi-turn in Phase 2)
✅ **Safety**: Multiple layers protecting CLAUDE.md and processes
✅ **Platform**: macOS only for MVP
✅ **Scope**: No cost tracking, no web dashboard in MVP

See [05-finalized-specification.md](05-finalized-specification.md) for complete details.

---

## What Happens Next

**Current Phase: Engineer Review** 📋

1. **Share planning docs** with senior engineer friend
2. **Gather technical feedback** on:
   - CLAUDE.md modification safety
   - Process cleanup strategy
   - Sequential vs. concurrent execution
   - Security model
   - Any other technical concerns

3. **Incorporate feedback** into specifications

**After Review: Implementation** 🔨

4. **Set up repository** and project structure
5. **Build Phase 1 MVP** (core + cron + file watcher)
6. **Test with real use cases** (email management, projects)
7. **Iterate and polish** based on usage
8. **Prepare for open source release**

---

## Research Highlights

**Good News** 🎉:
- Claude Code headless mode is production-ready
- Multi-turn conversations officially supported
- MCP integration works seamlessly
- No direct competitors in this space
- Clear community demand

**What We Need to Build** 🛠️:
- Scheduling layer (cron integration)
- File watching system (watchdog library)
- Task configuration format (YAML)
- Output parsing logic (JSON)
- Menu bar app (rumps library)
- Session management (optional, Phase 2)

**What We Don't Need to Build** ✅:
- Claude Code API (already exists)
- MCP integration (automatic)
- Background task management (native in Claude Code)
- Complex agent orchestration (not the goal)

---

## For Your Engineer Friend

**Start Here**: [00-START-HERE.md](00-START-HERE.md) - Complete review guide

**Critical Items to Review**:
1. CLAUDE.md modification safety ([08-installation-and-integration.md](08-installation-and-integration.md))
2. Process cleanup strategy ([09-safety-features.md](09-safety-features.md))
3. Sequential execution model ([05-finalized-specification.md](05-finalized-specification.md))
4. Security and permissions ([09-safety-features.md](09-safety-features.md))

**All 10 core planning documents ready for review!** 📚

---

**Planning Complete - Ready for Review! 🚀**
