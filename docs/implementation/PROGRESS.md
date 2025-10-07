# Clodputer Implementation Progress

**Status**: 🚀 Implementation Starting
**Last Updated**: October 7, 2025
**Current Phase**: Tracer Bullet (Core Executor)

---

## 🎯 Implementation Strategy

Following the **"Tracer Bullet" approach** recommended by expert engineer:
1. Prove core interaction first (Task Executor end-to-end)
2. Build infrastructure around proven core
3. Add `doctor` diagnostics incrementally
4. Use structured logging from the start

---

## Phase 0: Tracer Bullet - Prove Core Interaction

**Goal**: Make `clodputer run <task>` work end-to-end with a single hardcoded task

### Tracer Bullet Checklist

- [ ] **Create minimal Task Executor** (`src/clodputer/executor.py`)
  - [ ] Load a single hardcoded `email-management.yaml` config
  - [ ] Parse YAML with PyYAML
  - [ ] Build `claude -p "..."` command
  - [ ] Execute command with `subprocess.run()`
  - [ ] Capture stdout/stderr
  - [ ] Print captured output to console
  - **Notes**:

- [ ] **Implement PID-tracked cleanup** (`src/clodputer/cleanup.py`)
  - [ ] Get Claude Code process PID from `subprocess.Popen`
  - [ ] Use `psutil.Process(pid).children(recursive=True)` to find all children
  - [ ] Send SIGTERM to parent and all children
  - [ ] Wait 5 seconds
  - [ ] Send SIGKILL to any still running
  - [ ] Log all killed PIDs
  - [ ] Search for orphaned `mcp__*` processes as backup
  - **Notes**:

- [ ] **Create test YAML config** (`test-task.yaml`)
  - [ ] Simple email management task
  - [ ] Uses only Read/Write tools (no MCPs for initial test)
  - [ ] Short, quick execution (< 30 seconds)
  - **Notes**:

- [ ] **Test end-to-end**
  - [ ] Run: `python -m clodputer.executor`
  - [ ] Verify Claude Code executes
  - [ ] Verify output captured
  - [ ] Verify all processes cleaned up (check `ps aux | grep mcp`)
  - [ ] No orphaned processes remain
  - **Notes**:

**✅ Tracer Bullet Complete When**: Can run a task, capture output, and clean up perfectly. This proves the riskiest part works.

---

## Phase 1: Core Implementation

**Goal**: Functional MVP with queue + execution + logging

### 1.1 Repository Setup

- [x] **Initialize repository**
  - [x] Clone repo to local machine
  - [x] Create src-layout directory structure
  - [x] Add pyproject.toml with dependencies
  - [x] Create .gitignore
  - [x] Add planning docs to docs/planning/
  - [x] Initial commit and push
  - **Completed**: October 7, 2025

### 1.2 Queue Manager

- [ ] **Implement QueueManager class** (`src/clodputer/queue.py`)
  - [ ] Load/save queue from JSON file (`~/.clodputer/queue.json`)
  - [ ] Implement atomic writes (temp file + rename)
  - [ ] `enqueue(task_name, priority='normal')` method
  - [ ] `get_next_task()` method (respects priority)
  - [ ] `mark_running(task_id, pid)` method
  - [ ] `mark_completed(task_id, result)` method
  - [ ] `mark_failed(task_id, error)` method
  - [ ] `get_status()` method for display
  - **Notes**:

- [ ] **Implement lockfile mechanism**
  - [ ] Create lock at `~/.clodputer/clodputer.lock` on start
  - [ ] Write current PID to lockfile
  - [ ] Check for stale locks (PID not running)
  - [ ] Clean up lockfile on exit
  - [ ] Handle crashes gracefully
  - **Notes**:

- [ ] **Queue state management**
  - [ ] Define JSON schema for queue.json
  - [ ] Handle queue corruption (validate on load)
  - [ ] Support high/normal priority
  - [ ] Prevent duplicate task IDs
  - **Notes**:

- [ ] **Add `doctor` diagnostic** (incremental)
  - [ ] Check for stale lockfile
  - [ ] Validate queue.json is valid JSON
  - [ ] Check queue state is consistent
  - **Notes**:

### 1.3 Task Executor (Full Implementation)

- [ ] **Config loader** (`src/clodputer/config.py`)
  - [ ] Define Pydantic models for TaskConfig
  - [ ] Load YAML files from `~/.clodputer/tasks/`
  - [ ] Validate with Pydantic
  - [ ] Implement environment variable substitution (`{{ env.VAR }}`)
  - [ ] Handle config errors with clear messages
  - **Notes**:

- [ ] **Executor improvements** (`src/clodputer/executor.py`)
  - [ ] Accept task name instead of hardcoded path
  - [ ] Load config using ConfigLoader
  - [ ] Build Claude Code command with all flags (tools, permissions)
  - [ ] Add timeout support from config
  - [ ] Parse JSON output from Claude Code
  - [ ] Handle execution errors
  - **Notes**:

- [ ] **Integration with queue**
  - [ ] Executor pulls tasks from queue
  - [ ] Updates queue state (running → completed/failed)
  - [ ] Logs all state transitions
  - **Notes**:

- [ ] **Add `doctor` diagnostic** (incremental)
  - [ ] Validate all task YAML files
  - [ ] Check Pydantic validation passes
  - [ ] List tasks with validation errors
  - **Notes**:

### 1.4 Logging System

- [ ] **Implement StructuredLogger** (`src/clodputer/logger.py`)
  - [ ] Log events as JSON lines
  - [ ] Support event types: task_started, task_completed, task_failed
  - [ ] Include timestamp, task_name, duration, status
  - [ ] Write to `~/.clodputer/execution.log`
  - **Notes**:

- [ ] **Log formatting for CLI**
  - [ ] Parse JSON log entries
  - [ ] Format as human-readable output
  - [ ] Color coding (✅ success, ❌ failure)
  - [ ] Support filtering by date/task
  - **Notes**:

- [ ] **Log rotation**
  - [ ] Detect when log exceeds 10 MB
  - [ ] Archive to `~/.clodputer/archive/YYYY-MM.log`
  - [ ] Create fresh log file
  - [ ] Keep archives for 6 months
  - **Notes**:

### 1.5 CLI Interface

- [ ] **CLI framework setup** (`src/clodputer/cli.py`)
  - [ ] Use Click for command structure
  - [ ] Define main `clodputer` group
  - [ ] Add `--version` flag
  - [ ] Add `--help` documentation
  - **Notes**:

- [ ] **Implement `clodputer status`**
  - [ ] Show queue state (running/queued counts)
  - [ ] Show current running task with elapsed time
  - [ ] Show last 10 executions from log
  - [ ] Show stats for today (success/fail counts)
  - **Notes**:

- [ ] **Implement `clodputer logs`**
  - [ ] Display formatted log entries
  - [ ] Support `--tail` for last N entries
  - [ ] Support `--follow` for live updates
  - [ ] Support `--task <name>` for filtering
  - **Notes**:

- [ ] **Implement `clodputer run <task>`**
  - [ ] Enqueue task manually
  - [ ] Support `--priority high` flag
  - [ ] Show confirmation message
  - [ ] Display estimated queue position
  - **Notes**:

- [ ] **Implement `clodputer list`**
  - [ ] List all configured tasks from `~/.clodputer/tasks/`
  - [ ] Show scheduled tasks with cron schedule
  - [ ] Show file watchers with patterns
  - [ ] Show manual-only tasks
  - **Notes**:

- [ ] **Implement `clodputer queue`**
  - [ ] Show detailed queue state
  - [ ] Show all queued tasks with metadata
  - [ ] Show running task details
  - [ ] Support `--clear` to reset queue
  - **Notes**:

- [ ] **Implement `clodputer doctor`**
  - [ ] Run all diagnostic checks
  - [ ] Show ✅/❌ for each check
  - [ ] Provide actionable suggestions for failures
  - [ ] Exit with proper status code
  - **Notes**:

### 1.6 Testing & Validation

- [ ] **Manual testing with real task**
  - [ ] Create `email-management.yaml` config
  - [ ] Run: `clodputer run email-management`
  - [ ] Verify execution works
  - [ ] Verify logging works
  - [ ] Verify cleanup works
  - [ ] Check no orphaned processes
  - **Notes**:

- [ ] **Error handling tests**
  - [ ] Test with invalid YAML
  - [ ] Test with missing environment variables
  - [ ] Test with task timeout
  - [ ] Test with Claude Code crash
  - [ ] Verify graceful error handling
  - **Notes**:

**✅ Phase 1 Complete When**: Can manually run tasks via CLI with proper logging and cleanup.

---

## Phase 2: Automation Triggers

**Goal**: Tasks run automatically via cron and file watchers

### 2.1 Cron Integration

- [ ] **Cron schedule parser** (`src/clodputer/cron.py`)
  - [ ] Parse cron syntax from task configs
  - [ ] Support common formats (daily, hourly, custom)
  - [ ] Validate cron syntax
  - [ ] Handle timezone considerations
  - **Notes**:

- [ ] **Cron entry generator**
  - [ ] Generate cron entries for scheduled tasks
  - [ ] Use `clodputer run <task>` as command
  - [ ] Add error logging to cron output
  - [ ] Support user-specific crontab
  - **Notes**:

- [ ] **Implement `clodputer install`**
  - [ ] Backup existing crontab
  - [ ] Add Clodputer section to crontab
  - [ ] Install all scheduled tasks
  - [ ] Verify installation succeeded
  - [ ] Show installed cron jobs
  - **Notes**:

- [ ] **Implement `clodputer uninstall`**
  - [ ] Remove Clodputer section from crontab
  - [ ] Keep backup of removed entries
  - [ ] Verify removal succeeded
  - **Notes**:

- [ ] **Add `doctor` diagnostic** (incremental)
  - [ ] Check if cron daemon is running
  - [ ] Verify cron jobs are installed
  - [ ] Check cron job syntax
  - **Notes**:

### 2.2 File Watcher

- [ ] **File watcher implementation** (`src/clodputer/watcher.py`)
  - [ ] Use watchdog library for cross-platform watching
  - [ ] Monitor configured directories
  - [ ] Match file patterns (glob)
  - [ ] Debounce file events (wait for writes to complete)
  - [ ] Enqueue tasks when files match
  - **Notes**:

- [ ] **Watcher daemon mode**
  - [ ] Run in background as daemon
  - [ ] Log to `~/.clodputer/watcher.log`
  - [ ] Handle crashes and restarts
  - [ ] PID file for process management
  - **Notes**:

- [ ] **Implement `clodputer watch`**
  - [ ] Start watcher daemon
  - [ ] Support `--daemon` flag for background mode
  - [ ] Support `--stop` to stop daemon
  - [ ] Show watcher status
  - **Notes**:

- [ ] **Add `doctor` diagnostic** (incremental)
  - [ ] Check if watcher daemon is running
  - [ ] Verify watched directories exist
  - [ ] Check file permissions on watched dirs
  - **Notes**:

### 2.3 End-to-End Testing

- [ ] **Test scheduled execution**
  - [ ] Set task to run in 2 minutes via cron
  - [ ] Verify task runs automatically
  - [ ] Check logs show automated execution
  - [ ] Verify cleanup after automated run
  - **Notes**:

- [ ] **Test file watcher**
  - [ ] Configure project file watcher
  - [ ] Drop test file in watched directory
  - [ ] Verify task triggers automatically
  - [ ] Check task receives file path context
  - [ ] Verify file is processed correctly
  - **Notes**:

- [ ] **Test sequential execution**
  - [ ] Queue multiple tasks
  - [ ] Verify only one runs at a time
  - [ ] Verify queue processes in order
  - [ ] Check priority tasks jump queue
  - **Notes**:

**✅ Phase 2 Complete When**: Tasks run automatically via cron and file watchers without manual intervention.

---

## Phase 3: Polish & Release Preparation

**Goal**: Production-ready tool ready for open source release

### 3.1 Menu Bar App

- [ ] **Menu bar app** (`src/clodputer/menubar.py`)
  - [ ] Use rumps for macOS menu bar icon
  - [ ] Show status indicator (🟢 idle, 🔵 running, 🔴 error)
  - [ ] Menu: View Status, Open Dashboard, View Logs
  - [ ] Launch dashboard in terminal
  - **Notes**:

- [ ] **Terminal dashboard** (optional)
  - [ ] Use curses for full-screen display
  - [ ] Show live queue status
  - [ ] Show recent executions
  - [ ] Update in real-time
  - **Notes**:

### 3.2 Error Handling & Polish

- [ ] **Improve error messages**
  - [ ] User-friendly error descriptions
  - [ ] Suggest fixes for common errors
  - [ ] Link to troubleshooting docs
  - **Notes**:

- [ ] **Add recovery mechanisms**
  - [ ] Auto-recover from queue corruption
  - [ ] Handle Claude Code crashes gracefully
  - [ ] Retry failed tasks (optional)
  - **Notes**:

- [ ] **Config validation improvements**
  - [ ] Better Pydantic error messages
  - [ ] Suggest corrections for common mistakes
  - [ ] Validate tool names against available tools
  - **Notes**:

### 3.3 Documentation

- [ ] **User documentation**
  - [ ] Installation guide
  - [ ] Quick start guide
  - [ ] Configuration reference
  - [ ] Troubleshooting guide
  - [ ] FAQ
  - **Notes**:

- [ ] **Developer documentation**
  - [ ] Architecture overview
  - [ ] Contributing guide
  - [ ] Code style guide
  - [ ] Testing guide
  - **Notes**:

- [ ] **Example task configs**
  - [ ] Email management example
  - [ ] Project file processing example
  - [ ] Todo automation example
  - [ ] Add to templates/ directory
  - **Notes**:

### 3.4 Open Source Preparation

- [ ] **Code cleanup**
  - [ ] Add comprehensive docstrings
  - [ ] Add type hints throughout
  - [ ] Remove debug code and TODOs
  - [ ] Format with Black
  - [ ] Lint with Ruff
  - **Notes**:

- [ ] **Testing**
  - [ ] Write unit tests for core components
  - [ ] Write integration tests
  - [ ] Achieve >80% code coverage
  - [ ] Set up CI/CD (GitHub Actions)
  - **Notes**:

- [ ] **Legal & Licensing**
  - [ ] Verify MIT license is appropriate
  - [ ] Add copyright headers to files
  - [ ] Create CONTRIBUTING.md
  - [ ] Create CODE_OF_CONDUCT.md
  - **Notes**:

- [ ] **Release preparation**
  - [ ] Tag v0.1.0 release
  - [ ] Create GitHub release notes
  - [ ] Write announcement blog post
  - [ ] Share on relevant communities
  - **Notes**:

**✅ Phase 3 Complete When**: Project is documented, tested, and ready for public release.

---

## Future Enhancements (Phase 4+)

These are deferred to future releases:

- [ ] Multi-turn conversation support
- [ ] Session pooling for faster execution
- [ ] Advanced retry logic with exponential backoff
- [ ] Cost tracking and budget alerts
- [ ] Web dashboard (alternative to terminal)
- [ ] Cross-platform support (Linux, Windows)
- [ ] Team collaboration features
- [ ] Remote execution capabilities

---

## Notes & Decisions

### Key Technical Decisions

- **Tracer bullet approach**: Prove core interaction first before building infrastructure
- **Structured logging**: JSON internally, formatted for CLI display
- **Incremental `doctor`**: Build diagnostics as we build components
- **PID-tracked cleanup**: Primary method with name-based backup
- **Atomic writes**: All state changes use temp file + rename
- **Environment variables**: Secrets kept out of config files

### Blockers & Issues

_Document any blockers or issues encountered during implementation_

### Performance Observations

_Document any performance metrics or observations_

### Security Considerations

_Document any security findings or considerations_

---

**Last Updated**: October 7, 2025
**Current Focus**: Tracer Bullet - Core Executor
**Next Milestone**: Phase 1 Complete
