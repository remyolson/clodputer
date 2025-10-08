# Intelligent Task Generation - Planning Document

## Overview

Add intelligent, personalized task generation to the onboarding flow. Instead of offering generic templates, Clodputer will:
1. Detect the user's Claude Code MCP configuration
2. Use Claude Code itself (in headless mode) to generate 3 personalized task suggestions
3. Let the user select which tasks to install
4. Automatically create the selected tasks

**Goal**: Self-bootstrapping onboarding that demonstrates value immediately with tasks tailored to each user's environment.

## Design Philosophy

1. **Meta-intelligent** - Clodputer uses Claude to set itself up
2. **Personalized** - Different users get different suggestions based on their MCPs
3. **Graceful degradation** - Falls back to templates if generation fails
4. **Educational** - Shows users what's possible with their specific setup
5. **Safe** - Generated tasks are vetted, non-destructive, and well-documented

## Implementation Phases

### Phase 1: MCP Detection Infrastructure
**Goal**: Reliably detect and parse user's MCP configuration

- [ ] Create `_detect_available_mcps()` function
  - [ ] Run `claude mcp list` via subprocess
  - [ ] Parse output to extract MCP names and types
  - [ ] Handle errors gracefully (no MCPs, command fails, etc.)
  - [ ] Return structured list of MCP metadata

- [ ] Create `_parse_mcp_list_output()` helper
  - [ ] Parse Claude Code's MCP list format
  - [ ] Extract: name, type, description, status
  - [ ] Handle different output formats (table, JSON, text)
  - [ ] Return list[dict] with MCP info

- [ ] Add error handling
  - [ ] Handle case where `claude mcp` command doesn't exist
  - [ ] Handle empty MCP list
  - [ ] Handle parse errors
  - [ ] Log warnings but don't fail onboarding

- [ ] Write tests for MCP detection
  - [ ] Test with mock MCP list output
  - [ ] Test with empty output
  - [ ] Test with malformed output
  - [ ] Test error cases

### Phase 2: Task Generation Prompt Engineering
**Goal**: Create a robust prompt that generates high-quality, safe task suggestions

- [ ] Design base prompt template
  - [ ] Include MCP context
  - [ ] Specify output format (JSON with task configs)
  - [ ] Set safety constraints (no destructive actions)
  - [ ] Define quality criteria (useful, completable in 30-60s)

- [ ] Create MCP-specific guidance
  - [ ] Email MCP → email triage/summarization tasks
  - [ ] Calendar MCP → meeting prep/scheduling tasks
  - [ ] Search MCPs → research/monitoring tasks
  - [ ] Drive/Docs MCPs → document organization tasks
  - [ ] No MCPs → file/git/system automation tasks

- [ ] Define JSON output schema
  ```json
  {
    "tasks": [
      {
        "name": "task-name",
        "description": "User-facing description",
        "yaml_config": "Complete YAML including prompt",
        "reasoning": "Why this task is relevant"
      }
    ]
  }
  ```

- [ ] Add validation requirements
  - [ ] Must generate exactly 3 tasks
  - [ ] Each task must have valid YAML
  - [ ] Each task must be immediately useful
  - [ ] No destructive operations (delete, uninstall, etc.)

- [ ] Create fallback examples
  - [ ] Default tasks when no MCPs detected
  - [ ] Generic useful tasks (git status, todo finder, etc.)

### Phase 3: Claude Code Integration
**Goal**: Invoke Claude Code in headless mode to generate tasks

- [ ] Create `_generate_task_suggestions()` function
  - [ ] Build prompt with MCP context
  - [ ] Invoke Claude CLI with `--headless --output-format json`
  - [ ] Set reasonable timeout (60s)
  - [ ] Parse JSON response
  - [ ] Validate response structure

- [ ] Add Claude CLI execution logic
  - [ ] Use subprocess.run() with timeout
  - [ ] Capture stdout/stderr
  - [ ] Handle execution errors
  - [ ] Handle timeout errors
  - [ ] Handle JSON parse errors

- [ ] Implement response validation
  - [ ] Validate JSON structure matches schema
  - [ ] Validate each task has required fields
  - [ ] Validate YAML syntax is correct
  - [ ] Check task names are valid filenames
  - [ ] Verify no dangerous commands in prompts

- [ ] Add safety checks
  - [ ] Scan for destructive keywords (rm, delete, drop, etc.)
  - [ ] Verify allowed_tools don't include dangerous ones
  - [ ] Check file paths are within user's home directory
  - [ ] Reject tasks with suspicious patterns

- [ ] Write tests for task generation
  - [ ] Test with mock Claude responses
  - [ ] Test with various MCP configurations
  - [ ] Test error handling
  - [ ] Test validation logic

### Phase 4: User Interface for Task Selection
**Goal**: Present generated tasks beautifully and let user select

- [ ] Create `_offer_intelligent_task_generation()` function
  - [ ] Show "Analyzing your setup..." message
  - [ ] Display detected MCP count
  - [ ] Show "Generating suggestions..." progress
  - [ ] Present task list with descriptions

- [ ] Design task presentation UI
  - [ ] Use Rich formatting for readability
  - [ ] Show task number, name, and description
  - [ ] Highlight which MCPs each task uses
  - [ ] Display reasoning/value proposition

- [ ] Implement task selection logic
  - [ ] Prompt: "Select tasks to install (e.g., '1,3' or 'all')"
  - [ ] Parse user input (comma-separated, ranges, 'all')
  - [ ] Validate selections (in range, valid numbers)
  - [ ] Handle 'none' or empty selection

- [ ] Add task installation
  - [ ] Create YAML files in ~/.clodputer/tasks/
  - [ ] Show success message for each created task
  - [ ] Handle file conflicts (task already exists)
  - [ ] Set proper file permissions

- [ ] Write UI tests
  - [ ] Test with mock user input
  - [ ] Test selection parsing
  - [ ] Test file creation
  - [ ] Test conflict handling

### Phase 5: Integration with Onboarding Flow
**Goal**: Seamlessly integrate into existing Step 3 of onboarding

- [ ] Modify `run_onboarding()` in onboarding.py
  - [ ] Replace Step 3 header from "Template Installation" to "Task Generation"
  - [ ] Call `_offer_intelligent_task_generation()` first
  - [ ] Fall back to `_offer_template_install()` on failure
  - [ ] Maintain backward compatibility

- [ ] Add fallback logic
  - [ ] If MCP detection fails → use templates
  - [ ] If task generation fails → use templates
  - [ ] If user declines generation → offer templates
  - [ ] Show clear messaging for each path

- [ ] Update progress indicators
  - [ ] Keep 7-step structure
  - [ ] Step 3 now: "Intelligent Task Generation"
  - [ ] Show appropriate messages for success/fallback

- [ ] Preserve existing functionality
  - [ ] Template system still available as fallback
  - [ ] All existing tests still pass
  - [ ] No breaking changes to API

- [ ] Update onboarding tests
  - [ ] Mock MCP detection
  - [ ] Mock Claude Code responses
  - [ ] Test fallback paths
  - [ ] Verify task creation

### Phase 6: Error Handling and Edge Cases
**Goal**: Handle all failure modes gracefully

- [ ] Handle MCP detection failures
  - [ ] Command not found → show message, use templates
  - [ ] Permission denied → show message, use templates
  - [ ] Parse error → log warning, use templates

- [ ] Handle task generation failures
  - [ ] Claude CLI timeout → show message, use templates
  - [ ] Invalid JSON response → show error, use templates
  - [ ] Validation failures → show message, use templates
  - [ ] Network issues → show message, use templates

- [ ] Handle user interaction edge cases
  - [ ] Invalid selection input → re-prompt
  - [ ] All tasks rejected → ask if they want templates
  - [ ] File write errors → show error, continue
  - [ ] Keyboard interrupt → clean exit

- [ ] Add comprehensive logging
  - [ ] Log MCP detection results
  - [ ] Log generation attempts and responses
  - [ ] Log validation failures with details
  - [ ] Log fallback triggers

- [ ] Write edge case tests
  - [ ] Test all error paths
  - [ ] Test fallback scenarios
  - [ ] Test partial success cases
  - [ ] Test user cancellation

### Phase 7: Testing and Quality Assurance
**Goal**: Ensure feature is robust and reliable

- [ ] Write integration tests
  - [ ] End-to-end onboarding with intelligent generation
  - [ ] Test with various MCP configurations
  - [ ] Test fallback to templates
  - [ ] Test smoke test using generated task

- [ ] Add unit tests
  - [ ] Test each helper function individually
  - [ ] Test prompt construction
  - [ ] Test response parsing
  - [ ] Test validation logic

- [ ] Manual testing scenarios
  - [ ] Test with email MCP only
  - [ ] Test with calendar MCP only
  - [ ] Test with multiple MCPs
  - [ ] Test with no MCPs
  - [ ] Test with Claude CLI errors

- [ ] Performance testing
  - [ ] Measure generation time
  - [ ] Ensure reasonable timeout (< 60s)
  - [ ] Verify no memory leaks
  - [ ] Check subprocess cleanup

- [ ] Security review
  - [ ] Verify no code injection vulnerabilities
  - [ ] Check file path sanitization
  - [ ] Review allowed_tools restrictions
  - [ ] Audit destructive command detection

### Phase 8: Documentation and Polish
**Goal**: Document the feature and improve UX

- [ ] Update user documentation
  - [ ] Add section to quick-start.md
  - [ ] Explain how intelligent generation works
  - [ ] Show examples of generated tasks
  - [ ] Document fallback behavior

- [ ] Update developer documentation
  - [ ] Document prompt engineering approach
  - [ ] Explain MCP detection mechanism
  - [ ] Add architecture diagram
  - [ ] Document extension points

- [ ] Improve error messages
  - [ ] Make all errors user-friendly
  - [ ] Provide actionable guidance
  - [ ] Link to troubleshooting docs
  - [ ] Add helpful context

- [ ] Add configuration options (future)
  - [ ] Allow disabling intelligent generation
  - [ ] Allow custom generation prompts
  - [ ] Allow task count customization
  - [ ] Environment variable overrides

- [ ] Polish the UX
  - [ ] Add loading spinners/animations
  - [ ] Show estimated generation time
  - [ ] Add success celebrations
  - [ ] Improve visual hierarchy

## Success Criteria

### Must Have (MVP)
- [x] Planning document complete
- [ ] MCP detection works reliably
- [ ] Task generation produces valid YAML
- [ ] Generated tasks are safe and useful
- [ ] Fallback to templates works seamlessly
- [ ] Integration with onboarding doesn't break existing flow
- [ ] All existing tests pass
- [ ] Basic documentation exists

### Should Have (Polish)
- [ ] Comprehensive test coverage (>85%)
- [ ] Beautiful UI with progress indicators
- [ ] Helpful error messages
- [ ] Complete user documentation
- [ ] Performance optimized (<30s generation)

### Nice to Have (Future)
- [ ] Task regeneration capability
- [ ] User feedback loop (rate generated tasks)
- [ ] Learning from user preferences
- [ ] Template library from community tasks
- [ ] AI-powered task optimization

## Example Generated Tasks

### With Email MCP
```yaml
name: morning-email-triage
prompt: |
  You are my email assistant. Review emails from the last 24 hours and:
  1. Flag any urgent emails that need immediate response
  2. Create a summary of important emails
  3. Draft responses for simple queries

  Use the Gmail MCP to search, read, and optionally draft responses.
allowed_tools:
  - mcp__gmail__search_emails
  - mcp__gmail__read_email
  - mcp__gmail__draft_email
trigger:
  type: cron
  expression: "0 8 * * *"
  timezone: America/Los_Angeles
```

### With Calendar MCP
```yaml
name: meeting-prep
prompt: |
  You are my meeting assistant. For today's meetings:
  1. List all meetings in the next 8 hours
  2. For each meeting, extract attendees and agenda
  3. Create a brief with key talking points

  Use the Google Calendar MCP to access schedule.
allowed_tools:
  - mcp__google-calendar__list_events
  - mcp__google-calendar__get_event
trigger:
  type: cron
  expression: "0 7 * * 1-5"
  timezone: America/Los_Angeles
```

### No MCPs (Fallback)
```yaml
name: git-health-check
prompt: |
  You are my repository assistant. For ~/repos/:
  1. Check for uncommitted changes
  2. List branches older than 30 days
  3. Find TODOs in code
  4. Summarize repository health

  Use bash and file tools to analyze repositories.
allowed_tools:
  - Bash
  - Read
  - Glob
trigger:
  type: cron
  expression: "0 9 * * 1"
  timezone: America/Los_Angeles
```

## Open Questions

- [ ] Should we limit which MCPs are "interesting" for task generation?
- [ ] How do we handle MCP authentication issues during generation?
- [ ] Should generated tasks be marked as "AI-generated" in metadata?
- [ ] Do we need a "regenerate tasks" command for later use?
- [ ] Should we collect telemetry on which tasks users actually use?

## Notes

- Keep the existing template system as fallback
- Ensure backwards compatibility with current onboarding
- Generate tasks that work without additional setup
- Prioritize safety over cleverness
- Make the UX delightful (this is the user's first real interaction!)
