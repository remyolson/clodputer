# Clodputer: Autonomous Claude Code Automation System

**Project Status**: Planning Phase
**Created**: October 7, 2025
**Author**: Rémy Olson

## Executive Summary

Clodputer is a lightweight automation framework that enables Claude Code to execute tasks autonomously through scheduled jobs (cron) and event-driven triggers (file watchers, todo list changes). The goal is to create a simple, open-source tool that extends Claude Code's capabilities for hands-off task execution while maintaining full integration with existing MCP servers and Claude Code features.

## Core Use Cases

### 1. Scheduled Automation (Cron Jobs)
**Example: Daily Email Management**
- **Trigger**: Every day at 8:00 AM
- **Task**: Read all unread emails via Gmail MCP
- **Actions**:
  - Identify emails requiring responses
  - Research email history and communication patterns
  - Draft contextual responses matching writing style
  - Save drafts to `~/email-responses/[date]-[subject].md`
  - Archive previous day's responses to `~/email-responses/archive/`
- **Outcome**: Clean, ready-to-review email drafts every morning

### 2. Event-Driven Automation (File Watchers)
**Example: Project Assignment Queue**
- **Trigger**: New markdown file created in `~/todos/claude-assignments/`
- **Task**: Automatically execute project tasks
- **Actions**:
  - Detect new project file
  - Update file status to "🔵 in_progress"
  - Execute tasks sequentially with context retention
  - Add progress updates to the file
  - Mark as "🟢 complete" or "🔴 blocked" with details
- **Outcome**: Autonomous project execution without manual prompting

### 3. Todo List Integration
**Example: Tagged Task Execution**
- **Trigger**: Todo item tagged with `@claude` in `~/todos/todo-current.md`
- **Task**: Execute specific todo item
- **Actions**:
  - Parse todo list for `@claude` tags
  - Extract task context and dependencies
  - Execute task autonomously
  - Update todo status in-file
  - Add completion timestamp
- **Outcome**: Hands-free todo list execution

## Key Requirements

### Simplicity First
- **No heavy frameworks**: Minimal dependencies, primarily orchestration code
- **Simple architecture**: Leverages existing Claude Code capabilities
- **Easy setup**: Should work out-of-the-box on macOS
- **Open source**: Community-driven, shareable, extensible

### Multi-Turn Conversations
- **Not single-shot**: Tasks should support multi-step workflows
- **Context persistence**: Maintain conversation state across multiple prompts
- **Sequential execution**: Execute task lists in order
- **Progress tracking**: Parse responses to determine completion status

### Resource Management
- **Controlled execution**: Prevent excessive concurrent Claude Code instances
- **MCP efficiency**: Either reuse single Claude Code instance or manage MCP lifecycle
- **System integration**: Monitor system resources, throttle when necessary

### Integration with Existing Setup
- **Current working directory**: `/Users/ro` (root of user directory)
- **Access to all files**: Leverages existing filesystem access
- **MCP compatibility**: Works with all configured MCP servers:
  - Gmail MCP
  - Google Calendar MCP
  - Google Drive MCP
  - Google Sheets MCP
  - Playwright MCP
  - DuckDuckGo Search MCP
  - Crawl4AI MCP
  - Ultimate Google Docs MCP
  - Google Search Tool MCP

## Technical Foundation Discovered

### Claude Code Headless Mode
Claude Code supports **headless mode** (`claude -p`) for non-interactive, programmatic execution:
- **Basic usage**: `claude -p "prompt text" --output-format json`
- **Session management**: `--resume SESSION_ID` or `--continue` for multi-turn conversations
- **Output formats**: `text`, `json`, `stream-json`
- **Input formats**: Text or `stream-json` for multi-turn conversations
- **Tool control**: `--allowedTools`, `--disallowedTools` for security
- **Permission modes**: `--permission-mode acceptEdits` for automation
- **Custom system prompts**: `--append-system-prompt` for context

### Key Capabilities
- **Multi-turn conversations**: Resume sessions with `--resume` and `--continue`
- **JSON output**: Structured responses with metadata (cost, duration, session_id)
- **Streaming JSON**: Real-time message streaming for long-running tasks
- **Background tasks**: Native support for persistent processes
- **Hooks system**: Event-driven automation at specific execution points
- **Checkpoints**: Automatic code state snapshots for safety

### Existing Limitations
- **No native scheduling**: Claude Code has no built-in cron functionality ([GitHub Issue #4785](https://github.com/anthropics/claude-code/issues/4785))
- **No file watchers**: No native event-driven triggers for file changes
- **No autonomous triggers**: Requires external orchestration for automation

## Non-Goals
- Building a complex agent orchestration framework (CrewAI, LangGraph, etc.)
- Creating a full-featured IDE extension
- Implementing custom AI models or inference
- Building a web interface or dashboard

## Success Criteria
1. **Cron jobs execute reliably** on schedule with proper error handling
2. **File watchers detect changes** and trigger Claude Code tasks instantly
3. **Multi-turn conversations work** seamlessly with context retention
4. **Resource usage is controlled** with no runaway processes
5. **Easy to configure** for new automation tasks
6. **Open source ready** with clear documentation for community use

## Next Steps
1. Analyze technical architecture options
2. Identify integration points with Claude Code
3. Define implementation approaches with trade-offs
4. Prepare decision-making questions
5. Create technical specification
6. Build implementation plan with sequencing

---

**Related Files**:
- [Technical Architecture Options](02-technical-architecture.md) - To be created
- [Implementation Plan](03-implementation-plan.md) - To be created
- [Decision Matrix](04-decision-matrix.md) - To be created
