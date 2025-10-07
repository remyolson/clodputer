# Technical Architecture Options

## Overview

This document explores different architectural approaches for building Clodputer, analyzing the trade-offs between simplicity, performance, and functionality.

## Architecture Option 1: Single Persistent Claude Code Instance

### Description
Run a single Claude Code instance in headless mode that stays active in the background, receiving tasks through a message queue or stdin stream.

### Implementation
```bash
# Start persistent Claude Code instance
claude -p --output-format stream-json --input-format stream-json < task-queue.jsonl

# Orchestrator feeds tasks via stdin
echo '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Execute task 1"}]}}' >> task-queue.jsonl
```

### Pros
- **Single MCP initialization**: All MCPs spin up once, stay loaded
- **Minimal resource overhead**: No repeated process spawning
- **Context persistence**: Natural conversation continuity
- **Session management**: Built-in session tracking
- **Efficient for rapid task sequences**

### Cons
- **Complexity**: Managing stdin/stdout streaming is non-trivial
- **Failure recovery**: If instance crashes, entire system goes down
- **Resource leaks**: Long-running process may accumulate memory
- **Isolation issues**: Tasks share the same execution context
- **Debugging challenges**: Harder to troubleshoot individual tasks

### Best For
- High-frequency automation (multiple tasks per hour)
- Tasks requiring shared context
- Systems with limited resources

---

## Architecture Option 2: On-Demand Instance Spawning

### Description
Spawn a new Claude Code instance for each task, manage lifecycle explicitly.

### Implementation
```bash
# Cron job example
*/30 * * * * /usr/local/bin/clodputer-run --task email-management

# clodputer-run script
#!/bin/bash
session_output=$(claude -p "$TASK_PROMPT" --output-format json --allowedTools "$ALLOWED_TOOLS")
echo "$session_output" >> /var/log/clodputer/tasks.log
```

### Pros
- **Simple implementation**: Straightforward shell scripting
- **Fault isolation**: Each task is independent
- **Easy debugging**: Clear logs per execution
- **No state management**: Fresh start every time
- **Predictable resource usage**: Fixed per-task cost

### Cons
- **MCP overhead**: Spin up all MCPs for every task (5-10 seconds)
- **No context retention**: Each task starts from scratch
- **Higher resource usage**: Multiple concurrent instances can overwhelm system
- **Cost inefficiency**: Redundant initialization work

### Best For
- Infrequent automation (few times per day)
- Independent tasks with no shared context
- Simple, maintenance-free operation

---

## Architecture Option 3: Hybrid Session Pool

### Description
Maintain a small pool (2-3) of warm Claude Code sessions, route tasks to available instances.

### Implementation
```python
# Pseudo-code for session pool manager
class ClaudeSessionPool:
    def __init__(self, pool_size=2):
        self.sessions = [self.start_session() for _ in range(pool_size)]
        self.lock = threading.Lock()

    def execute_task(self, task):
        with self.lock:
            session = self.get_available_session()
            return session.resume_and_execute(task)
```

### Pros
- **Balanced resource usage**: Warm sessions reduce overhead
- **Concurrent execution**: Handle multiple tasks in parallel
- **Graceful degradation**: If one session fails, others continue
- **Context flexibility**: Can maintain separate contexts per session

### Cons
- **Implementation complexity**: Requires session management logic
- **Coordination overhead**: Need to track session states
- **Resource monitoring**: Must prevent pool exhaustion
- **Still requires MCP management**

### Best For
- Medium-frequency automation (hourly tasks)
- Mix of independent and context-dependent tasks
- Production systems needing reliability

---

## Architecture Option 4: Event-Driven Microservice

### Description
Build a lightweight daemon that listens for events (file changes, cron triggers) and dispatches to Claude Code.

### Implementation
```python
# Daemon architecture
class ClodputerDaemon:
    def __init__(self):
        self.file_watcher = FileSystemWatcher()
        self.cron_scheduler = CronScheduler()
        self.task_executor = ClaudeCodeExecutor()

    def run(self):
        self.file_watcher.on_change(self.handle_file_event)
        self.cron_scheduler.on_trigger(self.handle_cron_event)
        self.event_loop.run_forever()

    def handle_file_event(self, path):
        task = self.parse_file_task(path)
        self.task_executor.execute(task)
```

### Pros
- **Event-driven**: Responds instantly to triggers
- **Centralized control**: Single service manages all automation
- **Flexible routing**: Can choose execution strategy per task
- **Monitoring friendly**: Easy to add logging, metrics
- **Extensible**: Can add new trigger types easily

### Cons
- **Daemon management**: Need to ensure service stays running
- **More code**: Requires proper event loop, error handling
- **Platform dependency**: macOS vs Linux differences
- **Installation complexity**: Not just a simple script

### Best For
- Production environments
- Complex automation workflows
- Systems requiring monitoring and observability

---

## Integration Points with Claude Code

### 1. Headless Mode CLI
**Method**: Direct `claude` command invocation
- **Access**: `claude -p "prompt" --output-format json`
- **Multi-turn**: `claude --resume SESSION_ID "next prompt"`
- **Streaming**: `--output-format stream-json` with `--input-format stream-json`

### 2. Session Management
**Method**: Track session IDs for conversation continuity
- **Extract**: Parse `session_id` from JSON output
- **Resume**: Pass `--resume SESSION_ID` for follow-up prompts
- **Continue**: Use `--continue` for most recent session

### 3. Configuration Files
**Method**: Dynamic MCP and permission configuration
- **MCP config**: `--mcp-config /path/to/servers.json`
- **Tool control**: `--allowedTools "Bash,Read,Gmail"` or `--disallowedTools "Write"`
- **Permission mode**: `--permission-mode acceptEdits` for automation

### 4. Output Parsing
**Method**: Parse JSON responses for task completion
- **Success detection**: Check `"is_error": false` in response
- **Cost tracking**: Extract `"total_cost_usd"` for monitoring
- **Duration**: Monitor `"duration_ms"` for performance
- **Result extraction**: Parse `"result"` field for content

### 5. Hooks System
**Method**: Leverage existing Claude Code hooks
- **Pre-prompt**: Execute checks before task starts
- **Post-tool**: React to tool execution results
- **User-prompt-submit**: Intercept user submissions (less useful for automation)

### 6. Background Task Management
**Method**: Use Claude Code's native background task support
- **Long-running processes**: Dev servers, watchers, builds
- **Non-blocking**: Tasks continue while Claude works on other things

---

## Comparison Matrix

| Criterion | Option 1: Persistent | Option 2: On-Demand | Option 3: Session Pool | Option 4: Daemon |
|-----------|---------------------|---------------------|----------------------|------------------|
| **Simplicity** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Resource Efficiency** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Fault Isolation** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Context Retention** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Debugging** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Scalability** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Setup Complexity** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Open Source Ready** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## Recommended Approach: Hybrid Progressive Implementation

### Phase 1: Simple On-Demand (MVP)
Start with **Option 2** for immediate functionality:
- Simple cron scripts calling `claude -p`
- Basic file watchers using `fswatch` on macOS
- JSON output parsing for task completion
- Minimal configuration, maximum simplicity

**Rationale**:
- Fastest to implement and test
- Easy to understand and debug
- Validates core use cases
- Open source friendly

### Phase 2: Add Session Management
Enhance with multi-turn conversation support:
- Track session IDs across related tasks
- Resume conversations for context-dependent workflows
- Implement basic task sequencing

**Rationale**:
- Addresses the multi-turn requirement
- Doesn't require complete rewrite
- Opt-in complexity

### Phase 3: Daemon for Production (Optional)
Evolve to **Option 4** if needed:
- Build lightweight daemon for event handling
- Implement session pooling internally
- Add monitoring and observability
- Package for easy distribution

**Rationale**:
- Only add complexity if validated by usage
- Provides production-grade reliability
- Maintains backward compatibility with Phase 1/2

---

## Technical Stack Recommendation

### Core Components
- **Language**: Bash + Python (minimal)
  - Bash for cron scripts and simple orchestration
  - Python for complex logic (session management, JSON parsing)
- **File Watcher**: `fswatch` (macOS) or `inotify-tools` (Linux)
- **Scheduler**: Native `cron` on macOS/Linux
- **JSON Parsing**: `jq` for bash, `json` module for Python
- **Process Management**: `supervisord` (optional, for daemon phase)

### Configuration Format
- **YAML or JSON** for task definitions
- **Markdown** for task templates
- **Environment variables** for secrets and paths

### Logging
- **Structured logs**: JSON format for easy parsing
- **Rotation**: `logrotate` for long-running systems
- **Destinations**: File-based, with optional cloud export

---

## Key Design Decisions Needed

1. **Instance Management Strategy**:
   - Start with on-demand, evolve to session pool?
   - Acceptable MCP startup latency?

2. **Context Retention**:
   - How critical is multi-turn conversation continuity?
   - Can we approximate with good prompting?

3. **Resource Limits**:
   - Maximum concurrent Claude Code instances?
   - Memory/CPU thresholds for throttling?

4. **Error Handling**:
   - Retry failed tasks? How many attempts?
   - Alert on persistent failures?

5. **Configuration Management**:
   - Per-task MCP configurations?
   - Global vs. task-specific permissions?

6. **Security**:
   - Sandbox task execution?
   - Whitelist allowed tools per automation?

---

**Next**: [Implementation Plan](03-implementation-plan.md)
