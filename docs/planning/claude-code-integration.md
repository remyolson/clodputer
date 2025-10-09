# Claude Code Integration: Making Clodputer Native to AI Workflows

**Document Version:** 1.0
**Created:** January 2025
**Purpose:** Design features that make Clodputer feel native to Claude Code

---

## 🎯 Core Insight

**Clodputer's primary user is Claude Code, not humans.**

When a human asks Claude Code to "check my email daily," Claude Code should be able to:
1. Instantly create the task
2. Test it immediately
3. Schedule it without human YAML editing
4. Remember context for future runs

This document outlines features that make this workflow seamless.

---

## 🚧 Current Friction Points

### 1. **Task Creation Requires YAML Editing**
**Problem:** Claude Code has to instruct humans to manually edit YAML files.

**Current flow:**
```
Human: "Can you check my email daily?"
Claude: "I'll help you set up a task..."
Claude: "Please edit ~/.clodputer/tasks/email-check.yaml and add this YAML..."
Human: *manually edits file*
Human: "Okay, done"
Claude: "Now run: clodputer run email-check"
```

**Friction:** 3-step process, human must edit files, error-prone

---

### 2. **No Programmatic Task Creation**
**Problem:** Claude Code can't create tasks directly via CLI/API.

**What Claude Code needs:**
```bash
# Claude Code should be able to do this:
clodputer create-task \
  --name daily-email-check \
  --prompt "Check my email and draft responses to urgent messages" \
  --schedule "0 8 * * *" \
  --tools mcp__gmail,Read,Write \
  --priority normal
```

**Current workaround:** Template export + manual editing

---

### 3. **No Task Discovery/Query API**
**Problem:** Claude Code can't easily ask "What tasks exist?"

**What Claude Code needs:**
```bash
# Query tasks by status
clodputer list --format json --filter enabled

# Find tasks by keyword
clodputer search "email"

# Get task details
clodputer inspect daily-email-check --format json
```

**Current workaround:** Read YAML files manually

---

### 4. **No Context Persistence Between Runs**
**Problem:** Each task execution is stateless. Claude can't remember previous runs.

**Example use case:**
- Task: "Summarize my emails daily"
- Run 1: Processes 50 emails
- Run 2: Should only process NEW emails since Run 1
- Current: Claude has no memory of what it processed before

**What's needed:**
- Task-specific state storage
- Context sharing between runs
- Memory of previous decisions

---

### 5. **No Easy Task Modification**
**Problem:** Updating a task requires YAML editing again.

**What Claude Code needs:**
```bash
# Modify existing task
clodputer modify daily-email-check --schedule "0 9 * * *"
clodputer modify daily-email-check --add-tool mcp__google-calendar
clodputer modify daily-email-check --prompt "New prompt text here"
```

**Current workaround:** Re-edit YAML file

---

### 6. **No Natural Language Task Definition**
**Problem:** Claude Code has to construct YAML, not just describe intent.

**What would be magical:**
```bash
# Claude Code describes the task in plain English
clodputer create-from-description \
  "Check my email every morning at 8am and draft responses to urgent messages. \
   Use Gmail MCP and save drafts. If there are more than 5 urgent emails, \
   send me a summary instead."

# Clodputer generates valid task config automatically
# Claude Code reviews and confirms
```

---

### 7. **No Feedback Loop to Claude Code**
**Problem:** After scheduling a task, Claude Code has no easy way to check results.

**What's needed:**
```bash
# Get last execution result
clodputer last-result daily-email-check --format json

# Get summary of recent runs
clodputer summary daily-email-check --since "7 days ago"

# Check if task needs attention
clodputer health-check
```

---

### 8. **No Task Chaining / Dependencies**
**Problem:** Claude Code can't set up workflows where Task B runs after Task A succeeds.

**What's needed:**
```yaml
# Task B only runs if Task A succeeded
name: send-email-summary
depends_on:
  - task: process-emails
    condition: success
    max_age: 1h  # Must have run within last hour
```

---

## ✨ Proposed Features for Phase "Claude-Native"

### Feature CN.1: JSON-Based Task Creation API

**Implementation:**
```bash
# Create task from JSON input
clodputer create-task --json '{
  "name": "daily-email-check",
  "enabled": true,
  "priority": "normal",
  "schedule": "0 8 * * *",
  "task": {
    "prompt": "Check email and draft responses",
    "allowed_tools": ["mcp__gmail", "Read", "Write"],
    "timeout": 300
  }
}'

# Or from stdin (for Claude Code to pipe)
echo '$task_json' | clodputer create-task --stdin

# Returns: Task ID and path to created file
{
  "task_id": "daily-email-check",
  "path": "~/.clodputer/tasks/daily-email-check.yaml",
  "status": "created"
}
```

**Why:** Claude Code can generate JSON easily, no YAML manipulation needed.

**Priority:** **CRITICAL** - Unblocks programmatic task creation

---

### Feature CN.2: Task Query & Discovery API

**Implementation:**
```bash
# List all tasks as JSON
clodputer list --format json
# Returns: [{"name": "...", "enabled": true, "schedule": "...", ...}]

# Search tasks by keyword
clodputer search "email" --format json

# Get detailed task info
clodputer inspect daily-email-check --format json
# Returns: Full task config + metadata (last run, success rate, etc.)

# Query by status
clodputer list --filter enabled --format json
clodputer list --filter scheduled --format json
clodputer list --filter failed-recently --format json
```

**Why:** Claude Code can discover and reason about existing automation.

**Priority:** **HIGH** - Enables Claude to be aware of existing tasks

---

### Feature CN.3: Task Context Storage

**Implementation:**
```yaml
# Add to task config:
state:
  enabled: true
  storage: ~/.clodputer/state/{task_name}.json
  max_size: 1MB
```

**API:**
```bash
# Claude Code can read/write task state
clodputer state get daily-email-check
# Returns: {"last_processed_email_id": "...", "processed_count": 50}

clodputer state set daily-email-check --json '{"last_processed_email_id": "xyz"}'
```

**In task prompts:**
```
Your last run processed 50 emails. The last email ID was: {{state.last_processed_email_id}}
Continue from there.
```

**Why:** Enables stateful automation - tasks remember context between runs.

**Priority:** **CRITICAL** - Transforms tasks from stateless to stateful

---

### Feature CN.4: Quick Task Modification CLI

**Implementation:**
```bash
# Modify schedule
clodputer modify daily-email-check --schedule "0 9 * * *"

# Add tools
clodputer modify daily-email-check --add-tool mcp__google-calendar

# Update prompt
clodputer modify daily-email-check --prompt "New prompt text"

# Enable/disable
clodputer modify daily-email-check --enable
clodputer modify daily-email-check --disable

# Returns: Updated task config
```

**Why:** Claude Code can adjust tasks without YAML editing.

**Priority:** **HIGH** - Reduces friction for task updates

---

### Feature CN.5: Natural Language Task Generation

**Implementation:**
```bash
# Claude Code sends plain English description
clodputer generate-task \
  --description "Check my email every morning at 8am and draft responses" \
  --dry-run

# Clodputer uses Claude CLI to generate task config
# Returns proposed YAML for review

# If approved:
clodputer generate-task \
  --description "..." \
  --create
```

**Under the hood:**
- Uses Claude CLI with a meta-prompt
- Prompt: "Convert this user request into a valid Clodputer task YAML: {description}"
- Validates generated YAML
- Offers preview before creation

**Why:** Claude Code can create tasks from conversation without manual config.

**Priority:** **MEDIUM** - Nice-to-have, but powerful UX improvement

---

### Feature CN.6: Execution Results API

**Implementation:**
```bash
# Get last execution result
clodputer results daily-email-check --latest --format json
# Returns: {"status": "success", "duration": 12.5, "output": {...}}

# Get execution summary
clodputer results daily-email-check --summary --since "7 days"
# Returns: {"runs": 7, "success": 6, "failure": 1, "avg_duration": 10.2}

# Health check for all tasks
clodputer health-check --format json
# Returns: Tasks that failed recently or need attention
```

**Why:** Claude Code can check if automation is working without human intervention.

**Priority:** **HIGH** - Enables proactive monitoring

---

### Feature CN.7: Task Dependencies & Chaining

**Implementation:**
```yaml
name: send-email-summary
depends_on:
  - task: process-emails
    condition: success  # or: failure, always, any
    max_age: 3600  # Must have run in last hour

# Or: Sequential execution
chain:
  - task: fetch-data
  - task: process-data
    if: previous.status == "success"
  - task: send-report
    if: all_previous.status == "success"
```

**CLI:**
```bash
# Run a chain
clodputer chain run fetch-process-send

# Define a chain
clodputer chain create my-workflow \
  --tasks "fetch-data,process-data,send-report" \
  --stop-on-failure
```

**Why:** Enables complex workflows, not just isolated tasks.

**Priority:** **MEDIUM** - Powerful but can be deferred to Phase 6

---

### Feature CN.8: Claude Code Helper Functions

**Add to CLAUDE.md:**
```markdown
## Clodputer Helper Commands (For Claude Code)

When the user asks for automation, use these shortcuts:

### Create a task quickly
clodputer create-task --json '{...}'

### Check existing automation
clodputer list --format json | jq '.[] | {name, schedule}'

### Get task results
clodputer results <task> --latest --format json

### Modify existing task
clodputer modify <task> --schedule "0 9 * * *"

### Check task health
clodputer health-check --format json

### View task state
clodputer state get <task>

### Update task state
clodputer state set <task> --json '{...}'
```

**Why:** Claude Code has quick reference during conversations.

**Priority:** **HIGH** - Documentation is critical for adoption

---

## 📋 Implementation Roadmap

### Phase CN.1: Core Programmatic Interface (Week 1-2)
**Goal:** Enable Claude Code to create and query tasks programmatically

**Features:**
- CN.1: JSON-based task creation
- CN.2: Task query & discovery API
- CN.4: Quick task modification

**Deliverables:**
- `clodputer create-task --json`
- `clodputer list --format json`
- `clodputer inspect <task> --format json`
- `clodputer modify <task> --<option>`

**Success Criteria:**
- Claude Code can create task without YAML editing
- Claude Code can query all tasks as JSON
- Claude Code can modify tasks via CLI

---

### Phase CN.2: Task State & Results (Week 3)
**Goal:** Enable stateful automation and result tracking

**Features:**
- CN.3: Task context storage
- CN.6: Execution results API

**Deliverables:**
- `clodputer state get/set <task>`
- State interpolation in task prompts: `{{state.key}}`
- `clodputer results <task> --format json`
- `clodputer health-check --format json`

**Success Criteria:**
- Tasks can persist state between runs
- Claude Code can check task results programmatically

---

### Phase CN.3: Advanced Workflows (Week 4-5)
**Goal:** Enable complex automation patterns

**Features:**
- CN.5: Natural language task generation
- CN.7: Task dependencies & chaining

**Deliverables:**
- `clodputer generate-task --description "..."`
- Dependency configuration in YAML
- `clodputer chain` commands

**Success Criteria:**
- Claude Code can generate tasks from descriptions
- Tasks can depend on other tasks

---

### Phase CN.4: Documentation & Polish (Week 6)
**Goal:** Make Clodputer feel native to Claude Code workflows

**Features:**
- CN.8: CLAUDE.md helper reference
- Examples in documentation
- Video/GIF demos for README

**Deliverables:**
- Updated CLAUDE.md with Clodputer helpers
- Example conversations showing automation creation
- Integration guide for Claude Code users

---

## 🎯 Success Metrics

**Adoption:**
- % of Claude Code sessions that create at least 1 task
- Time from "user request" to "task scheduled" (target: <60s)

**Usability:**
- % of tasks created via JSON API vs manual YAML
- % of conversations where Claude Code modifies existing tasks

**Effectiveness:**
- Task success rate for Claude-generated tasks (target: >90%)
- % of tasks using state persistence

---

## 💡 Example: Ideal Claude Code Workflow

**User:** "Can you check my email every morning and draft responses to urgent messages?"

**Claude Code (internally):**
1. Query existing tasks: `clodputer list --format json`
2. Check if similar task exists (avoid duplicates)
3. Generate task definition using internal logic
4. Create task: `clodputer create-task --json '{...}'`
5. Test immediately: `clodputer run daily-email-check`
6. Schedule: Already in task config, just need to install cron
7. Confirm to user: "✅ I've set up 'daily-email-check' to run at 8am daily."

**Time:** <30 seconds
**User YAML editing:** 0
**Manual steps:** 0

---

## 🚀 Quick Wins

**Immediate improvements** that unblock Claude Code:

1. **Add `--format json` to all list commands** (1 day)
2. **Add `clodputer create-task --json`** (2 days)
3. **Add `clodputer modify <task> --<option>`** (2 days)
4. **Add task state storage** (3 days)
5. **Update CLAUDE.md with helper commands** (1 day)

**Total:** ~2 weeks for massive usability improvement

---

## 📚 Appendix: Related Features

### From Existing Roadmap:
- **Phase 2: Feature 2.2** - Task Creation Wizard (interactive, human-focused)
- **Phase 3: Feature 3.1** - CLAUDE.md Auto-Update
- **Phase 3: Feature 3.2** - Task Testing Framework
- **Phase 5: Feature 5.1** - Silent Task Optimization

### Differences:
- **Existing roadmap focuses on human UX**
- **This document focuses on Claude Code UX**
- Both are important, but Claude Code features should come first
- Claude Code can then help humans create tasks

---

**Document Status:** ✅ INTEGRATED into roadmap-2025.md
**Integration Date:** January 2025

All Claude-Native features have been integrated as **Phase 1** of the main roadmap.

See: `docs/planning/roadmap-2025.md` - Phase 1: Claude-Native Foundation (Weeks 1-3)

---

*Making Clodputer feel like a native extension of Claude Code, not an external tool.*
