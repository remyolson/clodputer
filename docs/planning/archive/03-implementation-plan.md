# Implementation Plan

## Overview

This document outlines a phased approach to building Clodputer, prioritizing quick wins while maintaining a path to production-grade automation.

---

## Phase 1: MVP - Simple On-Demand Execution (Week 1-2)

### Goal
Validate core concept with minimal code: cron-triggered tasks and basic file watching.

### Components

#### 1.1 Core Orchestrator Script
**File**: `clodputer-run.sh`

**Responsibilities**:
- Parse task configuration from YAML/JSON
- Construct appropriate `claude -p` command with flags
- Execute task and capture JSON output
- Parse response for success/failure
- Log execution details
- Handle basic error cases

**Example**:
```bash
#!/bin/bash
# clodputer-run.sh - Execute a single Clodputer task

TASK_CONFIG=$1
TASK_NAME=$(jq -r '.name' "$TASK_CONFIG")
TASK_PROMPT=$(jq -r '.prompt' "$TASK_CONFIG")
ALLOWED_TOOLS=$(jq -r '.allowed_tools | join(",")' "$TASK_CONFIG")

# Execute task
OUTPUT=$(claude -p "$TASK_PROMPT" \
  --output-format json \
  --allowedTools "$ALLOWED_TOOLS" \
  --permission-mode acceptEdits 2>&1)

# Parse result
IS_ERROR=$(echo "$OUTPUT" | jq -r '.is_error')
RESULT=$(echo "$OUTPUT" | jq -r '.result')
SESSION_ID=$(echo "$OUTPUT" | jq -r '.session_id')

# Log
echo "$(date) | $TASK_NAME | Session: $SESSION_ID | Error: $IS_ERROR" >> ~/.clodputer/logs/executions.log

if [ "$IS_ERROR" = "true" ]; then
  echo "Task failed: $RESULT" >&2
  exit 1
fi

echo "$RESULT"
```

#### 1.2 Task Configuration Format
**File**: `~/.clodputer/tasks/email-management.yaml`

**Format**:
```yaml
name: email-management
description: Daily email triage and response drafting
schedule: "0 8 * * *"  # Every day at 8 AM
enabled: true

task:
  prompt: |
    Read all unread emails from the past 24 hours using Gmail MCP.
    For each email requiring a response:
    1. Research relevant context from email history
    2. Draft a response matching my writing style
    3. Save to ~/email-responses/YYYY-MM-DD-[subject].md

    Archive all files in ~/email-responses/ (except today's) to ~/email-responses/archive/

    Provide a summary of actions taken.

  allowed_tools:
    - Read
    - Write
    - Bash
    - mcp__gmail

  permission_mode: acceptEdits

  output:
    format: json
    save_to: ~/.clodputer/logs/email-management-YYYY-MM-DD.json
```

#### 1.3 Cron Integration
**File**: `install-cron.sh`

**Responsibilities**:
- Parse all task configs in `~/.clodputer/tasks/`
- Generate cron entries for scheduled tasks
- Install to user's crontab
- Provide uninstall option

**Example**:
```bash
#!/bin/bash
# install-cron.sh - Set up cron jobs from task configs

TASKS_DIR=~/.clodputer/tasks
CRON_TMP=$(mktemp)

# Backup existing crontab
crontab -l > "$CRON_TMP" 2>/dev/null || true

# Add Clodputer tasks
echo "# Clodputer automated tasks" >> "$CRON_TMP"
for task_file in "$TASKS_DIR"/*.yaml; do
  ENABLED=$(yq -r '.enabled' "$task_file")
  if [ "$ENABLED" = "true" ]; then
    SCHEDULE=$(yq -r '.schedule' "$task_file")
    TASK_NAME=$(yq -r '.name' "$task_file")
    echo "$SCHEDULE /usr/local/bin/clodputer-run.sh $task_file >> ~/.clodputer/logs/cron.log 2>&1" >> "$CRON_TMP"
  fi
done

# Install new crontab
crontab "$CRON_TMP"
rm "$CRON_TMP"
echo "Cron jobs installed successfully"
```

#### 1.4 File Watcher
**File**: `clodputer-watch.sh`

**Responsibilities**:
- Monitor directories for file changes using `fswatch`
- Trigger task execution on specific patterns
- Debounce rapid file changes

**Example**:
```bash
#!/bin/bash
# clodputer-watch.sh - Watch directories for changes

WATCH_DIR=${1:-~/todos/claude-assignments}
TASK_CONFIG=~/.clodputer/tasks/project-assignment.yaml

fswatch -0 -e ".*" -i "\\.md$" "$WATCH_DIR" | while read -d "" filepath; do
  # Only process new files (not modifications)
  if [ -f "$filepath" ]; then
    echo "$(date) | New file detected: $filepath" >> ~/.clodputer/logs/watcher.log

    # Execute task with file context
    PROMPT=$(cat "$TASK_CONFIG" | yq -r '.task.prompt')
    PROMPT="$PROMPT\n\nNew file: $filepath"

    claude -p "$PROMPT" --output-format json \
      --allowedTools "Read,Write,Edit,Bash" \
      --permission-mode acceptEdits >> ~/.clodputer/logs/watcher-executions.log 2>&1
  fi
done
```

#### 1.5 Installation & Setup
**File**: `install.sh`

**Responsibilities**:
- Create directory structure (`~/.clodputer/{tasks,logs,sessions}`)
- Install dependencies (`jq`, `yq`, `fswatch`)
- Copy scripts to `/usr/local/bin/`
- Set up initial task templates
- Validate Claude Code installation

**Example**:
```bash
#!/bin/bash
# install.sh - Set up Clodputer

set -e

echo "🚀 Installing Clodputer..."

# Create directory structure
mkdir -p ~/.clodputer/{tasks,logs,sessions,templates}

# Check dependencies
command -v claude >/dev/null 2>&1 || { echo "❌ Claude Code not found. Install from https://claude.ai/download"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "❌ jq not found. Install with: brew install jq"; exit 1; }
command -v yq >/dev/null 2>&1 || { echo "❌ yq not found. Install with: brew install yq"; exit 1; }
command -v fswatch >/dev/null 2>&1 || { echo "❌ fswatch not found. Install with: brew install fswatch"; exit 1; }

# Copy scripts
cp clodputer-run.sh /usr/local/bin/clodputer-run
cp clodputer-watch.sh /usr/local/bin/clodputer-watch
cp install-cron.sh /usr/local/bin/clodputer-cron-install
chmod +x /usr/local/bin/clodputer-*

# Copy task templates
cp templates/*.yaml ~/.clodputer/tasks/

echo "✅ Clodputer installed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit task configs in ~/.clodputer/tasks/"
echo "2. Install cron jobs: clodputer-cron-install"
echo "3. Start file watcher: clodputer-watch ~/todos/claude-assignments"
```

### Success Metrics
- ✅ Can schedule and execute email management task daily
- ✅ File watcher detects new markdown files and triggers tasks
- ✅ JSON output parsed correctly for success/failure
- ✅ Logs capture execution history
- ✅ Installation process is documented and repeatable

### Limitations Accepted
- No multi-turn conversation support (each task is single-shot)
- No session pooling (new instance per task)
- Basic error handling (no retries)
- Manual configuration (no UI)

---

## Phase 2: Multi-Turn Task Execution (Week 3-4)

### Goal
Enable sequential task execution with conversation continuity.

### Components

#### 2.1 Session Manager
**File**: `clodputer-session.py`

**Responsibilities**:
- Track active Claude Code sessions
- Resume conversations with `--resume SESSION_ID`
- Parse task lists into sequential prompts
- Detect task completion from responses

**Example**:
```python
#!/usr/bin/env python3
# clodputer-session.py - Manage multi-turn Claude Code sessions

import json
import subprocess
import sys
from pathlib import Path

class ClaudeSession:
    def __init__(self, task_config):
        self.config = task_config
        self.session_id = None
        self.completed_tasks = []

    def execute_task_list(self, tasks):
        """Execute a list of tasks sequentially with context"""
        for i, task in enumerate(tasks):
            print(f"Executing task {i+1}/{len(tasks)}: {task['name']}")

            prompt = task['prompt']
            if self.session_id:
                # Resume existing session
                result = self._resume_session(prompt)
            else:
                # Start new session
                result = self._start_session(prompt)

            if result['is_error']:
                print(f"Task failed: {result['result']}")
                break

            self.completed_tasks.append({
                'name': task['name'],
                'result': result['result'],
                'session_id': self.session_id
            })

        return self.completed_tasks

    def _start_session(self, prompt):
        cmd = [
            'claude', '-p', prompt,
            '--output-format', 'json',
            '--allowedTools', ','.join(self.config['allowed_tools']),
            '--permission-mode', self.config.get('permission_mode', 'acceptEdits')
        ]

        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        result = json.loads(output)
        self.session_id = result['session_id']
        return result

    def _resume_session(self, prompt):
        cmd = [
            'claude', '--resume', self.session_id,
            '-p', prompt,
            '--output-format', 'json'
        ]

        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return json.loads(output)

if __name__ == '__main__':
    config_path = sys.argv[1]
    with open(config_path) as f:
        config = json.load(f)

    session = ClaudeSession(config['task'])
    results = session.execute_task_list(config['task']['task_list'])

    print(json.dumps(results, indent=2))
```

#### 2.2 Enhanced Task Configuration
**File**: `~/.clodputer/tasks/project-execution.yaml`

**Format**:
```yaml
name: project-execution
description: Execute multi-step project from file

task:
  type: multi-turn

  task_list:
    - name: read-project-file
      prompt: |
        Read the project file at {{PROJECT_FILE}}.
        Extract the list of tasks to complete.
        Confirm you understand the project scope.

    - name: execute-tasks
      prompt: |
        Execute the first incomplete task from the project file.
        Update the task status to 🔵 in_progress.
        Complete the task fully.
        Update status to 🟢 complete or 🔴 blocked.

    - name: next-task-or-complete
      prompt: |
        Check if there are more incomplete tasks.
        If yes, execute the next task (repeat previous step).
        If no, provide final project summary.

  allowed_tools:
    - Read
    - Write
    - Edit
    - Bash
    - Grep
    - Glob

  permission_mode: acceptEdits

  completion_detection:
    # Parse response for completion indicators
    patterns:
      - "🟢 complete"
      - "all tasks completed"
      - "project finished"
```

#### 2.3 Task Completion Detection
**File**: `completion-detector.py`

**Responsibilities**:
- Parse Claude Code responses for completion signals
- Detect if more prompts are needed
- Extract structured progress updates

### Success Metrics
- ✅ Can execute 3+ sequential tasks in one session
- ✅ Context maintained across conversation turns
- ✅ Correctly detects task completion
- ✅ Updates project files with status changes

---

## Phase 3: Resource Management & Reliability (Week 5-6)

### Goal
Make Clodputer production-ready with proper resource controls and error handling.

### Components

#### 3.1 Process Manager
**File**: `clodputer-daemon.py`

**Responsibilities**:
- Track active Claude Code instances
- Enforce max concurrent instance limit
- Queue tasks when at capacity
- Monitor system resources (CPU, memory)
- Graceful shutdown handling

#### 3.2 Retry & Error Handling
**Enhancements**:
- Exponential backoff for failed tasks
- Configurable retry limits
- Dead letter queue for persistent failures
- Alert mechanism (email, Slack) for critical failures

#### 3.3 Monitoring & Observability
**Components**:
- Structured JSON logging
- Execution metrics (cost, duration, success rate)
- Dashboard for task history (optional web UI)
- Prometheus/Grafana integration (optional)

### Success Metrics
- ✅ Never exceeds configured instance limit
- ✅ Failed tasks retry automatically with backoff
- ✅ Logs provide clear debugging information
- ✅ Cost tracking alerts when budget exceeded

---

## Phase 4: Advanced Features (Week 7+)

### Optional Enhancements (Based on Usage)

#### 4.1 Session Pooling
- Maintain 2-3 warm Claude Code sessions
- Route tasks to available sessions
- Improve startup latency

#### 4.2 Web Dashboard
- View task execution history
- Configure tasks via UI
- Real-time status monitoring
- Cost analytics

#### 4.3 Cloud Integration
- Deploy to cloud VM for 24/7 operation
- Webhook triggers from external services
- Integration with n8n, Zapier, Make

#### 4.4 Team Collaboration
- Shared task templates
- Multi-user authentication
- Audit logs
- Role-based permissions

---

## Technical Dependencies

### Required
- **Claude Code**: Headless mode support
- **jq**: JSON parsing in bash
- **yq**: YAML parsing in bash
- **fswatch**: File system monitoring (macOS)
- **cron**: Task scheduling
- **Python 3.8+**: Session management scripts

### Optional
- **supervisord**: Process management (Phase 3)
- **Redis**: Task queue (Phase 3)
- **PostgreSQL**: Execution history (Phase 4)
- **Docker**: Containerized deployment (Phase 4)

---

## Development Environment Setup

### Local Development
```bash
# Clone repository
git clone https://github.com/yourusername/clodputer.git
cd clodputer

# Install dependencies
brew install jq yq fswatch python3

# Set up development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
./test.sh

# Install locally
./install.sh
```

### Testing Strategy
- **Unit tests**: Individual script components
- **Integration tests**: End-to-end task execution
- **Manual testing**: Real-world use cases (email, projects)

---

## Open Source Preparation

### Repository Structure
```
clodputer/
├── README.md                 # Project overview, installation
├── LICENSE                   # MIT or Apache 2.0
├── install.sh                # Installation script
├── requirements.txt          # Python dependencies
├── scripts/
│   ├── clodputer-run.sh      # Core orchestrator
│   ├── clodputer-watch.sh    # File watcher
│   ├── clodputer-session.py  # Session manager
│   └── clodputer-daemon.py   # Process manager (Phase 3)
├── templates/
│   ├── email-management.yaml # Task template
│   ├── project-execution.yaml
│   └── todo-automation.yaml
├── docs/
│   ├── quickstart.md
│   ├── configuration.md
│   ├── architecture.md
│   └── api-reference.md
├── tests/
│   ├── test_orchestrator.sh
│   ├── test_session.py
│   └── test_integration.sh
└── examples/
    ├── gmail-automation/
    ├── calendar-sync/
    └── code-review/
```

### Documentation
- **README.md**: Clear value proposition, quick start
- **Quickstart Guide**: 5-minute setup for first task
- **Configuration Guide**: All YAML options explained
- **Architecture Guide**: Design decisions, extensibility
- **API Reference**: For extending Clodputer

### Community Building
- **GitHub Issues**: Bug tracking, feature requests
- **Discussions**: Community Q&A, use case sharing
- **Examples Directory**: Showcase community contributions
- **Video Tutorial**: Demo common workflows

---

## Risk Mitigation

### Technical Risks

**Risk**: Claude Code API changes break Clodputer
**Mitigation**:
- Pin to specific Claude Code version in docs
- Test against beta releases
- Maintain compatibility layer

**Risk**: MCP startup time makes automation impractical
**Mitigation**:
- Start with lightweight tasks
- Implement session pooling early if validated
- Document performance expectations

**Risk**: File watcher misses events or double-triggers
**Mitigation**:
- Use debouncing logic
- Maintain state file for processed files
- Add idempotency checks

### Operational Risks

**Risk**: Runaway costs from excessive API calls
**Mitigation**:
- Implement cost tracking and alerting
- Set hard limits in config
- Require explicit opt-in for expensive operations

**Risk**: Security vulnerabilities from arbitrary code execution
**Mitigation**:
- Sandbox task execution
- Whitelist allowed tools per task
- Audit logs for all executions

---

## Success Criteria

### Phase 1 MVP
- [ ] Can execute scheduled email management task
- [ ] File watcher triggers project execution
- [ ] JSON output parsed and logged
- [ ] Installation takes < 10 minutes
- [ ] Works on macOS without additional dependencies

### Phase 2 Multi-Turn
- [ ] Project files with 5+ tasks execute fully
- [ ] Context maintained across all turns
- [ ] Task status updates reflected in source files
- [ ] Completion detection accuracy > 95%

### Phase 3 Production
- [ ] Runs continuously for 1 week without intervention
- [ ] Failed tasks retry successfully
- [ ] Cost tracking accurate within 5%
- [ ] Logs enable debugging without code inspection

### Phase 4 Community
- [ ] 100+ GitHub stars
- [ ] 10+ community-contributed task templates
- [ ] 5+ forks with meaningful extensions
- [ ] Active discussions and feature requests

---

**Next**: [Decision Matrix](04-decision-matrix.md)
