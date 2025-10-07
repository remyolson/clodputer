# Clodputer Safety Features

**Date**: October 7, 2025
**Purpose**: Document all safety mechanisms to protect user data and system

---

## Critical Safety: CLAUDE.md Modification

### Multi-Layer Protection

**1. Automatic Backup**
```python
# Before ANY modification, create timestamped backup
backup_path = ~/CLAUDE.md.backup-1696723890
```

**2. Read-Only Verification**
```python
# Verify file is readable and contains expected content
original_content = read_file(CLAUDE.md)
if not original_content:
    prompt_user("File appears empty, continue?")
```

**3. Duplicate Detection**
```python
# Never add twice - check for existing Clodputer section
if "## Clodputer:" in content:
    skip_modification()
```

**4. Append-Only Operation**
```python
# NEVER delete or modify existing content
new_content = original_content + clodputer_section
# Original content always preserved at start
```

**5. Atomic Write**
```python
# Write to temporary file first
write(CLAUDE.md.tmp, new_content)
# Verify temp file is correct
verify(CLAUDE.md.tmp contains original_content)
# Only then replace original
move(CLAUDE.md.tmp → CLAUDE.md)
```

**6. Integrity Validation**
```python
# After write, verify original content still present
if original_content not in new_file:
    rollback_from_backup()
    raise_error()
```

**7. Automatic Rollback**
```python
try:
    modify_file()
except Exception:
    restore_from_backup()
    notify_user("Restored original, no changes made")
```

**8. Backup Retention**
```
Backup kept indefinitely at:
~/CLAUDE.md.backup-[timestamp]

User can delete manually after verification
```

---

## Process Safety: Task Execution

### Resource Cleanup

**1. Process Tree Termination**
```python
# Kill entire process tree on task completion
pkill -P <parent_pid>  # All child processes
kill <claude_pid>      # Main process
```

**2. MCP Process Cleanup (PID-Tracked)**
```python
# PRIMARY: Use tracked PIDs (safer)
# Get all children of Claude Code process
claude_proc = psutil.Process(claude_pid)
children = claude_proc.children(recursive=True)

# Graceful shutdown first (SIGTERM)
claude_proc.terminate()
for child in children:
    child.terminate()

wait(5 seconds)

# Force kill if still running (SIGKILL)
if claude_proc.is_running():
    claude_proc.kill()
for child in children:
    if child.is_running():
        child.kill()
        log_warning(f"Force killed child: {child.pid}")

# BACKUP: Name-based search for orphans
# Only kills processes if PID tracking missed something
orphaned_mcps = find_processes(name_pattern="mcp__*")
for proc in orphaned_mcps:
    proc.kill()
    log_warning(f"Killed orphaned MCP: {proc.pid}")
```

**3. Verification Loop**
```python
# After cleanup, verify no orphans
orphaned = find_mcp_processes()
if orphaned:
    raise CleanupError("Failed to cleanup all MCPs")
    retry_cleanup()
```

**4. Timeout Protection**
```python
# Every task has max execution time
execute_with_timeout(task, timeout=3600)

# If timeout exceeded:
kill_process_tree()
log_failure("Task timed out")
notify_user()
```

---

## File System Safety

### 1. Path Validation

**Before any file operation**:
```python
def validate_path(path):
    # Expand user home directory
    path = Path(path).expanduser()

    # Resolve symlinks to real path
    path = path.resolve()

    # Check path is within allowed directories
    allowed_roots = [
        Path.home(),
        Path("/tmp"),
    ]

    if not any(path.is_relative_to(root) for root in allowed_roots):
        raise SecurityError(f"Path outside allowed directories: {path}")

    # Check for path traversal attempts
    if ".." in path.parts:
        raise SecurityError("Path traversal not allowed")

    return path
```

### 2. File Creation Safety

**Before creating files**:
```python
def safe_create_file(path, content):
    path = validate_path(path)

    # Check if directory exists
    if not path.parent.exists():
        raise FileNotFoundError(f"Parent directory doesn't exist: {path.parent}")

    # Check if file already exists
    if path.exists():
        user_confirm = prompt(f"Overwrite {path}? (y/n)")
        if not user_confirm:
            raise FileExistsError("User cancelled overwrite")

    # Write atomically
    temp = path.with_suffix('.tmp')
    temp.write_text(content)
    temp.rename(path)
```

### 3. Directory Traversal

**When watching directories**:
```python
# Restrict file watcher to specific directory
watcher = FileWatcher(path="~/todos/claude-assignments")

# Never watch system directories
forbidden = ["/", "/System", "/usr", "/bin", "/etc"]
if any(path.startswith(f) for f in forbidden):
    raise SecurityError("Cannot watch system directories")

# Respect .gitignore patterns
watcher.ignore_patterns([".git/*", "*.pyc", "__pycache__/*"])
```

---

## Queue Safety

### 1. Lock File Protection

**Prevent concurrent queue managers**:
```python
LOCK_FILE = ~/.clodputer/clodputer.lock

def acquire_lock():
    if LOCK_FILE.exists():
        # Check if process still running
        pid = int(LOCK_FILE.read_text())
        if process_exists(pid):
            raise RuntimeError("Another queue manager is running")
        else:
            # Stale lock file, remove it
            LOCK_FILE.unlink()

    # Create lock with current PID
    LOCK_FILE.write_text(str(os.getpid()))

def release_lock():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
```

### 2. Queue Corruption Prevention

**Atomic queue updates**:
```python
def update_queue(queue_data):
    # Write to temp file
    temp_path = QUEUE_FILE.with_suffix('.tmp')
    temp_path.write_text(json.dumps(queue_data, indent=2))

    # Verify JSON is valid
    verify_json = json.loads(temp_path.read_text())

    # Atomic replace
    temp_path.rename(QUEUE_FILE)
```

### 3. Task Cancellation Safety

**If user cancels running task**:
```python
def cancel_task(task_id):
    # Find running task
    task = get_running_task(task_id)

    # Kill process gracefully
    task.process.terminate()
    wait(5 seconds)

    # Force kill if needed
    if task.process.is_running():
        task.process.kill()

    # Clean up MCPs
    cleanup_claude_instance(task.process.pid)

    # Update queue state
    mark_task_cancelled(task_id)
```

---

## Permission Safety

### 1. Tool Whitelisting

**Every task explicitly lists allowed tools**:
```yaml
allowed_tools:
  - Read
  - Write
  - mcp__gmail

# If task tries to use unlisted tool:
# Claude Code will reject the operation
```

### 2. Permission Mode

**Default: Require approval for edits**:
```yaml
permission_mode: prompt  # Default (safe)
# OR
permission_mode: acceptEdits  # Auto-approve (use carefully)
```

**For automation, set per-task**:
```yaml
# Trusted task: auto-approve
permission_mode: acceptEdits

# Sensitive task: require approval (but this breaks automation)
permission_mode: prompt
```

### 3. MCP Access Control

**Tasks can't access MCPs not in allowed_tools**:
```python
# Task config
allowed_tools: [Read, Write, mcp__gmail]

# If task tries to use mcp__google-calendar:
# Claude Code will reject the operation
```

---

## Log Safety

### 1. Log Rotation

**Prevent unbounded log growth**:
```python
# When execution.log exceeds 10 MB
if log_size > 10_MB:
    # Archive current log
    archive_path = ~/.clodputer/archive/YYYY-MM.log
    move(execution.log → archive_path)

    # Create fresh log
    touch(execution.log)
```

### 2. Sensitive Data Redaction

**Redact secrets from logs**:
```python
def log_output(text):
    # Redact common secret patterns
    patterns = [
        (r'api[_-]?key["\s:=]+[a-zA-Z0-9]+', 'api_key=***'),
        (r'password["\s:=]+[^\s]+', 'password=***'),
        (r'token["\s:=]+[a-zA-Z0-9]+', 'token=***'),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    write_log(text)
```

---

## Error Handling Safety

### 1. Never Crash Silently

**All errors logged and reported**:
```python
try:
    execute_task(task)
except Exception as e:
    log_error(task.name, str(e), traceback.format_exc())
    notify_user(f"Task failed: {task.name}")
    mark_task_failed(task.id, error=str(e))
```

### 2. Graceful Degradation

**If critical component fails**:
```python
# Menu bar app crash
try:
    update_menu_bar()
except Exception:
    log_error("Menu bar update failed")
    # Continue execution, don't crash entire system

# CLI still works even if menu bar fails
```

### 3. Partial Failure Handling

**If task partially completes**:
```python
# Task: Draft 10 emails, save to files

drafted = []
failed = []

for email in emails:
    try:
        draft = create_draft(email)
        save_file(draft)
        drafted.append(email.id)
    except Exception as e:
        failed.append((email.id, str(e)))

# Report partial success
log(f"Drafted {len(drafted)}/10 emails")
if failed:
    log(f"Failed: {failed}")
    notify_user("Task partially completed with errors")
```

---

## Installation Safety

### 1. Dry Run Mode

**Test installation without changes**:
```bash
$ clodputer setup --dry-run

🔍 Clodputer Setup (Dry Run Mode)

Would perform:
  ✓ Create ~/.clodputer/ directories
  ✓ Copy 3 task templates
  ✓ Add Clodputer section to ~/CLAUDE.md
    (Show exact text that would be added)
  ✓ Install menu bar app

No changes made. Run without --dry-run to install.
```

### 2. Dependency Verification

**Check before installation**:
```python
# Verify all dependencies exist
required = {
    'claude': 'Claude Code',
    'fswatch': 'fswatch',
    'jq': 'jq',
    'yq': 'yq',
}

missing = [name for cmd, name in required.items() if not which(cmd)]

if missing:
    print(f"❌ Missing: {', '.join(missing)}")
    print("Install with: brew install " + " ".join(missing))
    exit(1)
```

### 3. Version Compatibility

**Check Claude Code version**:
```python
claude_version = get_claude_version()
min_version = "2.0.0"

if version.parse(claude_version) < version.parse(min_version):
    print(f"⚠️  Claude Code {claude_version} is too old")
    print(f"   Clodputer requires {min_version}+")
    print("   Update Claude Code: brew upgrade claude")
    exit(1)
```

---

## Uninstallation Safety

### 1. Preserve User Data by Default

**Uninstall process**:
```bash
$ clodputer uninstall

🗑️  Uninstalling Clodputer...

✅ Removed cron jobs
✅ Stopped file watchers
✅ Removed menu bar app
✅ Removed Clodputer section from ~/CLAUDE.md

Your task configs and logs are preserved at:
  ~/.clodputer/

Delete all data? (y/n): n

Clodputer has been uninstalled.
Your data is kept for future reinstallation.

To remove data manually:
  rm -rf ~/.clodputer/
```

### 2. CLAUDE.md Restoration

**Remove only Clodputer section**:
```python
def remove_from_claude_md(claude_md_path):
    # Backup first
    create_backup(claude_md_path)

    # Read content
    content = claude_md_path.read_text()

    # Find Clodputer section
    start_marker = "# CLODPUTER INTEGRATION"
    if start_marker not in content:
        print("Clodputer section not found")
        return

    # Find section boundaries
    start_idx = content.find(start_marker)
    # Find previous paragraph break
    start_idx = content.rfind('\n\n', 0, start_idx)

    # Section ends at EOF (it's at the end)
    end_idx = len(content)

    # Remove section
    new_content = content[:start_idx] + content[end_idx:]

    # Verify we didn't lose other content
    if len(new_content) < 100:  # CLAUDE.md should be substantial
        print("⚠️  Error: Result file too small")
        restore_from_backup()
        return

    # Write atomically
    atomic_write(claude_md_path, new_content)
```

---

## Summary: Safety-First Design

### Core Principles

1. **Never delete user data** without explicit confirmation
2. **Always create backups** before modifications
3. **Verify operations** before committing changes
4. **Fail gracefully** with clear error messages
5. **Log everything** for debugging and audit
6. **Atomic operations** to prevent corruption
7. **Cleanup thoroughly** to prevent resource leaks
8. **Validate inputs** to prevent security issues

### Safety Checklist for Every Feature

- [ ] Creates backup if modifying files?
- [ ] Validates paths to prevent traversal?
- [ ] Uses atomic writes for critical files?
- [ ] Cleans up processes thoroughly?
- [ ] Handles errors without crashing?
- [ ] Logs operations for debugging?
- [ ] Provides clear error messages?
- [ ] Allows user to cancel/rollback?

---

## For Your Engineer Friend

**Key safety highlights to review**:

1. **CLAUDE.md modification** - See lines 141-218 in `08-installation-and-integration.md`
   - Automatic backup before modification
   - Append-only (never deletes existing content)
   - Atomic write with verification
   - Auto-rollback on errors

2. **Process cleanup** - See "Process Safety" section above
   - Kills entire process tree
   - Hunts down orphaned MCP processes
   - Verifies cleanup succeeded

3. **File system operations** - See "File System Safety" section
   - Path validation and traversal protection
   - Atomic file writes
   - Directory access controls

4. **Queue management** - See "Queue Safety" section
   - Lock file prevents concurrent managers
   - Atomic queue updates
   - Graceful cancellation

Is there anything else you'd like documented before sharing with your engineer friend?
