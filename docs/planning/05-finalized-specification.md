# Finalized Technical Specification

**Date**: October 7, 2025
**Status**: Ready for Implementation
**Based on**: User input from decision matrix review

---

## Core Decisions Made

### ✅ Architecture: On-Demand with Sequential Queue

**Approach**: Spawn new Claude Code instance per task, but enforce strict sequential execution with proper cleanup.

**Key Requirements**:
1. **Sequential execution only** - No concurrent tasks
2. **Queue management** - Tasks wait their turn
3. **Priority support** - Mark tasks as high/low priority
4. **Complete cleanup** - Shutdown instance + all MCPs after each task
5. **Resource monitoring** - Track and prevent buildup

**Rationale**: Simplicity + reliability. Avoids complexity of persistent sessions while preventing resource exhaustion.

---

### ✅ Conversation Style: Single-Turn (Phase 1)

**Approach**: Each task is a single comprehensive prompt. Multi-turn deferred to Phase 2.

**Implication**: Tasks must be structured as complete instructions that Claude Code can execute from start to finish in one go.

**Example**:
```yaml
# Good: Single comprehensive prompt
prompt: |
  Read all unread emails from past 24 hours.
  For each email requiring response:
  1. Research email history for context
  2. Draft response matching my style
  3. Save to ~/email-responses/YYYY-MM-DD-[subject].md
  Archive old responses to ~/email-responses/archive/

# Avoid: Multi-turn dependencies (for now)
# Step 1: Read emails
# Step 2: (Wait for user to review)
# Step 3: Draft responses
```

---

### ✅ Resource Philosophy: Conservative Sequential

**Limits**:
- **Max concurrent instances**: 1 (strictly sequential)
- **Queue depth**: Unlimited (tasks wait as long as needed)
- **Priority levels**: 2 (normal, high)
- **Scheduling**: Prefer off-hours for daily tasks

**User System**: macOS with moderate resources (will detect automatically)

---

### ✅ Configuration: Simple YAML (AI-Writable)

**Philosophy**: Simple enough for humans to read, structured enough for Claude Code to generate.

**Key Insight**: User will ask Claude Code to create task configs, so they need to be AI-friendly.

**Config Format**:
```yaml
name: email-management
description: Daily email triage and response drafting
enabled: true

schedule:
  type: cron
  expression: "0 8 * * *"  # 8 AM daily
  timezone: America/Los_Angeles

priority: normal  # or "high"

task:
  prompt: |
    [Comprehensive task instructions here]

  allowed_tools:
    - Read
    - Write
    - Bash
    - mcp__gmail

  permission_mode: acceptEdits

  timeout: 3600  # seconds (1 hour)

  on_success:
    - log: "Email management completed"
    - notify: false  # Don't alert on success

  on_failure:
    - log: "Email management failed: {{error}}"
    - notify: true  # Alert immediately on failure
```

---

### ✅ Error Handling: Log + Alert

**Strategy**:
1. **Log everything** to single consolidated log file
2. **Alert immediately** on failures (via terminal notification + log entry)
3. **Clear visibility** - User can quickly see status
4. **No automatic retries** (for now) - User reviews and manually retriggers if needed

**Log Format**:
```
~/.clodputer/execution.log (always overwritten with latest status)

LAST EXECUTION: 2025-10-07 11:30:00
STATUS: ✅ SUCCESS

ACTIVE QUEUE (2 tasks):
  1. 🔵 [RUNNING] email-management (started 11:30:00)
  2. ⏸️ [QUEUED] project-sync (waiting)

RECENT HISTORY (last 10):
  ✅ 2025-10-07 08:00 | email-management | 45s | $0.03
  ✅ 2025-10-06 17:30 | project-sync | 120s | $0.08
  ❌ 2025-10-06 12:00 | todo-automation | Failed: Permission denied on ~/todos/
  ✅ 2025-10-06 08:00 | email-management | 52s | $0.04

TOTAL STATS:
  Tasks today: 3 (2 success, 1 failed)
  Cost today: $0.11
  Uptime: 100% (0 crashes)
```

**Failure Alerts**: macOS notification + log entry with error details

---

### ✅ Target Audience: Claude Code Power Users

**Positioning**: "Autonomous Claude Code: Your AI assistant that works while you sleep"

**Key Messages**:
- Automate repetitive Claude Code workflows
- Schedule daily tasks (email, research, data processing)
- Build your personal AI automation layer
- Open source, local-first, privacy-focused

**Not For**: Non-technical users, enterprise teams (at least not initially)

---

### ✅ Standalone Tool (MVP)

**No external dependencies** beyond:
- Claude Code (obviously)
- System cron (macOS)
- Python 3.9+ (orchestration, includes watchdog for file watching)
- PyYAML (YAML parsing, installed with Clodputer)

**Future integrations** (post-MVP): n8n nodes, GitHub Actions, Zapier, etc.

---

## System Architecture (Finalized)

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    User Interactions                     │
│  - claude code "create email task"                       │
│  - clodputer status                                      │
│  - clodputer logs                                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│               Task Configuration Files                   │
│         ~/.clodputer/tasks/*.yaml                        │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────┐          ┌──────▼────────┐
│  Cron Jobs   │          │ File Watchers │
│  (scheduled) │          │  (fswatch)    │
└───────┬──────┘          └──────┬────────┘
        │                         │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   Task Queue Manager    │
        │  (sequential executor)  │
        │  - Priority handling    │
        │  - Resource monitoring  │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  Claude Code Instance   │
        │  (spawn → execute →     │
        │   shutdown + cleanup)   │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │     MCPs Auto-Loaded    │
        │  (Gmail, Calendar, etc) │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   Results & Logging     │
        │  - Consolidated log     │
        │  - Failure alerts       │
        │  - Cost tracking        │
        └─────────────────────────┘
```

---

## Core Components (Implementation Ready)

### 1. Queue Manager (`clodputer-queue.py`)

**Responsibilities**:
- Maintain task queue in `~/.clodputer/queue.json`
- Enforce sequential execution (max 1 running task)
- Handle priority (high-priority tasks jump queue)
- Monitor running task, cleanup on completion
- Prevent multiple queue managers running simultaneously (lockfile)

**API**:
```python
class QueueManager:
    def enqueue(task_name, priority='normal')
    def get_next_task() -> Task
    def mark_running(task_id)
    def mark_completed(task_id, result)
    def mark_failed(task_id, error)
    def get_status() -> QueueStatus
```

**State Management (Atomic Writes)**:

To prevent queue corruption from crashes during writes, all queue updates use atomic file operations:

```python
def _save_queue(self, queue_data):
    """
    Atomically write queue state to disk.

    Ensures queue.json is always in a valid state, even if process
    crashes mid-write.
    """
    # 1. Write to temporary file
    temp_path = self.queue_file.with_suffix('.tmp')
    temp_path.write_text(json.dumps(queue_data, indent=2))

    # 2. Verify JSON is valid before committing
    json.loads(temp_path.read_text())

    # 3. Atomic rename (replaces old file in single filesystem operation)
    os.rename(temp_path, self.queue_file)
```

**Why atomic?** `os.rename()` is an atomic operation on POSIX systems. If the process crashes during step 1 or 2, the original `queue.json` remains intact. Only after verification does step 3 replace the file in a single, indivisible operation.

**Queue File Format** (`~/.clodputer/queue.json`):
```json
{
  "running": {
    "id": "task-123",
    "name": "email-management",
    "started_at": "2025-10-07T11:30:00Z",
    "pid": 12345
  },
  "queued": [
    {
      "id": "task-124",
      "name": "project-sync",
      "priority": "normal",
      "queued_at": "2025-10-07T11:31:00Z"
    }
  ]
}
```

---

### 2. Task Executor (`clodputer-run.py`)

**Responsibilities**:
- Load task config from YAML
- Construct `claude -p` command with proper flags
- Execute Claude Code instance
- Parse JSON output
- Cleanup: kill process, ensure MCPs shutdown
- Update queue status
- Log results

**Execution Flow**:
```python
def execute_task(task_config_path):
    # 1. Load config
    config = load_yaml(task_config_path)

    # 2. Build command
    cmd = build_claude_command(config)

    # 3. Execute with timeout
    result = subprocess.run(cmd,
                          timeout=config.timeout,
                          capture_output=True)

    # 4. Parse output
    output = json.loads(result.stdout)

    # 5. Cleanup (kill process tree, verify MCP shutdown)
    cleanup_claude_instance(result.pid)

    # 6. Log results
    log_execution(config.name, output)

    # 7. Alert on failure
    if output['is_error']:
        send_notification(f"Task failed: {config.name}")

    return output
```

---

### 3. Cron Integration (`clodputer-cron.py`)

**Responsibilities**:
- Parse all task configs for scheduled tasks
- Generate cron entries
- Install/uninstall cron jobs
- Handle timezone conversions

**Generated Cron Entry**:
```bash
# Clodputer: email-management
0 8 * * * /usr/local/bin/clodputer-enqueue email-management >> ~/.clodputer/cron.log 2>&1
```

**Note**: `clodputer-enqueue` adds task to queue, doesn't execute directly

---

### 4. File Watcher (`clodputer-watch.py`)

**Responsibilities**:
- Monitor directories for file changes using `watchdog` library
- Match file patterns to task triggers
- Enqueue tasks when conditions met
- Debounce rapid changes (1 second delay)
- Track processed files to avoid double-triggering

**Watched Patterns**:
```yaml
# In task config
trigger:
  type: file_watch
  path: ~/todos/claude-assignments
  pattern: "*.md"
  event: created  # created, modified, deleted
  debounce: 1000  # milliseconds
```

**Implementation** (using watchdog):
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TaskTriggerHandler(FileSystemEventHandler):
    def __init__(self, task_name, pattern):
        self.task_name = task_name
        self.pattern = pattern
        self.processed = set()

    def on_created(self, event):
        if event.is_directory:
            return

        filepath = Path(event.src_path)
        if filepath.match(self.pattern) and filepath not in self.processed:
            self.processed.add(filepath)
            enqueue_task(self.task_name, context={'filepath': str(filepath)})

def watch_directory(watch_config):
    handler = TaskTriggerHandler(watch_config.task_name, watch_config.pattern)
    observer = Observer()
    observer.schedule(handler, watch_config.path, recursive=False)
    observer.start()
```

---

### 5. Logging System (`clodputer-log.py`)

**Responsibilities**:
- Maintain single consolidated log file (always current)
- Track execution history (last 10 runs)
- Calculate daily stats (cost, success rate)
- Format for human readability

**Log Location**: `~/.clodputer/execution.log` (overwritten on each update)

**Archive**: `~/.clodputer/archive/YYYY-MM.log` (monthly archives for history)

---

### 6. CLI Interface (`clodputer`)

**Commands**:
```bash
# View status
clodputer status
  # Shows: running task, queue depth, recent history

# View logs
clodputer logs
  # Tail the consolidated log

# Enqueue task manually
clodputer run <task-name> [--priority high]
  # Add task to queue immediately

# List available tasks
clodputer list
  # Show all task configs

# Install cron jobs
clodputer install
  # Set up cron jobs from configs

# Start file watchers
clodputer watch [--daemon]
  # Start file watchers (or as background daemon)

# View queue
clodputer queue
  # Show current queue state

# Clear queue
clodputer clear
  # Remove all queued tasks (not running task)

# System info
clodputer info
  # Show system resources, Claude Code version, MCP status
```

---

## File Structure

```
~/.clodputer/
├── tasks/                          # Task configuration files
│   ├── email-management.yaml
│   ├── project-sync.yaml
│   └── todo-automation.yaml
│
├── templates/                      # Task templates (for reference)
│   ├── daily-email.yaml
│   ├── file-watcher.yaml
│   └── on-demand.yaml
│
├── queue.json                      # Current task queue state
├── execution.log                   # Consolidated current log
├── clodputer.lock                  # Prevents multiple queue managers
│
├── archive/                        # Historical logs (monthly)
│   ├── 2025-10.log
│   └── 2025-09.log
│
└── watches/                        # File watcher state
    ├── project-assignments.state
    └── todo-list.state

/usr/local/bin/
├── clodputer                       # Main CLI
├── clodputer-queue                 # Queue manager (daemon)
├── clodputer-run                   # Task executor
├── clodputer-enqueue               # Add task to queue
├── clodputer-watch                 # File watcher
└── clodputer-cron                  # Cron management
```

---

## Task Configuration Schema (Final)

```yaml
# Required fields
name: task-name                     # Unique identifier
description: Human-readable description
enabled: true                       # Can disable without deleting

# Trigger (one of: schedule, file_watch, manual)
schedule:
  type: cron                        # or: interval, once
  expression: "0 8 * * *"           # Cron expression
  timezone: America/Los_Angeles     # Optional, defaults to system

# OR
trigger:
  type: file_watch
  path: ~/todos/claude-assignments
  pattern: "*.md"                   # Glob pattern
  event: created                    # created, modified, deleted
  debounce: 1000                    # milliseconds

# OR (manual only, no automatic trigger)
trigger:
  type: manual

# Execution config
priority: normal                    # normal, high

task:
  prompt: |                         # Comprehensive single-turn prompt
    [Task instructions]

  allowed_tools:                    # Whitelist of tools
    - Read
    - Write
    - Edit
    - Bash
    - mcp__gmail
    - mcp__google-calendar

  disallowed_tools: []              # Optional blacklist

  permission_mode: acceptEdits      # acceptEdits, rejectEdits, prompt

  timeout: 3600                     # Max execution time (seconds)

  context:                          # Optional variables for prompt
    email: olson.remy@gmail.com
    folder: ~/email-responses

  mcp_config: ~/.clodputer/mcp-custom.json  # Optional custom MCP config

# Outcome handlers
on_success:
  - log: "{{name}} completed successfully"
  - notify: false                   # macOS notification

on_failure:
  - log: "{{name}} failed: {{error}}"
  - notify: true                    # Alert immediately
  - retry: false                    # Future: auto-retry

# Metadata
created: 2025-10-07T11:30:00Z
created_by: claude-code             # or: user
last_run: 2025-10-07T08:00:00Z
run_count: 15
success_rate: 0.93
total_cost: 0.45                    # USD
```

---

## Safety & Cleanup Mechanism

### Problem: MCP Process Cleanup

When a Claude Code instance terminates, MCPs may not always shut down cleanly, leading to orphaned processes.

### Solution: PID-Tracked Cleanup (Safer)

**After each task execution**:
1. Track all PIDs spawned as children of Claude Code instance
2. Kill Claude Code process tree (parent + tracked children)
3. Graceful shutdown: Send SIGTERM, wait 5 seconds
4. Force kill: SIGKILL any still running
5. Final sweep: Find any orphaned `mcp__*` processes by name (safety net)
6. Log any processes that couldn't be killed

**Why PID tracking?**: Safer than name-based killing. Only kills processes we spawned, not unrelated processes that might match `mcp__*` pattern.

**Implementation**:
```python
def cleanup_claude_instance(claude_pid, tracked_child_pids):
    """
    Clean up Claude Code and its MCP children.

    Args:
        claude_pid: Main Claude Code process PID
        tracked_child_pids: List of child PIDs we spawned
    """
    # 1. Get Claude Code process and all its children
    try:
        claude_proc = psutil.Process(claude_pid)
        all_children = claude_proc.children(recursive=True)
    except psutil.NoSuchProcess:
        all_children = []

    # 2. Graceful shutdown - SIGTERM
    try:
        claude_proc.terminate()
    except psutil.NoSuchProcess:
        pass

    for child in all_children:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            continue

    # 3. Wait for graceful shutdown
    time.sleep(5)

    # 4. Force kill any still running
    still_running = []
    try:
        if claude_proc.is_running():
            claude_proc.kill()
            still_running.append(claude_pid)
    except psutil.NoSuchProcess:
        pass

    for child in all_children:
        try:
            if child.is_running():
                child.kill()
                still_running.append(child.pid)
                log_warning(f"Force killed child process: {child.pid}")
        except psutil.NoSuchProcess:
            continue

    # 5. Final safety sweep - find any orphaned MCP processes by name
    #    (This is a backup in case PID tracking missed something)
    orphaned_mcps = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and 'mcp__' in proc.info['name']:
                orphaned_mcps.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Kill any orphaned MCPs found
    for proc in orphaned_mcps:
        try:
            proc.kill()
            log_warning(f"Killed orphaned MCP: {proc.pid} ({proc.info['name']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        'killed_count': len(still_running) + len(orphaned_mcps),
        'orphaned_mcps': len(orphaned_mcps)
    }
```

**Key Improvement**: Primary cleanup uses PID tracking (explicit list of processes we spawned). Name-based search is only a final safety sweep for truly orphaned processes.

---

## Resource Monitoring

### System Resource Check (Before Task Execution)

```python
def check_resources():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent

    if cpu > 80 or memory > 80:
        log_warning(f"High resource usage: CPU {cpu}%, Memory {memory}%")
        return False

    return True

def wait_for_resources(timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        if check_resources():
            return True
        time.sleep(30)  # Check every 30 seconds

    return False
```

**Pre-execution check**: If system resources are high, wait up to 5 minutes before executing task. If still high, log warning but proceed anyway (user may be on video call, etc.).

---

## User System Detection

**Auto-detect system capabilities** on first run:

```python
def detect_system():
    return {
        'os': platform.system(),  # Darwin (macOS)
        'cpu_cores': psutil.cpu_count(),
        'memory_gb': psutil.virtual_memory().total / (1024**3),
        'claude_version': get_claude_version(),
        'mcp_servers': get_configured_mcps(),
    }

# Example output:
{
    'os': 'Darwin',
    'cpu_cores': 8,
    'memory_gb': 16,
    'claude_version': '2.0.0',
    'mcp_servers': [
        'gmail', 'google-calendar', 'google-sheets',
        'crawl4ai', 'ultimate-google-docs', 'playwright'
    ]
}
```

**Use this to**:
- Set reasonable defaults (max 1 concurrent for <16GB RAM)
- Warn if Claude Code not installed
- Verify MCP availability before task execution

---

## AI-Writable Configuration

### Goal: User asks Claude Code to create tasks

**User**: "Claude, I want you to draft email responses every morning at 8 AM"

**Claude Code**: Reads CLAUDE.md → sees Clodputer instructions → generates:

```yaml
name: email-management
description: Daily email triage and response drafting
enabled: true

schedule:
  type: cron
  expression: "0 8 * * *"
  timezone: America/Los_Angeles

priority: normal

task:
  prompt: |
    Read all unread emails from the past 24 hours using the Gmail MCP.

    For each email that requires a response:
    1. Research relevant context from email history
    2. Analyze my writing style from sent emails
    3. Draft an appropriate response
    4. Save to ~/email-responses/YYYY-MM-DD-[subject-slug].md

    After drafting responses:
    - Move all files from ~/email-responses/ (except today's) to ~/email-responses/archive/

    Provide a summary: "Drafted X responses, archived Y old drafts"

  allowed_tools:
    - Read
    - Write
    - Bash
    - mcp__gmail

  permission_mode: acceptEdits
  timeout: 1800

on_success:
  - log: "Email responses drafted"
  - notify: false

on_failure:
  - log: "Email drafting failed: {{error}}"
  - notify: true

created: 2025-10-07T11:30:00Z
created_by: claude-code
```

**Claude Code**: Saves to `~/.clodputer/tasks/email-management.yaml`

**Claude Code**: Runs `clodputer install` to update cron jobs

**Result**: Task will run automatically starting tomorrow at 8 AM

---

## Decisions Finalized ✅

### 1. Notification Mechanism
**Decision**: macOS native notifications only (`osascript -e 'display notification ...'`)
- Pop-up alerts on task failures
- No email/Slack in MVP
- **Platform**: macOS only (no Windows/Linux support)

---

### 2. Cost Tracking
**Decision**: No cost tracking in MVP
- Users expected to have Claude Code Max tier or similar
- If token limits hit, task fails (visible in logs)
- Can manually retry later
- **Rationale**: Keep it simple, most users won't hit limits

---

### 3. Off-Hours Scheduling
**Decision**: Optional preferred time window in config, but not enforced
- User can set preferred hours if desired
- No automatic rescheduling
- User controls their own schedule
- **Rationale**: Test with users first, avoid being prescriptive

**Optional Config**:
```yaml
# ~/.clodputer/config.yaml (optional)
preferred_hours:
  start: "00:00"
  end: "06:00"
  # Tasks scheduled in this window get priority
```

---

### 4. Config Generation
**Decision**: No CLI helper, Claude Code generates configs
- Users ask Claude Code: "Create a daily email task at 8 AM"
- Claude Code reads documentation and generates YAML
- Saves to `~/.clodputer/tasks/*.yaml`
- **Rationale**: Simpler, more powerful, AI-native approach

---

## Next Steps - READY TO BUILD 🚀

### 🎯 Implementation Strategy (Engineer's Advice)

**Critical Approach**: The "Tracer Bullet" Method

Instead of building all components in parallel, prove the core interaction first:

**Days 1-2: Make `clodputer run <task>` work end-to-end**

Focus entirely on the **Task Executor** with a single, hardcoded task:

1. Load `email-management.yaml`
2. Construct and run `claude -p ...` command
3. Capture output
4. Perform PID-based cleanup
5. Print log message to console

**Why?** This proves the single most critical and riskiest part works: the interaction with Claude Code and subsequent cleanup. Once this works, the rest becomes infrastructure around a proven core.

**Build `doctor` Incrementally**

Don't save diagnostics for the end. Build as you go:
- Queue manager built? → Add "check stale lockfile" diagnostic
- Config loader built? → Add "validate all YAMLs" diagnostic
- Cron installer built? → Add "check cron jobs installed" diagnostic

This makes `doctor` your primary debugging tool during development.

**Consider Structured Logging**

Keep human-readable logs for users, but log internally as JSON:

```python
# Instead of:
log.info(f"Task {task.name} completed in {duration}s")

# Log structured data:
log.info({
    "event": "task_completed",
    "task_name": task.name,
    "duration_sec": duration,
    "status": "success"
})
```

**Why?** Makes future dashboard trivial to build. Much easier to parse JSON than human-readable strings. CLI can still format nicely for display.

---

### Phase 1: Core Implementation (Week 1)

**Goal**: Functional MVP with queue + execution + logging

1. **Set up repository** (new repo, not in clodputer planning folder)
   - Initialize git repo
   - Create directory structure
   - Add README with installation instructions

2. **Implement queue manager** (`clodputer-queue.py`)
   - Sequential task execution
   - Priority support (high/normal)
   - Lockfile to prevent concurrent managers
   - Queue persistence (JSON)

3. **Implement task executor** (`clodputer-run.py`)
   - Load YAML config
   - Build Claude Code command
   - Execute with timeout
   - **Aggressive cleanup**: Kill process + all MCPs
   - Parse JSON output

4. **Implement logging system** (`clodputer-log.py`)
   - Consolidated log (single file, always current)
   - Format for readability
   - Monthly archives

5. **Build CLI interface** (`clodputer` script)
   - `clodputer status` - Show queue and recent history
   - `clodputer logs` - View logs
   - `clodputer run <task>` - Enqueue manually
   - `clodputer list` - Show available tasks
   - `clodputer queue` - Show current queue
   - `clodputer doctor` - Run system diagnostics

6. **Test with email management task**
   - Create sample email-management.yaml
   - Run manually: `clodputer run email-management`
   - Verify: execution, logging, cleanup, notifications

### Phase 2: Automation Triggers (Week 2)

7. **Add cron integration** (`clodputer-cron.py`)
   - Parse task configs for schedules
   - Generate cron entries
   - `clodputer install` command

8. **Add file watcher** (`clodputer-watch.py`)
   - Use fswatch for macOS
   - Debouncing logic
   - `clodputer watch --daemon` command

9. **End-to-end testing**
   - Email task running daily at 8 AM
   - Project file watcher monitoring folder
   - Verify sequential execution, cleanup

10. **Documentation**
    - Installation guide
    - Task configuration guide
    - CLAUDE.md instructions for creating tasks
    - Troubleshooting guide

### Phase 3: Polish & Release (Week 3)

11. **Error handling improvements**
    - Better error messages
    - Recovery from common failures
    - Validation of task configs

12. **Open source preparation**
    - Clean up code
    - Add comments
    - Write contributing guide
    - Choose license (MIT recommended)

13. **Public release**
    - GitHub repository
    - Demo video (optional)
    - Share with community

---

## ALL DECISIONS MADE ✅

**Ready to start building immediately!**

All questions answered, specification complete. The next step is to create a new repository and start implementing the core components.

Should I proceed with setting up the repository structure and starting implementation?
