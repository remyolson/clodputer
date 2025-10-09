# Clodputer Testing Principles

## Overview
This document outlines the core principles and best practices for testing Clodputer, with special attention to resource management, safety protocols, and systematic testing methodology.

## Core Testing Principles

### 1. Systematic Approach
- **Document Everything**: Every test run must be documented with logs, findings, and outcomes
- **Reproducibility**: Tests should be repeatable with consistent results
- **Incremental Testing**: Test one feature at a time, don't combine multiple changes
- **Baseline First**: Always establish a working baseline before making changes

### 2. Safety First
- **Never Kill Own Processes**: When testing as Claude Code, never terminate your own process or parent processes
- **MCP Protection**: Do not kill or interfere with MCP servers that the testing instance relies on
- **Backup State**: Always backup configuration and state files before destructive operations
- **Rollback Plan**: Have a clear rollback strategy for every test

### 3. Resource Management

#### Computer Resource Monitoring
Claude Code with MCPs can be **very resource intensive**. Careful monitoring and cleanup are essential.

**Resource Concerns:**
- High CPU usage from multiple Claude CLI processes
- Memory consumption from MCP servers (especially browser-based MCPs like Playwright, Crawl4AI)
- File descriptor limits from multiple concurrent connections
- Disk I/O from logging and state management

**Monitoring Strategy:**
```bash
# Before testing - establish baseline
top -l 1 | grep -E "CPU|PhysMem"
ps aux | grep -E "claude|python|node" | wc -l

# During testing - monitor continuously
# Check for runaway processes, memory leaks, zombie processes
```

**Cleanup Protocol:**
1. **After Each Test Run**:
   - Check for orphaned Claude CLI processes: `ps aux | grep "claude"`
   - Check for zombie Python processes: `ps aux | grep "python.*clodputer"`
   - Clean up temp files in `~/.clodputer/`
   - Review log files for size (`~/.clodputer/logs/`, `~/.clodputer/debug.log`)

2. **Between Test Cycles**:
   - Stop any running daemons: `clodputer watch --stop`, `clodputer menu --stop`
   - Clear test tasks from `~/.clodputer/tasks/` (backup first)
   - Archive old logs
   - Reset state if needed: `clodputer init --reset`

3. **Process Cleanup Rules**:
   - ✅ **SAFE**: Kill orphaned `claude` CLI processes spawned by Clodputer
   - ✅ **SAFE**: Kill `clodputer` daemon processes (watch, menu)
   - ✅ **SAFE**: Kill test-spawned Python processes
   - ❌ **UNSAFE**: Kill the Claude Code instance running the tests (your parent process)
   - ❌ **UNSAFE**: Kill MCP servers that Claude Code (the tester) depends on
   - ❌ **UNSAFE**: Kill any process you didn't spawn or verify

4. **How to Identify Safe vs Unsafe Processes**:
   ```bash
   # Get your own PID and parent processes
   echo $$  # Your shell PID
   ps -p $$ -o ppid=  # Parent PID
   pstree -p $$  # Process tree

   # Safe to kill: Processes spawned by clodputer with PPID from clodputer
   ps aux | grep "claude" | grep -v "grep" | grep -v $PPID

   # NEVER kill processes with your Claude Code session's PPID or above
   ```

#### Disk Space Management
```bash
# Check available disk space before testing
df -h ~/.clodputer/

# Monitor log growth
du -sh ~/.clodputer/logs/
du -sh ~/.clodputer/debug.log

# Archive large logs before testing
[ -f ~/.clodputer/debug.log ] && [ $(stat -f%z ~/.clodputer/debug.log) -gt 10485760 ] && \
  mv ~/.clodputer/debug.log ~/.clodputer/debug.log.$(date +%Y%m%d_%H%M%S)
```

### 4. Test Environment Isolation

#### Fresh Install Testing
When testing fresh installation:
1. **Backup existing state**:
   ```bash
   cp -r ~/.clodputer ~/.clodputer.backup.$(date +%Y%m%d_%H%M%S)
   ```
2. **Uninstall cleanly**:
   ```bash
   pipx uninstall clodputer
   rm -rf ~/.clodputer/  # After backup!
   ```
3. **Verify clean state**: Ensure no residual files, cron jobs, or processes
4. **Document baseline**: Record system state before installation

#### Test Data Management
- Use separate task files for testing (e.g., `test-*.yaml`)
- Never modify production task configurations during testing
- Keep test prompts simple and fast (< 30 seconds execution)
- Use mock/stub tasks when possible to avoid actual Claude API calls

### 5. Test Run Documentation

#### Required Test Run Artifacts
Each test run must produce:
1. **Test Run Log**: Timestamped file with complete test execution output
2. **Findings Document**: Issues, bugs, unexpected behavior, UX observations
3. **Resource Metrics**: CPU/memory usage before, during, after
4. **Screenshots** (if applicable): Visual evidence of UI issues
5. **Next Steps**: Clear action items derived from findings

#### Test Run Template
```markdown
# Test Run: [Description] - [YYYY-MM-DD HH:MM]

## Test Objective
[What are you testing?]

## Pre-Test State
- Clodputer version: [version]
- Installation method: [pipx, source, etc.]
- Existing tasks: [count and types]
- System resources: [CPU %, Memory %, Disk %]
- Active processes: [relevant process count]

## Test Execution
[Step-by-step log of what was done]

## Observations
[What happened? Expected vs actual behavior]

## Issues Found
[Numbered list of bugs, UX issues, unexpected behavior]

## Resource Usage
- Peak CPU: [%]
- Peak Memory: [MB]
- Orphaned processes: [count]
- Log file sizes: [MB]

## Next Steps
[Action items derived from this test]

## Cleanup Performed
[What cleanup was done after the test]
```

### 6. Test Coverage Areas

#### Installation & Onboarding
- Fresh installation from source
- Fresh installation via pipx
- Re-running onboarding (`clodputer init`)
- Onboarding with existing state
- Template installation flow
- CLAUDE.md integration
- Intelligent task generation (with and without MCPs)

#### Core Functionality
- Task execution (`clodputer run`)
- Queue management (`clodputer queue`)
- Cron scheduling (`clodputer install`)
- File watching (`clodputer watch`)
- Logging and diagnostics (`clodputer logs`, `clodputer doctor`)

#### Edge Cases
- Network disconnection during task execution
- Claude CLI timeout
- Invalid task configurations
- Disk space exhaustion
- Permission errors
- Concurrent task execution

### 7. Continuous Improvement

#### After Each Test Cycle
1. Review all findings and prioritize fixes
2. Update test documentation with new edge cases discovered
3. Add regression tests for fixed bugs
4. Improve error messages and user guidance based on observations
5. Document any resource management improvements needed

#### Master Issues Tracker
Maintain `docs/testing/ISSUES_AND_IMPROVEMENTS.md` with:
- All issues found during testing (with test run reference)
- Priority classification (Critical, High, Medium, Low)
- Status tracking (Open, In Progress, Fixed, Verified)
- Owner and target resolution date

## Quick Reference Commands

### Pre-Test Checklist
```bash
# 1. Backup state
cp -r ~/.clodputer ~/.clodputer.backup.$(date +%Y%m%d_%H%M%S)

# 2. Check baseline resources
top -l 1 | head -10
df -h ~/.clodputer/

# 3. Document active processes
ps aux | grep -E "claude|clodputer" > pre-test-processes.txt
```

### Post-Test Cleanup
```bash
# 1. Stop daemons
clodputer watch --stop 2>/dev/null || true
# (menu stop would go here, but skip if testing from Claude Code)

# 2. Check for orphaned processes (CAREFULLY)
ps aux | grep "claude" | grep -v "grep" | grep -v $PPID
# Manually review before killing any!

# 3. Archive logs
mkdir -p ~/.clodputer/logs/archive/$(date +%Y%m%d)
mv ~/.clodputer/logs/*.log ~/.clodputer/logs/archive/$(date +%Y%m%d)/ 2>/dev/null || true

# 4. Check disk usage
du -sh ~/.clodputer/
```

## Testing Best Practices

1. **One Change at a Time**: Test one feature or fix at a time to isolate issues
2. **Document Immediately**: Write findings as you discover them, not after
3. **Take Breaks**: Resource-intensive testing can slow down your system - take breaks between test runs
4. **Version Everything**: Tag or note the exact commit being tested
5. **Compare to Baseline**: Always compare behavior to a known-good baseline
6. **User Perspective**: Think like a first-time user encountering this feature
7. **Failure Modes**: Explicitly test failure scenarios (network loss, invalid input, etc.)
8. **Recovery Testing**: Test how the system recovers from errors (can user continue? data loss?)

## Emergency Procedures

### System Overloaded
If testing causes system overload:
1. **DO NOT** use `killall` or `pkill` broadly
2. Identify specific runaway processes: `top` or Activity Monitor
3. Verify process ownership before killing
4. Start with most recent spawned processes (highest PID)
5. Archive current test logs before cleanup
6. Document the overload scenario for bug reporting

### Accidental Self-Termination Prevention
If you're testing as Claude Code and risk killing your own process:
```bash
# ALWAYS check before killing processes
MY_SESSION_PID=$(ps -p $$ -o ppid= | tr -d ' ')
CLAUDE_CODE_PPID=$(ps -p $MY_SESSION_PID -o ppid= | tr -d ' ')

# Verify you're not about to kill your parent
ps -p <TARGET_PID> -o ppid= | grep -q "$CLAUDE_CODE_PPID" && \
  echo "⚠️  DANGER: This process is related to your Claude Code session!" && \
  exit 1
```

## Version History
- 2025-01-09: Initial testing principles document created

---

**Remember**: Testing is about learning and improving, not about being perfect. Document everything, be systematic, and prioritize safety and resource management.
