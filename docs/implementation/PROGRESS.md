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

- [x] **Create minimal Task Executor** (`src/clodputer/executor.py`)
  - [x] Load a single hardcoded `email-management.yaml` config
  - [x] Parse YAML with PyYAML
  - [x] Build `claude -p "..."` command
  - [x] Execute command (implemented with `subprocess.Popen` to support PID capture)
  - [x] Capture stdout/stderr
  - [x] Print captured output to console
  - **Notes**: `python -m clodputer.executor` now runs end-to-end; uses `CLODPUTER_CONFIG_PATH`/`CLODPUTER_CLAUDE_BIN` overrides for flexibility.

- [x] **Implement PID-tracked cleanup** (`src/clodputer/cleanup.py`)
  - [x] Get Claude Code process PID from `subprocess.Popen`
  - [x] Use `psutil.Process(pid).children(recursive=True)` to find all children
  - [x] Send SIGTERM to parent and all children
  - [x] Wait 5 seconds (via `psutil.wait_procs` with a 5s timeout)
  - [x] Send SIGKILL to any still running
  - [x] Log all killed PIDs
  - [x] Search for orphaned `mcp__*` processes as backup
  - **Notes**: Returns a `CleanupReport` summarising terminated/killed/orphaned PIDs and logs the details.

- [x] **Create test YAML config** (`test-task.yaml`)
  - [x] Simple email management task
  - [x] Uses only Read/Write tools (no MCPs for initial test)
  - [x] Short, quick execution (< 30 seconds)
  - **Notes**: Added `email-management.yaml` tracer config at repo root; prompts Claude to emit a single-line JSON summary for deterministic testing.

- [ ] **Test end-to-end**
  - [x] Run: `python -m clodputer.executor`
  - [x] Verify Claude Code executes
  - [x] Verify output captured
  - [x] Verify all processes cleaned up (check `ps aux | grep mcp`)
  - [x] No orphaned processes remain
  - **Notes**: Real Claude CLI run (`CLODPUTER_CLAUDE_BIN=/Users/ro/.claude/local/claude --dangerously-skip-permissions`) produced the expected JSON response and exited cleanly. `ps` only showed pre-existing long-lived Claude/MCP helpers (start times days prior); no new processes remained after execution.

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

- [x] **Implement QueueManager class** (`src/clodputer/queue.py`)
  - [x] Load/save queue from JSON file (`~/.clodputer/queue.json`)
  - [x] Implement atomic writes (temp file + rename)
  - [x] `enqueue(task_name, priority='normal')` method
  - [x] `get_next_task()` method (respects priority)
  - [x] `mark_running(task_id, pid)` method
  - [x] `mark_completed(task_id, result)` method
  - [x] `mark_failed(task_id, error)` method
  - [x] `get_status()` method for display
  - **Notes**: Queue state tracked via dataclasses with UUID task IDs, persisted after every mutation; smoke-tested in an isolated temp directory.

- [x] **Implement lockfile mechanism**
  - [x] Create lock at `~/.clodputer/clodputer.lock` on start
  - [x] Write current PID to lockfile
  - [x] Check for stale locks (PID not running)
  - [x] Clean up lockfile on exit
  - [x] Handle crashes gracefully
  - **Notes**: `QueueManager` auto-acquires the lock and removes stale files; exposes context-manager + `release_lock` for orderly shutdowns.

- [x] **Queue state management**
  - [x] Define JSON schema for queue.json
  - [x] Handle queue corruption (validate on load)
  - [x] Support high/normal priority
  - [x] Prevent duplicate task IDs
  - **Notes**: State serialised with a deterministic schema (`QueueState`); loader raises `QueueCorruptionError` on parse issues and priorities enforced in `_sorted_queue`.

- [x] **Add `doctor` diagnostic** (incremental)
  - [x] Check for stale lockfile
  - [x] Validate queue.json is valid JSON
  - [x] Check queue state is consistent
  - **Notes**: Introduced `lockfile_status()` and `QueueManager.validate_state()` helpers for upcoming `clodputer doctor` integration.

### 1.3 Task Executor (Full Implementation)

- [x] **Config loader** (`src/clodputer/config.py`)
  - [x] Define Pydantic models for TaskConfig
  - [x] Load YAML files from `~/.clodputer/tasks/`
  - [x] Validate with Pydantic
  - [x] Implement environment variable substitution (`{{ env.VAR }}`)
  - [x] Handle config errors with clear messages
  - **Notes**: Added `validate_all_tasks()` for diagnostics and env substitution with clear `ConfigError` reporting.

- [x] **Executor improvements** (`src/clodputer/executor.py`)
  - [x] Accept task name instead of hardcoded path
  - [x] Load config using ConfigLoader
  - [x] Build Claude Code command with all flags (tools, permissions)
  - [x] Add timeout support from config
  - [x] Parse JSON output from Claude Code
  - [x] Handle execution errors
  - **Notes**: `TaskExecutor` now processes queue items, parses fenced JSON, and distinguishes success/timeout/failure while emitting structured logs.

- [x] **Integration with queue**
  - [x] Executor pulls tasks from queue
  - [x] Updates queue state (running → completed/failed)
  - [x] Logs all state transitions
  - **Notes**: Uses `QueueManager` for state transitions and records config/disabled failures via `record_failure`.

- [x] **Add `doctor` diagnostic** (incremental)
  - [x] Validate all task YAML files
  - [x] Check Pydantic validation passes
  - [x] List tasks with validation errors
  - **Notes**: `clodputer doctor` surfaces config errors, lockfile state, and queue validation issues.

### 1.4 Logging System

- [x] **Implement StructuredLogger** (`src/clodputer/logger.py`)
  - [x] Log events as JSON lines
  - [x] Support event types: task_started, task_completed, task_failed
  - [x] Include timestamp, task_name, duration, status
  - [x] Write to `~/.clodputer/execution.log`
  - **Notes**: Rotation kicks in at 10 MB and archives to `~/.clodputer/archive/YYYY-MM.log`.

- [x] **Log formatting for CLI**
  - [x] Parse JSON log entries
  - [x] Format as human-readable output
  - [x] Color coding (✅ success, ❌ failure)
  - [x] Support filtering by date/task
  - **Notes**: `clodputer logs` tail/follow output with task filters; `status` summarises recent history and daily stats.

- [x] **Log rotation**
  - [x] Detect when log exceeds 10 MB
  - [x] Archive to `~/.clodputer/archive/YYYY-MM.log`
  - [x] Create fresh log file
  - [ ] Keep archives for 6 months
  - **Notes**: Archive retention trimming deferred; rotation and archive naming implemented.

### 1.5 CLI Interface

- [x] **CLI framework setup** (`src/clodputer/cli.py`)
  - [x] Use Click for command structure
  - [x] Define main `clodputer` group
  - [x] Add `--version` flag
  - [x] Add `--help` documentation
  - **Notes**: `clodputer` entry point wired via pyproject scripts.

- [x] **Implement `clodputer status`**
  - [x] Show queue state (running/queued counts)
  - [x] Show current running task with elapsed time
  - [x] Show last 10 executions from log
  - [x] Show stats for today (success/fail counts)
  - **Notes**: Handles empty history gracefully; leverages structured log reader.

- [x] **Implement `clodputer logs`**
  - [x] Display formatted log entries
  - [x] Support `--tail` for last N entries
  - [x] Support `--follow` for live updates
  - [x] Support `--task <name>` for filtering
  - **Notes**: Basic follow loop with JSON parsing and task filtering.

- [x] **Implement `clodputer run <task>`**
  - [x] Enqueue task manually
  - [x] Support `--priority high` flag
  - [x] Show confirmation message
  - [x] Display estimated queue position
  - **Notes**: Executes queue immediately unless `--enqueue-only`, reporting outcome.

- [x] **Implement `clodputer list`**
  - [x] List all configured tasks from `~/.clodputer/tasks/`
  - [x] Show scheduled tasks with cron schedule
  - [x] Show file watchers with patterns
  - [x] Show manual-only tasks
  - **Notes**: Displays trigger type, schedule, and file watcher path/pattern details.

- [x] **Implement `clodputer queue`**
  - [x] Show detailed queue state
  - [x] Show all queued tasks with metadata
  - [x] Show running task details
  - [x] Support `--clear` to reset queue
  - **Notes**: Provides elapsed runtime for active task.

- [x] **Implement `clodputer doctor`**
  - [x] Run all diagnostic checks
  - [x] Show ✅/❌ for each check
  - [x] Provide actionable suggestions for failures
  - [x] Exit with proper status code
  - **Notes**: Checks tasks directory, lockfile, queue integrity, config validation, and log readability.

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

- [x] **Cron schedule parser** (`src/clodputer/cron.py`)
  - [x] Parse cron syntax from task configs
  - [x] Support common formats (daily, hourly, custom)
  - [x] Validate cron syntax
  - [x] Handle timezone considerations
  - **Notes**: `validate_cron_expression` validates macros and 5/6-field expressions; timezone applied via `CRON_TZ=` per job.

- [x] **Cron entry generator**
  - [x] Generate cron entries for scheduled tasks
  - [x] Use `clodputer run <task>` as command
  - [x] Add error logging to cron output
  - [x] Support user-specific crontab
  - **Notes**: `generate_cron_section` builds a managed block with log redirection to `~/.clodputer/cron.log`.

- [x] **Implement `clodputer install`**
  - [x] Backup existing crontab
  - [x] Add Clodputer section to crontab
  - [x] Install all scheduled tasks
  - [x] Verify installation succeeded
  - [x] Show installed cron jobs
  - **Notes**: `clodputer install` validates configs, supports `--dry-run`, and writes a backup before updating `crontab`.

- [x] **Implement `clodputer uninstall`**
  - [x] Remove Clodputer section from crontab
  - [x] Keep backup of removed entries
  - [x] Verify removal succeeded
  - **Notes**: `clodputer uninstall` optionally previews the managed block and removes it with backup restoration.

- [x] **Add `doctor` diagnostic** (incremental)
  - [x] Check if cron daemon is running
  - [x] Verify cron jobs are installed
  - [x] Check cron job syntax
  - **Notes**: `doctor` now checks cron daemon presence, ensures scheduled tasks map to installed jobs, and validates cron definitions.

### 2.2 File Watcher

- [x] **File watcher implementation** (`src/clodputer/watcher.py`)
  - [x] Use watchdog library for cross-platform watching
  - [x] Monitor configured directories
  - [x] Match file patterns (glob)
  - [x] Debounce file events (wait for writes to complete)
  - [x] Enqueue tasks when files match
  - **Notes**: `run_watch_service` schedules per-task handlers, respects per-config debounce, and enqueues via `QueueManager` with metadata.

- [x] **Watcher daemon mode**
  - [x] Run in background as daemon
  - [x] Log to `~/.clodputer/watcher.log`
  - [x] Handle crashes and restarts
  - [x] PID file for process management
  - **Notes**: `start_daemon` spawns a multiprocessing process, records PID, and the loop reloads configs on errors with logged retries.

- [x] **Implement `clodputer watch`**
  - [x] Start watcher daemon
  - [x] Support `--daemon` flag for background mode
  - [x] Support `--stop` to stop daemon
  - [x] Show watcher status
  - **Notes**: CLI command handles foreground execution, daemon lifecycle, and status reporting with log path hints.

- [x] **Add `doctor` diagnostic** (incremental)
  - [x] Check if watcher daemon is running
  - [x] Verify watched directories exist
  - [x] Check file permissions on watched dirs
  - **Notes**: `doctor` now validates watcher daemon state, path existence, and log directory availability when file-watch tasks exist.

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
