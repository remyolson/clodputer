# Debug Logging: Before & After Examples

## Scenario: Running `clodputer --debug init` with Task Generation Failure

### CURRENT STATE (What You See Now)

```
🐛 Debug mode enabled
   Logs writing to ~/.clodputer/debug.log
🪟  Debug log window opened
```

**In debug.log** (raw JSON, one per line):
```json
{"timestamp":"2025-10-09T15:01:05.519Z","level":"INFO","module":"onboarding","function":"run_onboarding","line":199,"event":"onboarding_started","data":{"reset":false}}
{"timestamp":"2025-10-09T15:01:05.520Z","level":"INFO","module":"onboarding","function":"_ensure_directories","line":260,"event":"directory_setup_started"}
{"timestamp":"2025-10-09T15:01:05.521Z","level":"INFO","module":"onboarding","function":"_ensure_directories","line":263,"event":"directory_created","data":{"path":"~/.clodputer","purpose":"queue and state management"}}
{"timestamp":"2025-10-09T15:01:05.522Z","level":"INFO","module":"onboarding","function":"_ensure_directories","line":266,"event":"directory_created","data":{"path":"~/.clodputer/tasks","purpose":"task YAML configurations"}}
{"timestamp":"2025-10-09T15:01:05.523Z","level":"INFO","module":"onboarding","function":"_ensure_directories","line":269,"event":"directory_created","data":{"path":"~/.clodputer/logs","purpose":"execution logs"}}
{"timestamp":"2025-10-09T15:01:05.524Z","level":"INFO","module":"onboarding","function":"_ensure_directories","line":272,"event":"directory_created","data":{"path":"~/.clodputer/archive","purpose":"archived task results"}}
{"timestamp":"2025-10-09T15:01:05.525Z","level":"INFO","module":"onboarding","function":"_ensure_directories","line":279,"event":"directory_setup_completed"}
{"timestamp":"2025-10-09T15:01:05.530Z","level":"INFO","module":"onboarding","function":"_choose_claude_cli","line":343,"event":"claude_cli_detection_started"}
{"timestamp":"2025-10-09T15:01:05.531Z","level":"INFO","module":"onboarding","function":"_choose_claude_cli","line":347,"event":"claude_cli_candidate_found","data":{"path":"/usr/local/bin/claude"}}
{"timestamp":"2025-10-09T15:01:07.234Z","level":"INFO","module":"onboarding","function":"_choose_claude_cli","line":352,"event":"claude_cli_candidate_accepted","data":{"path":"/usr/local/bin/claude"}}
{"timestamp":"2025-10-09T15:01:07.235Z","level":"INFO","module":"onboarding","function":"_verify_claude_cli","line":941,"event":"claude_cli_verification_started","data":{"path":"/usr/local/bin/claude"}}
{"timestamp":"2025-10-09T15:01:08.123Z","level":"INFO","module":"onboarding","function":"_verify_claude_cli","line":951,"event":"claude_cli_version_check","data":{"command":"/usr/local/bin/claude --version","return_code":0,"stdout_length":23,"stderr_length":0}}
{"timestamp":"2025-10-09T15:01:08.124Z","level":"INFO","module":"onboarding","function":"_verify_claude_cli","line":979,"event":"claude_cli_version_detected","data":{"version":"Claude CLI v1.2.3"}}
{"timestamp":"2025-10-09T15:01:08.125Z","level":"INFO","module":"onboarding","function":"_detect_available_mcps","line":1284,"event":"mcp_detection_started"}
{"timestamp":"2025-10-09T15:01:08.126Z","level":"INFO","module":"onboarding","function":"_detect_available_mcps","line":1295,"event":"mcp_list_command_starting","data":{"command":"/usr/local/bin/claude mcp list"}}
{"timestamp":"2025-10-09T15:01:10.234Z","level":"INFO","module":"onboarding","function":"_detect_available_mcps","line":1306,"event":"mcp_list_command_completed","data":{"command":"/usr/local/bin/claude mcp list","return_code":0,"stdout_length":456,"stderr_length":0}}
{"timestamp":"2025-10-09T15:01:10.235Z","level":"INFO","module":"onboarding","function":"_detect_available_mcps","line":1320,"event":"mcp_detection_completed","data":{"mcp_count":3,"mcps":["gmail","calendar","crawl4ai"]}}
{"timestamp":"2025-10-09T15:01:10.236Z","level":"INFO","module":"onboarding","function":"_generate_task_suggestions","line":1106,"event":"task_generation_started","data":{"mcp_count":3}}
{"timestamp":"2025-10-09T15:01:10.240Z","level":"INFO","module":"onboarding","function":"_generate_task_suggestions","line":1120,"event":"task_generation_prompt_built","data":{"prompt":"You are helping set up Clodputer, an autonomous task automation system that runs Claude Code tasks on a schedule.\n\nAvailable MCPs in this Claude Code installation:\n- gmail: npx @gongrzhe/server-gmail-autoauth-mcp\n- calendar: npx @gongrzhe/google-calendar-mcp\n- crawl4ai: /Users/ro/code/claude-scripts/run_crawl4ai_mcp.sh\n\nYour goal: Generate exactly 3 useful, safe, and immediately valuable task suggestions for this user.\n\n... (2086 chars total)","prompt_length":2086,"mcp_count":3,"connected_mcp_count":3}}
{"timestamp":"2025-10-09T15:01:10.241Z","level":"INFO","module":"onboarding","function":"_generate_task_suggestions","line":1132,"event":"task_generation_command_built","data":{"command":["/usr/local/bin/claude","--print","--output-format","json"],"command_string":"/usr/local/bin/claude --print --output-format json"}}
{"timestamp":"2025-10-09T15:01:10.242Z","level":"INFO","module":"onboarding","function":"_generate_task_suggestions","line":1138,"event":"task_generation_claude_starting","data":{"command":"/usr/local/bin/claude --print --output-format json"}}
{"timestamp":"2025-10-09T15:01:55.678Z","level":"INFO","module":"onboarding","function":"_generate_task_suggestions","line":1152,"event":"task_generation_claude_response_received","data":{"command":"/usr/local/bin/claude --print --output-format json","return_code":0,"stdout":"I'd be happy to help you set up your automation system! To generate personalized task suggestions, I'll need to understand...\n\nWhat specific workflows are you looking to automate? For example:\n- Email management patterns\n- Calendar optimization needs\n- Research or monitoring requirements\n\nCould you share more about your daily routines and what you'd like automated?","stderr":"","stdout_length":423,"stderr_length":0}}
{"timestamp":"2025-10-09T15:01:55.679Z","level":"ERROR","module":"onboarding","function":"_generate_task_suggestions","line":1189,"event":"task_generation_json_parse_error","data":{"error":"Expecting value: line 1 column 1 (char 0)","full_stdout":"I'd be happy to help you set up your automation system! To generate personalized task suggestions, I'll need to understand...\n\nWhat specific workflows are you looking to automate? For example:\n- Email management patterns\n- Calendar optimization needs\n- Research or monitoring requirements\n\nCould you share more about your daily routines and what you'd like automated?"}}
{"timestamp":"2025-10-09T15:01:55.680Z","level":"INFO","module":"onboarding","function":"_offer_intelligent_task_generation","line":1429,"event":"task_generation_failed"}
```

**Problems with this**:
- 😵 Wall of JSON - hard to scan
- 🤷 No visual hierarchy - everything looks the same
- ❓ Unclear what went wrong - buried in technical details
- 🔍 Hard to find related logs - no correlation ID
- 📏 Timestamps are absolute - can't easily see "took 45s"
- 💭 Technical jargon - "stdout_length", "return_code" not user-friendly

---

## IMPROVED STATE (What It Could Be)

### In Terminal (Color-coded, readable)

```
🐛 Debug mode enabled
   Logs writing to ~/.clodputer/debug.log
   Operation ID: onboard-f3a8b912
🪟  Debug log window opened

═══════════════════════════════════════════════════════════
🚀 ONBOARDING STARTED
═══════════════════════════════════════════════════════════
```

### In Debug Log Window (Formatted for humans)

```
[+0.0s] 🏁 Onboarding Started
        └─ Operation ID: onboard-f3a8b912

[+0.0s] ━━━ STEP 1/7: Directory Setup ━━━

[+0.0s] 📁 Creating directories
        ✓ ~/.clodputer (queue and state management)
        ✓ ~/.clodputer/tasks (task configurations)
        ✓ ~/.clodputer/logs (execution logs)
        ✓ ~/.clodputer/archive (archived results)

[+0.1s] ✅ Directory setup complete

[+0.1s] ━━━ STEP 2/7: Claude CLI Configuration ━━━

[+0.1s] 🔍 Detecting Claude CLI
        Checking environment and common paths...

[+0.1s] ✓ Found candidate: /usr/local/bin/claude
        Asking user to confirm...

[+1.7s] ✅ User confirmed: /usr/local/bin/claude

[+1.7s] 🧪 Verifying Claude CLI works
        Running: /usr/local/bin/claude --version

[+2.6s] ✅ Claude CLI verified
        Version: Claude CLI v1.2.3
        Path stored in ~/.clodputer/env.json

[+2.6s] ━━━ STEP 3/7: Intelligent Task Generation ━━━

[+2.6s] 🔍 Detecting available MCPs
        Running: claude mcp list

[+4.7s] ✅ Found 3 MCP servers
        Connected: gmail, calendar, crawl4ai

[+4.7s] 📝 Building AI prompt for task generation

        Summary:
        • Prompt size: 2.0 KB
        • MCPs detected: 3 (all connected)
        • Expected tasks: 3
        • Sections: intro, mcp_context, requirements, output_format

        MCP Examples:
        • gmail → email triage, inbox summarization
        • calendar → meeting prep, schedule analysis
        • crawl4ai → research, monitoring, content extraction

[+4.7s] 🔌 Sending request to Claude
        Command: claude --print --output-format json
        Prompt: 2,086 chars

        ⏳ This may take 30-60 seconds...

[+50.1s] ⚠️  Received response but not in expected format

         Expected: Valid JSON with 'tasks' array
         Received: Conversational text response

         Claude's Response (first 200 chars):
         "I'd be happy to help you set up your automation
         system! To generate personalized task suggestions,
         I'll need to understand...

         What specific workflows are you looking to..."

         💡 Troubleshooting:
         • Claude may not be in headless mode
         • Try: claude --print (verify --print flag works)
         • Check: Is --output-format json flag supported?
         • This version may require interactive prompts

         📋 Full Response Available:
         View with: clodputer debug view --operation-id onboard-f3a8b912 --event task_generation_claude_response_received

[+50.1s] 🔄 Falling back to template system
         AI generation failed, using manual templates instead

[+50.1s] ━━━ STEP 3/7: Template Installation (Fallback) ━━━

        ...continues with template flow...
```

### In debug.log (Still JSON for machines, but enriched)

```json
{
  "timestamp": "2025-10-09T15:01:55.678Z",
  "elapsed": 45.1,
  "operation_id": "onboard-f3a8b912",
  "marker": "⚠️",
  "level": "WARNING",
  "module": "onboarding",
  "function": "_generate_task_suggestions",
  "line": 1152,

  "phase": "Intelligent Task Generation",
  "step": "Received Claude response",
  "step_number": "3/7",
  "progress_percent": 43,

  "event": "task_generation_unexpected_response",
  "description": "Received conversational response instead of JSON",

  "tags": ["claude", "api", "response", "format-error", "fallback"],

  "attempted": "Generating 3 task suggestions via Claude Code API",

  "expected_vs_actual": {
    "expected": "JSON object with 'tasks' array containing 3 task definitions",
    "expected_format": "{\"tasks\": [{\"name\": \"...\", \"description\": \"...\", \"yaml_config\": \"...\"}]}",
    "actual": "Conversational text asking for more information",
    "actual_preview": "I'd be happy to help you set up your automation system! To generate personalized task suggestions, I'll need to understand... (423 chars)"
  },

  "summary": {
    "duration": "45.1s",
    "request_size": "2.0 KB",
    "response_size": "423 bytes",
    "return_code": 0,
    "stderr_present": false,
    "json_valid": false,
    "fallback_triggered": true
  },

  "troubleshooting": [
    "Verify Claude CLI supports --print flag (headless mode)",
    "Check if --output-format json flag is recognized",
    "This version may require interactive prompts",
    "Try running manually: claude --print --output-format json < prompt.txt",
    "Consider upgrading Claude CLI to latest version"
  ],

  "related_logs": [
    "task_generation_prompt_built",
    "task_generation_command_built",
    "task_generation_claude_starting"
  ],

  "data": {
    "command": "/usr/local/bin/claude --print --output-format json",
    "return_code": 0,
    "stdout": "I'd be happy to help you set up your automation system! To generate personalized task suggestions, I'll need to understand...\n\nWhat specific workflows are you looking to automate? For example:\n- Email management patterns\n- Calendar optimization needs\n- Research or monitoring requirements\n\nCould you share more about your daily routines and what you'd like automated?",
    "stderr": "",
    "stdout_length": 423,
    "stderr_length": 0
  }
}
```

---

## Key Improvements Demonstrated

### 1. ✅ Visual Hierarchy
- Clear section headers with emoji markers
- Step numbers (1/7, 2/7, etc.)
- Indentation shows relationships
- Progress indicators

### 2. ✅ Human-Readable
- Plain English descriptions
- Emoji markers for quick scanning
- "Summary" blocks with key metrics
- Avoids technical jargon

### 3. ✅ Correlation
- Operation ID ties all logs together
- "Related logs" references
- Easy to filter one operation

### 4. ✅ Timing
- Elapsed seconds from operation start
- Easy to see "this took 45s"
- Duration in summaries

### 5. ✅ Actionable Errors
- "Expected vs Actual" comparison
- Troubleshooting suggestions
- Links to related logs
- Command to view full details

### 6. ✅ Smart Truncation
- Full data still in JSON
- Summaries for quick understanding
- Preview with "view full" option
- Structure description

### 7. ✅ Searchable
- Tags for filtering
- Keywords in descriptions
- Operation IDs for correlation
- Event names remain

### 8. ✅ Both Machine & Human
- JSON for machine parsing
- Formatted view for humans
- Both available simultaneously
- Switch between views

---

## Command Examples

```bash
# View full operation in readable format
clodputer debug view --operation-id onboard-f3a8b912

# Show only errors
clodputer debug view --level ERROR

# Show all Claude API interactions
clodputer debug view --tags claude,api

# Show specific event with full data
clodputer debug view --event task_generation_claude_response_received

# Follow live (like tail -f but formatted)
clodputer debug follow

# Export operation to file
clodputer debug export --operation-id onboard-f3a8b912 --format markdown > issue-report.md
```

---

## Summary: Why This Matters

**Current State**: You need to be a developer to understand what's happening
**Improved State**: Anyone can follow along and debug issues

**Current State**: Hard to find what went wrong
**Improved State**: Errors highlighted with troubleshooting steps

**Current State**: Data overload, hard to scan
**Improved State**: Summaries + full data available

**Current State**: All logs look the same
**Improved State**: Visual hierarchy, emoji markers, colors

**Current State**: Technical event names
**Improved State**: Human descriptions + technical names

This transforms debug logging from "developer only" to "human readable" while keeping the machine-parseable JSON format for automation.
