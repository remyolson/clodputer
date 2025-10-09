# Debug Logging Improvements - Analysis & Recommendations

## Current State Analysis

### ✅ What's Good
- Structured JSON format (machine parseable)
- Context tracking with stack
- Sanitization of sensitive data
- Module/function/line tracking
- Log rotation

### ❌ Pain Points for Human Readers

1. **No Visual Hierarchy** - All logs look the same, hard to scan
2. **No Correlation** - Can't easily group related logs together
3. **Technical Event Names** - `claude_command_built` vs "Building command to send to Claude"
4. **Data Overload** - Full JSON dumps overwhelm the log
5. **No Operation Boundaries** - Hard to see where operations start/end
6. **No Relative Timing** - Can't see "this happened 2s into the operation"
7. **No Search Keywords** - Hard to filter to specific issues
8. **No Summaries** - No "what happened" at operation completion
9. **Truncation Issues** - 500 char limit sometimes cuts important data awkwardly

## Recommended Improvements

### 1. Add Operation Correlation IDs

**Problem**: When onboarding runs, you get 50+ log entries but can't easily group them.

**Solution**: Add `operation_id` UUID that persists through related operations.

```json
{
  "timestamp": "2025-10-09T15:01:05.519Z",
  "operation_id": "onboard-a1b2c3d4",  // NEW: correlate related logs
  "level": "INFO",
  "event": "onboarding_started"
}
```

**Implementation**:
- Add `operation_id` to context stack
- Generate UUID at start of major operations (onboarding, task execution)
- Include in all child logs

### 2. Add Human-Readable Descriptions

**Problem**: Technical event names require developer knowledge to understand.

**Solution**: Add `description` field with plain English explanation.

```json
{
  "event": "claude_command_built",
  "description": "📝 Building command to send to Claude CLI",  // NEW
  "level": "INFO"
}
```

**Emoji Guide**:
- 📝 Building/preparing
- 🚀 Starting/launching
- ✅ Success/completed
- ❌ Error/failed
- ⏱️ Timeout
- 🔍 Detecting/searching
- 💾 Reading/loading
- ✏️ Writing/saving
- 🔧 Configuring
- 🌐 Network operation

### 3. Add Phase & Step Hierarchy

**Problem**: Flat structure makes it hard to understand context.

**Solution**: Add hierarchical tracking with `phase` and `step`.

```json
{
  "operation_id": "onboard-a1b2c3d4",
  "phase": "Claude CLI Configuration",        // NEW: major section
  "step": "Detecting Claude CLI executable",  // NEW: specific action
  "step_number": "2/7",                      // NEW: progress indicator
  "event": "claude_cli_detection_started"
}
```

### 4. Smart Data Truncation with Summaries

**Problem**: Full JSON dumps make logs unreadable, but we need the data.

**Solution**: Add `summary` field with key metrics, keep full data optional.

```json
{
  "event": "claude_response_received",
  "description": "✅ Received response from Claude",

  // NEW: Quick summary for scanning
  "summary": {
    "response_size": "2.3 KB",
    "duration": "12.5s",
    "status": "success",
    "turns": 3,
    "cost_usd": 0.0042
  },

  // Full data still available but not shown by default viewer
  "data": {
    "stdout": "... full response ...",
    "stderr": "",
    "return_code": 0
  }
}
```

### 5. Add Relative Timestamps

**Problem**: Can't easily see how long into an operation something happened.

**Solution**: Add `elapsed_seconds` from operation start.

```json
{
  "timestamp": "2025-10-09T15:01:15.519Z",
  "elapsed_seconds": 10.0,  // NEW: 10s since operation started
  "event": "claude_response_received"
}
```

### 6. Add Searchable Tags

**Problem**: Hard to filter logs to specific types of events.

**Solution**: Add `tags` array for easy filtering.

```json
{
  "event": "claude_json_parse_failed",
  "tags": ["claude", "api", "json", "error", "parse"],  // NEW
  "level": "ERROR"
}
```

Common tag categories:
- Component: `claude`, `queue`, `cron`, `mcp`, `watcher`
- Operation: `api`, `subprocess`, `file`, `network`
- Status: `success`, `error`, `warning`, `timeout`
- Type: `start`, `end`, `progress`, `state_change`

### 7. Enhanced Error Context

**Problem**: Errors don't always show what was being attempted.

**Solution**: Add `attempted` and `expected_vs_actual` fields.

```json
{
  "event": "claude_json_parse_failed",
  "level": "ERROR",
  "description": "❌ Failed to parse Claude's response as JSON",
  "attempted": "Parsing JSON response from Claude for task generation",  // NEW
  "expected_vs_actual": {  // NEW: comparison
    "expected": "Valid JSON with 'tasks' array",
    "actual": "Plain text starting with 'I apologize...'"
  },
  "troubleshooting": [  // NEW: actionable hints
    "Check if Claude CLI is in headless mode",
    "Verify --output-format json flag is set",
    "Check if prompt is causing conversational response"
  ]
}
```

### 8. Operation Summary Logs

**Problem**: No overview of what happened in an operation.

**Solution**: Add summary log at operation completion.

```json
{
  "event": "onboarding_completed",
  "description": "✅ Onboarding completed successfully",
  "level": "INFO",

  // NEW: High-level summary
  "summary": {
    "duration": "124.5s",
    "total_steps": 7,
    "completed_steps": 7,
    "warnings": 0,
    "errors": 0,
    "tasks_created": 3,
    "automation_enabled": ["cron", "watcher"],
    "claude_interactions": 2,
    "claude_total_cost": 0.0089
  },

  // NEW: Key events timeline
  "timeline": [
    {"step": 1, "name": "Directory Setup", "duration": "0.1s", "status": "success"},
    {"step": 2, "name": "Claude CLI Config", "duration": "2.3s", "status": "success"},
    {"step": 3, "name": "Task Generation", "duration": "45.2s", "status": "success"},
    // ...
  ]
}
```

### 9. Better Prompt/Response Handling

**Problem**: Full prompts/responses are too long but we need them.

**Solution**: Multi-level detail with smart truncation.

```json
{
  "event": "claude_prompt_sent",
  "description": "📝 Sending prompt to Claude",

  // Level 1: Quick preview (always shown)
  "prompt_preview": "You are helping set up Clodputer, an autonomous task... (2,450 chars total)",

  // Level 2: Structural summary
  "prompt_structure": {
    "sections": ["introduction", "mcp_context", "requirements", "output_format"],
    "instruction_count": 7,
    "example_count": 2,
    "word_count": 450
  },

  // Level 3: Full content (only in expanded view)
  "data": {
    "prompt": "... full 2450 char prompt ..."
  }
}
```

### 10. Visual Markers for Log Levels

**Problem**: All logs look the same when scanning.

**Solution**: Add visual markers based on level and event type.

```json
// Success operations
{"marker": "✅", "level": "INFO", "event": "operation_completed"}

// Errors
{"marker": "❌", "level": "ERROR", "event": "operation_failed"}

// Warnings
{"marker": "⚠️", "level": "WARNING", "event": "something_suspicious"}

// Progress
{"marker": "⏳", "level": "INFO", "event": "operation_in_progress"}

// API calls
{"marker": "🔌", "level": "INFO", "event": "claude_api_call"}

// File operations
{"marker": "📁", "level": "INFO", "event": "file_operation"}

// Network
{"marker": "🌐", "level": "INFO", "event": "network_check"}
```

## Implementation Plan

### Phase 1: Core Infrastructure (High Priority)

1. Add `operation_id` to context stack
2. Add `description` field to all log methods
3. Add `tags` field for filtering
4. Update `_write_log` to include new fields

### Phase 2: Summaries & Structure (High Priority)

1. Add `summary` extraction for large data
2. Add `phase` and `step` tracking to context
3. Add `elapsed_seconds` calculation
4. Create operation summary logs

### Phase 3: Error Improvements (Medium Priority)

1. Add `attempted` field to error logs
2. Add `expected_vs_actual` comparisons
3. Add `troubleshooting` hints
4. Add `related_logs` references

### Phase 4: Viewer Tool (Medium Priority)

Create `clodputer debug view` command that:
- Filters logs by operation_id
- Shows hierarchical view (operation > phase > step)
- Color codes by level
- Collapses large data by default
- Supports search by tags
- Shows summaries prominently

### Phase 5: Advanced Features (Low Priority)

1. Add performance metrics (memory, CPU)
2. Add log export to different formats
3. Add log analysis (patterns, anomalies)
4. Add integration with external monitoring

## Example: Before & After

### Before (Current)
```json
{"timestamp":"2025-10-09T15:01:05.519Z","level":"INFO","module":"onboarding","function":"_generate_task_suggestions","line":1122,"event":"task_generation_prompt_built","data":{"prompt":"You are helping set up Clodputer, an autonomous task automation system that runs Claude Code tasks on a schedule.\n\nAvailable MCPs in this Claude Code installation:\n- gmail: npx @gongrzhe/server-gmail-autoauth-mcp\n- calendar: npx @gongrzhe/google-calendar-mcp\n\nYour goal: Generate exactly 3 useful, safe, and immediately valuable task suggestions for this user.\n\n- Email MCP detected: Consider email triage, inbox summarization, or draft response tasks\n  Examples: morning-email-triage, newsletter-digest, urgent-email-alerts\n\n- Calendar MCP detected: Consider meeting prep, schedule analysis, or availability tasks\n  Examples: meeting-prep, schedule-optimizer, calendar-summary\n\nIMPORTANT REQUIREMENTS:\n1. Each task must be IMMEDIATELY USEFUL (not a toy example)\n2. Tasks should complete in 30-60 seconds\n3. NO destructive operations (no delete, rm, drop, uninstall commands)\n4. Use available MCPs when relevant, but don't force it\n5. Include complete, valid YAML configuration\n6. Add helpful comments in the YAML\n7. Set reasonable schedules (cron expressions)\n\nOUTPUT FORMAT (must be valid JSON):\n{\n  \"tasks\": [\n    {\n      \"name\": \"task-filename\",\n      \"description\": \"Brief user-facing description of value (1-2 sentences)\",\n      \"yaml_config\": \"Complete YAML including name, prompt, allowed_tools, trigger\",\n      \"reasoning\": \"Why this task is useful for this user (internal, not shown)\"\n    }\n  ]\n}\n\nYAML TEMPLATE for each task:\n```yaml\nname: task-name\nprompt: |\n  Clear, specific instructions for Claude.\n  Explain what to do, what tools to use, what output to produce.\nallowed_tools:\n  - tool_name_1\n  - tool_name_2\ntrigger:\n  type: cron\n  expression: \"0 9 * * *\"  # Daily at 9am\n  timezone: America/Los_Angeles\nenabled: true\n```\n\nGenerate 3 tasks now. Focus on practical value and safety.","prompt_length":2086,"mcp_count":2,"connected_mcp_count":2}}
```

### After (Proposed)
```json
{
  "timestamp": "2025-10-09T15:01:05.519Z",
  "operation_id": "onboard-a1b2c3d4",
  "elapsed_seconds": 0.0,
  "marker": "📝",
  "level": "INFO",
  "phase": "Intelligent Task Generation",
  "step": "Building prompt for Claude",
  "step_number": "3/7",
  "event": "task_generation_prompt_built",
  "description": "Building AI prompt to generate personalized task suggestions",
  "tags": ["claude", "api", "task-generation", "prompt"],

  "summary": {
    "prompt_length": "2.0 KB",
    "sections": 4,
    "mcps_detected": 2,
    "mcps_connected": 2,
    "expected_tasks": 3
  },

  "prompt_preview": "You are helping set up Clodputer, an autonomous task automation system... (2,086 chars)",

  "prompt_structure": {
    "sections": ["introduction", "mcp_context", "requirements", "output_format"],
    "mcp_examples": ["gmail", "calendar"],
    "constraints": ["30-60s runtime", "no destructive ops", "valid YAML"]
  },

  // Full prompt in data field (not shown in compact view)
  "data": {
    "prompt": "... full 2086 char prompt ...",
    "mcp_count": 2,
    "connected_mcp_count": 2
  }
}
```

## Log Viewer Examples

### Compact View (Default)
```
🚀 Onboarding Started (onboard-a1b2c3d4)

  [1/7] Directory Setup (0.1s)
    ✅ Created ~/.clodputer directories

  [2/7] Claude CLI Configuration (2.3s)
    🔍 Detecting Claude CLI... found at /usr/local/bin/claude
    ✅ Verified Claude CLI version 1.2.3

  [3/7] Intelligent Task Generation (45.2s)
    📝 Building prompt for Claude (2.0 KB, 2 MCPs detected)
    🔌 Sending request to Claude...
    ⏳ Waiting for response... (this may take 30-60s)
    ✅ Received response (3.5 KB, 3 tasks generated)
    ✅ Validated all 3 tasks

  ...

✅ Onboarding Completed (124.5s total)
   Created 3 tasks, enabled cron + watcher, 0 errors
```

### Detailed View (--verbose)
Shows full JSON for each entry, but formatted nicely with syntax highlighting.

### Error View (--errors-only)
Shows only ERROR and WARNING level logs with full context.

### Filter View
```bash
# Show only Claude interactions
clodputer debug view --tags claude,api

# Show specific operation
clodputer debug view --operation-id onboard-a1b2c3d4

# Show errors in last hour
clodputer debug view --level ERROR --since 1h

# Search for specific text
clodputer debug view --search "json parse"
```

## Migration Strategy

1. **Additive Changes**: New fields don't break existing logs
2. **Backwards Compatible**: Old logs still readable
3. **Gradual Rollout**: Add features incrementally
4. **Testing**: Ensure all tests pass with new fields
5. **Documentation**: Update examples and docs

## Benefits Summary

✅ **Easier to Scan**: Visual markers and hierarchy
✅ **Easier to Search**: Tags and correlation IDs
✅ **Easier to Understand**: Human-readable descriptions
✅ **Better Debugging**: Error context and troubleshooting hints
✅ **Better Overview**: Operation summaries and timelines
✅ **Less Overwhelming**: Smart truncation and summaries
✅ **More Actionable**: Includes troubleshooting suggestions

## Next Steps

1. Review this document and discuss priorities
2. Implement Phase 1 changes (core infrastructure)
3. Update existing log statements with new fields
4. Create log viewer tool prototype
5. Get user feedback and iterate
