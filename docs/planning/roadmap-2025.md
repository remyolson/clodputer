# Clodputer 2025 Roadmap

**Document Version:** 2.0
**Last Updated:** January 2025
**Status:** Active Development
**Current Version:** 0.1.0 (Developer Preview)

---

## 🎯 Vision & Goals

**Mission:** Make Claude Code work autonomously in the background, enabling "set it and forget it" automation that feels magical.

**Core Insight:** **Claude Code is Clodputer's primary user.** All features should prioritize making automation seamless for Claude Code during conversations with humans.

**Core Pillars:**
1. **Claude-Native First** - Deep integration with Claude Code's workflow
2. **Reliability Always** - Tasks execute consistently without surprises
3. **Delightful UX** - Onboarding and daily use feel effortless
4. **Visible Progress** - Users always know what's happening

**Target Audience:**
- Claude Code (primary user) - needs programmatic task creation
- Power users who want automation
- Knowledge workers with repetitive workflows
- Developers who want AI assistance on a schedule

---

## 📊 Current State (January 2025)

### ✅ What's Built
- **Core Engine:** Queue, executor, cron, watcher (100% functional)
- **Onboarding:** Guided setup with intelligent task generation (80% test coverage)
- **Safety:** PID tracking, atomic writes, crash recovery
- **UI:** Terminal dashboard + macOS menu bar
- **Testing:** 205 tests, 80% coverage, zero flaky tests

### 🚧 What's Missing (Critical for Claude Code)
- **No programmatic task creation** - Claude has to tell humans to edit YAML
- **No task discovery API** - Claude can't query existing tasks
- **No task state storage** - Tasks are stateless, can't remember context
- **No results API** - Claude can't check if tasks succeeded
- **Task authoring complexity** - Manual YAML editing required

### 📈 Metrics
- **Test Coverage:** 80.01%
- **Onboarding Time:** ~5-8 minutes (target: <3 minutes)
- **Task Success Rate:** Unknown (need instrumentation)
- **Claude Code Integration:** 0% (no programmatic API exists)

---

## 🗺️ Roadmap Overview

### Phase 1: Claude-Native Foundation (Weeks 1-3) 🔥
**Goal:** Enable Claude Code to create, query, and manage tasks programmatically
**Priority:** CRITICAL - Unlocks primary user workflow
**Impact:** Transforms Claude Code from documentation reader to active automation creator

### Phase 2: Core Reliability (Weeks 4-6)
**Goal:** Make background task execution bulletproof and debuggable
**Priority:** CRITICAL - Enables trust in the system

### Phase 3: Onboarding Magic (Weeks 7-9)
**Goal:** Reduce friction and create "wow" moments in first use
**Priority:** HIGH - Determines adoption

### Phase 4: Integration & Authoring (Weeks 10-12)
**Goal:** Make task creation and Claude integration seamless
**Priority:** HIGH - Enables power users

### Phase 5: UX Polish (Weeks 13-15)
**Goal:** Make dashboard and menu bar delightful
**Priority:** MEDIUM - Increases engagement

### Phase 6: Advanced Intelligence (Weeks 16-20)
**Goal:** Add silent optimization, NL generation, dependencies
**Priority:** MEDIUM - Differentiator features

### Phase 7: Community & Scale (Beyond Week 20)
**Goal:** Enable sharing, learning, optimization
**Priority:** LOW - Post-launch

---

## 📅 Phase 1: Claude-Native Foundation (Weeks 1-3) 🔥

**Timeline:** 3 weeks
**Goal:** Claude Code can create, query, and manage tasks programmatically in <30 seconds

**Philosophy:** Claude Code should never tell humans to edit YAML files. All task operations should be possible via CLI with JSON input/output.

---

### Feature 1.1: JSON Task Creation API (Week 1)
**Problem:** Claude Code has to instruct humans to manually edit YAML files

**Current painful flow:**
```
User: "Check my email daily"
Claude: "Please edit ~/.clodputer/tasks/email.yaml and add this YAML..."
Human: *manually edits file*
Claude: "Now run: clodputer run email"
```

**New seamless flow:**
```
User: "Check my email daily"
Claude: *creates task directly*
Claude: "✅ Set up 'daily-email-check' to run at 8am daily."
```

**Implementation:**
```
1. Add JSON-based task creation
   - `clodputer create-task --json '{...}'`
   - `echo '{...}' | clodputer create-task --stdin`
   - Returns: task ID, path, status as JSON

2. JSON schema validation
   - Validate against TaskConfig schema
   - Return clear error messages for invalid JSON
   - Support both full config and minimal config

3. Quick-create shortcuts
   - `clodputer create-task --name X --prompt "..." --schedule "0 8 * * *"`
   - Mix JSON and CLI args (CLI args override JSON)

4. Test immediately option
   - `clodputer create-task --json '{...}' --test`
   - Creates task and runs it once
   - Returns creation result + execution result
```

**Files to Modify:**
- `src/clodputer/cli.py` - Add create-task command
- `src/clodputer/config.py` - Add JSON serialization methods
- `tests/test_cli.py` - Test create-task command
- `docs/user/cli-reference.md` - Document new command

**Success Criteria:**
- [ ] `clodputer create-task --json` works
- [ ] `--stdin` accepts piped JSON
- [ ] Returns JSON result with task path
- [ ] Validates config before creation
- [ ] 6 new tests added

**Time Estimate:** 3-4 days

---

### Feature 1.2: Task Query & Discovery API (Week 1)
**Problem:** Claude Code can't discover what tasks already exist

**Implementation:**
```
1. Add --format json flag to existing commands
   - `clodputer list --format json`
   - `clodputer status --format json`
   - `clodputer queue --format json`
   - Returns: structured JSON instead of formatted text

2. Add task inspection command
   - `clodputer inspect <task> --format json`
   - Returns: full config + metadata
   - Include: last run, success rate, next scheduled run

3. Add task search
   - `clodputer search "email" --format json`
   - Search by: name, prompt text, tools used
   - Returns: matching tasks as JSON array

4. Add health check
   - `clodputer health-check --format json`
   - Returns: tasks with issues (failed recently, etc.)
```

**Files to Modify:**
- `src/clodputer/cli.py` - Add --format json to commands
- `src/clodputer/cli.py` - Add inspect and search commands
- `src/clodputer/formatting.py` - Add JSON formatters
- `tests/test_cli.py` - Test JSON output

**Success Criteria:**
- [ ] All list commands support --format json
- [ ] `clodputer inspect` returns full task details
- [ ] `clodputer search` finds tasks by keyword
- [ ] JSON output is valid and parseable
- [ ] 5 new tests added

**Time Estimate:** 2-3 days

---

### Feature 1.3: Task State Storage (Week 2)
**Problem:** Tasks are stateless - can't remember context between runs

**Example use case:**
```
Task: "Summarize my emails daily"
Run 1: Processes 50 emails
Run 2: Should only process NEW emails since Run 1
Current: Claude has no memory of previous run ❌
Needed: Task remembers last processed email ID ✅
```

**Implementation:**
```
1. Add state storage to task config
   state:
     enabled: true
     storage: ~/.clodputer/state/{task_name}.json
     max_size: 1MB  # Prevent unbounded growth

2. State API commands
   - `clodputer state get <task>` - read current state
   - `clodputer state get <task> --key last_id` - read specific key
   - `clodputer state set <task> --json '{...}'` - write state
   - `clodputer state clear <task>` - reset state

3. State interpolation in prompts
   - {{state.last_processed_id}} - access state in task prompt
   - {{state.processed_count}} - access counters
   - If state missing, value is empty string

4. State management in executor
   - Load state before task execution
   - Save state after task completion
   - Atomic writes to prevent corruption

5. State in task output
   - Tasks can write: {"state": {"last_id": "xyz"}}
   - Executor automatically saves to state file
```

**Files to Modify:**
- `src/clodputer/config.py` - Add StateConfig model
- `src/clodputer/state.py` - New module for state management
- `src/clodputer/executor.py` - Load/save state during execution
- `src/clodputer/cli.py` - Add state commands
- `tests/test_state.py` - Test state operations

**Success Criteria:**
- [ ] Tasks can persist state between runs
- [ ] State accessible in prompts via {{state.key}}
- [ ] CLI commands for state management work
- [ ] State survives task failures
- [ ] 8 new tests added

**Time Estimate:** 4-5 days

---

### Feature 1.4: Quick Task Modification (Week 2)
**Problem:** Updating tasks requires manual YAML editing

**Implementation:**
```
1. Modify command
   - `clodputer modify <task> --schedule "0 9 * * *"`
   - `clodputer modify <task> --prompt "New prompt"`
   - `clodputer modify <task> --add-tool mcp__calendar`
   - `clodputer modify <task> --remove-tool Read`
   - `clodputer modify <task> --timeout 300`
   - `clodputer modify <task> --enable`
   - `clodputer modify <task> --disable`

2. Atomic updates
   - Read current config
   - Apply modification
   - Validate new config
   - Write atomically (backup created)

3. Bulk modifications
   - `clodputer modify <task> --json '{"schedule": "...", "timeout": 300}'`
   - Apply multiple changes in one command

4. Dry-run mode
   - `clodputer modify <task> --schedule "..." --dry-run`
   - Shows what would change without applying
```

**Files to Modify:**
- `src/clodputer/cli.py` - Add modify command
- `src/clodputer/config.py` - Add atomic update methods
- `tests/test_cli.py` - Test modify command

**Success Criteria:**
- [ ] Can modify schedule, prompt, tools, timeout
- [ ] Changes validated before applying
- [ ] Backup created before modification
- [ ] Dry-run shows changes without applying
- [ ] 5 new tests added

**Time Estimate:** 2-3 days

---

### Feature 1.5: Results API (Week 3)
**Problem:** Claude Code can't check if tasks succeeded

**Implementation:**
```
1. JSON results format
   - `clodputer results <task> --latest --format json`
   - Returns: {status, duration, output, error, timestamp}

2. Results summary
   - `clodputer results <task> --summary --since "7 days"`
   - Returns: {runs, success, failure, avg_duration}

3. Filter results
   - `clodputer results <task> --failed --format json`
   - `clodputer results <task> --limit 10 --format json`

4. Health check
   - `clodputer health-check --format json`
   - Returns: tasks needing attention
   - Criteria: recent failures, long runtime, etc.
```

**Files to Modify:**
- `src/clodputer/cli.py` - Add --format json to results
- `src/clodputer/cli.py` - Add health-check command
- `src/clodputer/executor.py` - Ensure results saved as JSON
- `tests/test_cli.py` - Test results commands

**Success Criteria:**
- [ ] Results available in JSON format
- [ ] Summary provides useful stats
- [ ] Health check identifies problem tasks
- [ ] Results persist across task runs
- [ ] 4 new tests added

**Time Estimate:** 2-3 days

---

### Feature 1.6: CLAUDE.md Integration Guide (Week 3)
**Problem:** Claude Code doesn't know how to use new APIs

**Implementation:**
```
1. Add comprehensive Clodputer section to CLAUDE.md template

   ## Clodputer: Autonomous Task Automation (For Claude Code)

   When the user requests automation, use these commands:

   ### Create a task (programmatically)
   clodputer create-task --json '{
     "name": "daily-email-check",
     "schedule": "0 8 * * *",
     "task": {
       "prompt": "Check my email and draft responses",
       "allowed_tools": ["mcp__gmail", "Read", "Write"]
     }
   }'

   ### Check existing tasks
   clodputer list --format json | jq '.[] | {name, schedule}'

   ### Get task details
   clodputer inspect daily-email-check --format json

   ### Check results
   clodputer results daily-email-check --latest --format json

   ### Modify task
   clodputer modify daily-email-check --schedule "0 9 * * *"

   ### Manage task state
   clodputer state get daily-email-check
   clodputer state set daily-email-check --json '{"last_id": "xyz"}'

   ### Use state in prompts
   Your last run processed {{state.processed_count}} emails.
   Continue from email ID {{state.last_email_id}}.

2. Example workflows
   - Email automation with state
   - File watching with results checking
   - Multi-step tasks with dependencies (coming in Phase 6)

3. Best practices
   - Always check if task exists before creating
   - Use state for incremental processing
   - Check results before reporting success
   - Use --dry-run for safety
```

**Files to Modify:**
- `docs/planning/CLAUDE-MD-ADDITION.md` - Update with new section
- `src/clodputer/onboarding.py` - Include in CLAUDE.md during init
- `docs/user/claude-code-integration.md` - New guide for users

**Success Criteria:**
- [ ] CLAUDE.md has comprehensive Clodputer section
- [ ] Examples cover common use cases
- [ ] Quick reference for all commands
- [ ] Best practices documented
- [ ] Integration guide for users

**Time Estimate:** 1-2 days

---

### Phase 1 Deliverables

**What Ships:**
- JSON task creation (`create-task --json`)
- Task discovery API (`list --format json`, `inspect`, `search`)
- Task state storage (`state get/set`)
- Quick modification (`modify --<option>`)
- Results API (`results --format json`)
- CLAUDE.md integration guide

**Metrics to Track:**
- % of tasks created via JSON API vs manual YAML
- Time from user request to task scheduled (target: <30s)
- % of Claude Code sessions using Clodputer
- Task creation success rate (target: >95%)

**Documentation Updates:**
- CLI reference with all new commands
- Claude Code integration guide
- State management guide
- JSON API examples

**Testing:**
- +28 new tests
- Coverage target: 83%
- Integration test: Claude Code creates, modifies, queries task

**Success:** Claude Code can create and manage tasks in <30 seconds with zero manual YAML editing.

---

## 📅 Phase 2: Core Reliability (Weeks 4-6)

**Timeline:** 3 weeks
**Goal:** Users trust that tasks execute reliably and can debug when they don't

### Feature 2.1: Task Execution Reports (Week 4)
**Problem:** When tasks fail, users have no easy way to understand why

**Implementation:**
```
1. Create output directory structure
   - ~/.clodputer/outputs/<task-name>/
   - Store results as: YYYY-MM-DD_HH-MM-SS.json

2. Extend executor.py to save task results
   - Save full TaskExecutionResult as JSON
   - Include: status, duration, return_code, stdout, stderr, error
   - Add markdown summary: <timestamp>.md

3. Add result viewing command (enhanced from Phase 1)
   - Already have `clodputer results` from Phase 1
   - Add markdown report generation
   - Add result comparison (this run vs last run)
```

**Files to Modify:**
- `src/clodputer/executor.py` - Save detailed results
- `src/clodputer/cli.py` - Enhance results command
- `src/clodputer/formatting.py` - Add result formatters

**Success Criteria:**
- [ ] Detailed results saved for every execution
- [ ] Markdown reports generated automatically
- [ ] Results include full debugging info
- [ ] 4 new tests added

**Time Estimate:** 2-3 days

---

### Feature 2.2: Enhanced Retry Logic (Week 5)
**Problem:** Tasks fail transiently and aren't retried intelligently

**Implementation:**
```
1. Add retry configuration to task YAML/JSON
   retry:
     enabled: true
     max_attempts: 3
     backoff: exponential
     initial_delay: 60
     max_delay: 3600

2. Enhance executor retry logic
   - Calculate next retry time with backoff
   - Store retry attempt count in queue metadata
   - Log retry attempts with reasoning

3. Add retry status to queue
   - Show "Retry 2/3 in 4m" in status output
   - Display retry history in task results
```

**Files to Modify:**
- `src/clodputer/config.py` - Add RetryConfig model
- `src/clodputer/executor.py` - Implement backoff logic
- `src/clodputer/queue.py` - Store retry metadata

**Success Criteria:**
- [ ] Retry configuration validated from YAML/JSON
- [ ] Exponential backoff works correctly
- [ ] Retry attempts logged clearly
- [ ] 6 new tests added

**Time Estimate:** 3-4 days

---

### Feature 2.3: Task Execution Monitoring (Week 6)
**Problem:** No visibility into long-running tasks

**Implementation:**
```
1. Add progress reporting to executor
   - Tasks write to: ~/.clodputer/progress/<task-id>.json
   - Format: { "percent": 45, "message": "Processing emails", "step": "2/5" }

2. Display progress in dashboard
   - Show progress bar for running task
   - Display current message and step
   - Update in real-time (1s refresh)

3. Add progress to task results
   - Store progress timeline in result
   - Show progress checkpoints
```

**Files to Modify:**
- `src/clodputer/executor.py` - Read progress file
- `src/clodputer/logger.py` - Add progress events
- `src/clodputer/dashboard.py` - Display progress

**Success Criteria:**
- [ ] Progress file format documented
- [ ] Dashboard shows progress bar
- [ ] Progress included in results
- [ ] 4 new tests added

**Time Estimate:** 3-4 days

---

### Phase 2 Deliverables

**What Ships:**
- Detailed execution reports
- Smart retry with exponential backoff
- Progress monitoring for long-running tasks

**Metrics to Track:**
- Task success rate (target: >95%)
- Average retry count per failed task
- Time to debug failed task (target: <2 min)

**Testing:**
- +14 new tests
- Coverage target: 85%

---

## 📅 Phase 3: Onboarding Magic (Weeks 7-9)

**Timeline:** 3 weeks
**Goal:** First-time users get value in under 3 minutes

### Feature 3.1: Express Mode (Week 7)
- 60-second onboarding
- Auto-generate 1 task
- Test immediately
- Schedule automatically

### Feature 3.2: Task Creation Wizard (Week 8)
- Interactive task creation
- Smart defaults
- Validation during creation
- Test before scheduling

### Feature 3.3: Onboarding Analytics (Week 9)
- Track friction points (opt-in)
- Optimize based on data
- Feedback collection

**Phase 3 Deliverables:**
- Express mode for rapid setup
- Interactive task wizard
- Data-driven onboarding optimization

---

## 📅 Phase 4: Integration & Authoring (Weeks 10-12)

**Timeline:** 3 weeks
**Goal:** Make task creation and Claude integration seamless

### Feature 4.1: CLAUDE.md Auto-Update (Week 10)
- Version tracking for CLAUDE.md
- Automatic upgrade notifications
- Preserve user customizations

### Feature 4.2: Task Testing Framework (Week 11)
- Dry-run validation
- Quick test mode
- Error simulation

### Feature 4.3: Template Library (Week 12)
- 12+ task templates
- Categorization by use case
- Customization wizard

**Phase 4 Deliverables:**
- CLAUDE.md stays current
- Task testing before deployment
- Rich template library

---

## 📅 Phase 5: UX Polish (Weeks 13-15)

**Timeline:** 3 weeks
**Goal:** Dashboard and menu bar feel responsive and delightful

### Feature 5.1: Real-Time Dashboard (Week 13)
- Live output streaming
- File-based event tailing
- Syntax highlighting

### Feature 5.2: Enhanced Menu Bar (Week 14)
- Quick-run menu
- Badge counts
- Recent failures submenu

### Feature 5.3: Visual Polish (Week 15)
- Loading animations
- Keyboard shortcuts
- Success celebrations

**Phase 5 Deliverables:**
- Real-time task monitoring
- Enhanced menu bar
- Delightful visual polish

---

## 📅 Phase 6: Advanced Intelligence (Weeks 16-20)

**Timeline:** 5 weeks
**Goal:** Silent optimization, NL generation, task dependencies

### Feature 6.1: Silent Task Optimization (Week 16-17)
- Automatic config tuning
- Prompt enrichment from history
- Resource optimization
- Zero user-facing notifications

### Feature 6.2: Passive Analytics (Week 18)
- Background metrics collection
- User-initiated reports only
- Performance insights on demand

### Feature 6.3: Silent Self-Healing (Week 19)
- Automatic failure recovery
- Pattern-based fixes
- Learning knowledge base

### Feature 6.4: Natural Language Task Generation (Week 19)
**From Claude-Native features:**
```bash
clodputer generate-task \
  --description "Check my email every morning at 8am"

# Uses Claude CLI to convert description → task config
# Validates and creates automatically
```

### Feature 6.5: Task Dependencies (Week 20)
**From Claude-Native features:**
```yaml
name: send-summary
depends_on:
  - task: process-emails
    condition: success
    max_age: 3600
```

**Phase 6 Deliverables:**
- Silent optimization
- Passive analytics
- Self-healing
- Natural language task creation
- Task dependencies & chaining

**Philosophy:** All intelligence is silent or passive. Zero notifications to user.

---

## 📅 Phase 7: Community & Scale (Beyond Week 20)

**Timeline:** Ongoing
**Goal:** Enable sharing, learning, scaling

### Future Features
- Task marketplace
- Multi-machine sync
- Web dashboard
- Plugin system
- Team features
- Advanced scheduling

---

## 📊 Success Metrics

### Claude Code Integration (New - Most Important)
- **Programmatic Task Creation:** >80% via JSON API
- **Time to Task Creation:** <30 seconds (from user request)
- **Claude Code Sessions Using Clodputer:** >50%
- **Task Creation Success Rate:** >95%

### User Adoption
- **Onboarding Completion Rate:** >90%
- **Time to First Task:** <3 minutes
- **Active Users (7-day):** Track growth
- **Retention (30-day):** >70%

### Reliability
- **Task Success Rate:** >95%
- **Crash Rate:** <0.1%
- **Data Loss Rate:** 0%
- **Uptime (cron/watcher):** >99.9%

### Engagement
- **Tasks per User:** >5 within first week
- **Daily Active Users:** 50% of onboarded
- **Task Executions per Day:** >10 per active user
- **State Usage:** >60% of tasks use state storage

### Quality
- **Test Coverage:** >85%
- **User Satisfaction:** >4.5/5
- **Bug Reports:** <5 per week

---

## 🎯 Release Schedule

### v0.2.0 (Week 3) - "Claude-Native Release" 🔥
- JSON task creation API
- Task query/discovery
- Task state storage
- Quick modification CLI
- Results API
- CLAUDE.md integration

### v0.3.0 (Week 6) - "Reliability Release"
- Detailed execution reports
- Enhanced retry logic
- Progress monitoring

### v0.4.0 (Week 9) - "Onboarding Release"
- Express mode
- Task creation wizard
- Onboarding analytics

### v0.5.0 (Week 12) - "Integration Release"
- CLAUDE.md auto-update
- Task testing framework
- Template library

### v0.6.0 (Week 15) - "UX Release"
- Real-time dashboard
- Enhanced menu bar
- Visual polish

### v0.7.0 (Week 20) - "Intelligence Release"
- Silent optimization
- Passive analytics
- Self-healing
- NL task generation
- Task dependencies

### v1.0.0 (Week 24) - "Production Release"
- All Phase 1-6 features complete
- Comprehensive documentation
- User testing incorporated
- Production-ready stability

---

## 🚧 Known Risks & Mitigations

### Risk: Claude Code API Complexity
**Mitigation:** Start simple (JSON in/out), iterate based on usage

### Risk: State Storage Unbounded Growth
**Mitigation:** Enforce size limits, add cleanup policies

### Risk: Breaking Changes to JSON Schema
**Mitigation:** Version JSON schema, support migration

### Risk: Feature Creep
**Mitigation:** Strict phase boundaries, user testing between phases

### Risk: Claude API Changes
**Mitigation:** Version detection, graceful degradation

---

## 🎓 Learning & Iteration

### After Each Phase
1. **User Testing** (5-10 users)
2. **Claude Code Testing** (real conversations)
3. **Metrics Review** (compare to targets)
4. **Retrospective** (what worked, what didn't)
5. **Roadmap Adjustment** (re-prioritize based on learning)

### Continuous Feedback
- Weekly check-ins with early users
- Claude Code integration testing
- GitHub issues for feature requests
- Discord/Slack for quick feedback

---

## 💡 Example: Ideal Claude Code Workflow (Phase 1 Complete)

**User:** "Can you check my email every morning and draft responses to urgent messages?"

**Claude Code:**
```bash
# 1. Check if similar task exists
clodputer list --format json | jq '.[] | select(.name | contains("email"))'

# 2. Create task programmatically
clodputer create-task --json '{
  "name": "daily-email-check",
  "enabled": true,
  "schedule": "0 8 * * *",
  "task": {
    "prompt": "Check my email and draft responses to urgent messages. Use state to track processed emails.",
    "allowed_tools": ["mcp__gmail", "Read", "Write"],
    "timeout": 300
  },
  "state": {
    "enabled": true
  }
}' --test

# 3. Check result
clodputer results daily-email-check --latest --format json

# 4. Confirm to user
```

**Claude Code (to user):** "✅ I've set up 'daily-email-check' to run at 8am daily. Just tested it - drafted 3 responses. The task will remember which emails it's processed so it won't duplicate work."

**Time:** <30 seconds
**Manual YAML editing:** 0
**Human intervention:** 0

---

## 📝 Appendices

### Appendix A: Why Claude-Native First?

**The Problem:**
Currently, when a user asks Claude Code to automate something, Claude has to:
1. Explain what Clodputer is
2. Tell the user to manually create a YAML file
3. Guide them through the YAML structure
4. Tell them to run `clodputer run <task>`
5. Hope they did it correctly

This is a **terrible experience** for both Claude and the user.

**The Solution:**
With Phase 1 complete, Claude Code can:
1. Create task in one command
2. Test it immediately
3. Report results
4. Done

This is **transformative** for the primary user (Claude Code).

### Appendix B: Technical Debt
- [ ] Split onboarding.py into submodules
- [ ] Add property-based testing (Hypothesis)
- [ ] Implement log retention policy
- [ ] Create architecture diagrams
- [ ] Add JSON schema versioning

### Appendix C: Documentation Roadmap
- [ ] Video walkthrough (3 min quick start)
- [ ] Claude Code integration examples
- [ ] State management patterns
- [ ] JSON API reference
- [ ] Troubleshooting guide

---

**Document Status:** Living document, updated monthly
**Next Review:** February 2025
**Owner:** Rémy Olson
**Contributors:** Claude Code team

---

*Phase 1 unlocks everything else. Claude-Native features first, reliability second, delight third.*
