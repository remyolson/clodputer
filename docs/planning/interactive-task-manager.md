# Interactive Task Manager - Planning Document

## Overview

Create an interactive terminal interface for managing Clodputer tasks - a "file manager for tasks" that lets users explore, create, edit, and delete task definitions without leaving the terminal.

**Goal**: Extend Claude Code's capabilities through an intuitive, interactive CLI experience that makes task management feel natural and integrated.

## Problem Statement

Currently:
- ✅ Dashboard exists but is **read-only** (shows status, logs, queue)
- ❌ No interactive way to manage tasks from the terminal
- ❌ Users must manually edit YAML files in `~/.clodputer/tasks/`
- ❌ No task browser or explorer
- ❌ No guided task creation wizard

**User need**: "I want to run `clodputer` and do stuff - explore, create, edit, delete tasks interactively"

## Design Philosophy

1. **Extension, not replacement** - Clodputer extends Claude Code, doesn't replace it
2. **Terminal-native** - Beautiful, interactive terminal UI (like Claude Code's formatting)
3. **Discoverable** - Easy to explore and learn through the interface
4. **Non-destructive** - Confirm before deleting, show previews before editing
5. **Fast** - Keyboard-driven for power users, but also accessible

## Proposed Command Structure

### Option A: New `clodputer manage` Command (Recommended)

```bash
# Launch interactive task manager
clodputer manage

# Or use shorthand
clodputer tasks  # Alias for 'manage'
```

**Why?** Clear, discoverable, doesn't break existing commands.

### Option B: Extend Existing Commands

```bash
# Interactive mode for existing commands
clodputer list --interactive
clodputer run --interactive
clodputer template --interactive
```

**Why?** Integrates with existing patterns, more granular.

**Recommendation**: Use Option A (`clodputer manage`) for initial implementation.

## Feature Breakdown

### Phase 1: Interactive Task Browser (MVP)

**Entry Point**: `clodputer manage`

**Main Screen**:
```
╔══════════════════════════════════════════════════════════════╗
║                    Clodputer Task Manager                    ║
║                     ~/.clodputer/tasks/                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  ┌─ Tasks (5) ──────────────────────────────────────────┐  ║
║  │                                                        │  ║
║  │  📅  daily-email.yaml                        [Cron]   │  ║
║  │  📁  file-watcher.yaml                       [Watch]  │  ║
║  │  📋  todo-triage.yaml                        [Manual] │  ║
║  │  📧  calendar-sync.yaml                      [Cron]   │  ║
║  │  ⚙️   manual-task.yaml                       [Manual] │  ║
║  │                                                        │  ║
║  └────────────────────────────────────────────────────────┘  ║
║                                                              ║
║  ┌─ Actions ─────────────────────────────────────────────┐  ║
║  │  [↵] View  [e] Edit  [n] New  [d] Delete  [r] Run    │  ║
║  │  [t] Test  [i] Import Template  [?] Help  [q] Quit   │  ║
║  └────────────────────────────────────────────────────────┘  ║
║                                                              ║
║  Use ↑↓ to navigate, ↵ to select                            ║
╚══════════════════════════════════════════════════════════════╝
```

**Navigation**:
- `↑↓` or `j/k` - Navigate tasks
- `↵` - View selected task details
- `e` - Edit task (opens in $EDITOR)
- `n` - Create new task (wizard or template)
- `d` - Delete task (with confirmation)
- `r` - Run task immediately
- `t` - Test/validate task YAML
- `i` - Import from template
- `?` - Show help overlay
- `q` - Quit back to terminal

**Task List Features**:
- Show task name, type (Cron/Watch/Manual), and status
- Color coding: Active (green), Scheduled (blue), Manual (gray)
- Sort by: name, type, last run, next run
- Filter by: type, status, search term

### Phase 2: Task Detail View

**Screen** (when pressing `↵` on a task):
```
╔══════════════════════════════════════════════════════════════╗
║                      daily-email.yaml                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Name:           daily-email                                 ║
║  Type:           Scheduled (Cron)                            ║
║  Schedule:       0 8 * * * (Daily at 8:00 AM)               ║
║  Last Run:       2025-10-08 08:00:00 (success, 33s)         ║
║  Next Run:       2025-10-09 08:00:00 (in 11h 23m)           ║
║                                                              ║
║  ┌─ Prompt Preview ─────────────────────────────────────┐  ║
║  │  You are my email assistant. Please review emails    │  ║
║  │  from the last 24 hours and create a summary with    │  ║
║  │  action items...                                      │  ║
║  └────────────────────────────────────────────────────────┘  ║
║                                                              ║
║  ┌─ Recent Executions ───────────────────────────────────┐  ║
║  │  2025-10-08 08:00:00  ✅ success  33s  $0.22         │  ║
║  │  2025-10-07 08:00:00  ✅ success  28s  $0.19         │  ║
║  │  2025-10-06 08:00:00  ⚠️  timeout  120s  $0.15       │  ║
║  └────────────────────────────────────────────────────────┘  ║
║                                                              ║
║  [e] Edit  [r] Run Now  [l] View Logs  [Esc] Back          ║
╚══════════════════════════════════════════════════════════════╝
```

**Features**:
- Full task metadata displayed
- Prompt preview (first few lines, expandable)
- Recent execution history
- Quick actions: edit, run, view logs
- `Esc` to go back to list

### Phase 3: Task Creation Wizard

**Screen** (when pressing `n` for new task):
```
╔══════════════════════════════════════════════════════════════╗
║                   Create New Task (1/5)                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Choose creation method:                                     ║
║                                                              ║
║    ○  Start from template                                    ║
║    ●  Create from scratch                                    ║
║    ○  Duplicate existing task                                ║
║                                                              ║
║  Use ↑↓ to select, ↵ to continue, Esc to cancel            ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║                   Create New Task (2/5)                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Task name (will be saved as <name>.yaml):                   ║
║  ┌────────────────────────────────────────────────────────┐  ║
║  │  my-new-task█                                          │  ║
║  └────────────────────────────────────────────────────────┘  ║
║                                                              ║
║  ✓ Name is valid (lowercase, hyphens, alphanumeric)         ║
║                                                              ║
║  [↵] Continue  [Esc] Cancel                                  ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║                   Create New Task (3/5)                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  How should this task be triggered?                          ║
║                                                              ║
║    ●  Manual (run with `clodputer run my-new-task`)         ║
║    ○  Scheduled (cron schedule)                              ║
║    ○  File watcher (triggered by file changes)              ║
║                                                              ║
║  Use ↑↓ to select, ↵ to continue, Esc to cancel            ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║                   Create New Task (4/5)                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Write your task prompt:                                     ║
║  ┌────────────────────────────────────────────────────────┐  ║
║  │  You are my assistant. Please help me...█              │  ║
║  │                                                         │  ║
║  │                                                         │  ║
║  │                                                         │  ║
║  └────────────────────────────────────────────────────────┘  ║
║                                                              ║
║  💡 Tip: Include all context and instructions needed        ║
║          for a single Claude CLI run.                        ║
║                                                              ║
║  [Ctrl+S] Save and continue  [Ctrl+E] Open in $EDITOR       ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║                   Create New Task (5/5)                      ║
║                       Review & Confirm                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Task will be saved as: ~/.clodputer/tasks/my-new-task.yaml ║
║                                                              ║
║  ┌─ Preview ────────────────────────────────────────────┐   ║
║  │  name: my-new-task                                    │   ║
║  │  description: My new task                             │   ║
║  │  prompt: |                                            │   ║
║  │    You are my assistant. Please help me...           │   ║
║  │  trigger:                                             │   ║
║  │    type: manual                                       │   ║
║  └────────────────────────────────────────────────────────┘  ║
║                                                              ║
║  [s] Save  [e] Edit  [Esc] Cancel                           ║
╚══════════════════════════════════════════════════════════════╝
```

**Wizard Flow**:
1. Choose creation method (template/scratch/duplicate)
2. Enter task name (with validation)
3. Select trigger type (manual/cron/watch)
4. If cron: Enter schedule (with preview of next runs)
5. If watch: Enter directory and patterns
6. Write prompt (inline editor or open $EDITOR)
7. Optional: Configure allowed tools, context, etc.
8. Review and confirm

### Phase 4: Task Editing

**Options**:

1. **Quick Edit Mode** - Opens task YAML in $EDITOR (vim, nano, code)
   ```bash
   # User presses 'e' on a task
   # Opens: $EDITOR ~/.clodputer/tasks/daily-email.yaml
   ```

2. **Guided Edit Mode** - Step-through wizard similar to creation
   - Edit specific fields without touching YAML
   - Good for non-technical users

3. **Inline Edit Mode** - Edit fields directly in the interface
   - Like editing a form in the terminal

**Recommendation**: Start with Quick Edit Mode (simplest), add Guided Edit later.

### Phase 5: Advanced Features

1. **Task Validation & Testing**
   - Press `t` to validate YAML syntax
   - Run dry-run/test execution
   - Show validation errors inline

2. **Task Duplication**
   - Press `Shift+d` to duplicate selected task
   - Prompt for new name
   - Creates copy with "-copy" suffix

3. **Bulk Operations**
   - Select multiple tasks (Space to toggle)
   - Run all selected
   - Delete all selected (with confirmation)
   - Export selected

4. **Search & Filter**
   - Press `/` to enter search mode
   - Filter by name, type, schedule
   - Fuzzy matching

5. **Task History & Analytics**
   - View execution history per task
   - Success rate, average duration, cost tracking
   - Trends over time

## Technical Implementation

### Technology Stack

**Option A: Rich + Click (Recommended)**
- Use `rich` library for beautiful terminal output
- Use `click` for menu navigation and prompts
- Pros: Already using click, rich is lightweight, good docs
- Cons: Not a full TUI framework, need to build navigation

**Option B: Textual (Full TUI)**
- Use Textual framework (by same author as Rich)
- Full TUI with mouse support, widgets, layouts
- Pros: Professional, feature-rich, reactive UI
- Cons: Heavier dependency, steeper learning curve

**Option C: Prompt Toolkit**
- Use Python Prompt Toolkit
- Full-featured CLI framework
- Pros: Powerful, widely used (used by IPython)
- Cons: Complex API, might be overkill

**Recommendation**: Start with Rich + Click (Option A), migrate to Textual (Option B) if needed.

### File Structure

```
src/clodputer/
├── cli.py                    # Add 'manage' command
├── manager.py                # New: Interactive task manager
├── manager_views.py          # New: UI views (list, detail, wizard)
├── manager_actions.py        # New: CRUD operations
└── manager_formatters.py     # New: Rich formatting helpers
```

### Code Structure

```python
# src/clodputer/manager.py
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
import click

@click.command()
def manage():
    """Launch interactive task manager."""
    console = Console()

    while True:
        # Show task list
        tasks = load_tasks()
        render_task_list(console, tasks)

        # Get user action
        action = Prompt.ask(
            "Action",
            choices=["view", "edit", "new", "delete", "run", "quit"],
            default="view"
        )

        if action == "quit":
            break
        elif action == "view":
            handle_view_task(console, tasks)
        elif action == "edit":
            handle_edit_task(console, tasks)
        # ... etc
```

### Integration Points

1. **With Existing Dashboard** (`clodputer dashboard`)
   - Keep dashboard as read-only monitoring view
   - Link from manager: "Press 'm' to open dashboard in new window"
   - Separate concerns: manager = CRUD, dashboard = monitoring

2. **With Existing Commands**
   - `clodputer run <task>` - Still works, manager just adds GUI
   - `clodputer template export` - Manager uses this internally
   - `clodputer doctor` - Manager can show validation inline

3. **With File System**
   - Manager reads/writes `~/.clodputer/tasks/*.yaml`
   - External edits are immediately visible (reload on return to manager)
   - File watchers detect changes made outside manager

## User Experience Flow

### Scenario 1: Browse and Run a Task

```bash
$ clodputer manage

# User sees task list
# Navigates with ↑↓ to "daily-email"
# Presses ↵ to view details
# Sees last run was 11 hours ago
# Presses 'r' to run now
# Sees "⏳ Running task..." spinner
# After 30s: "✅ Task completed successfully"
# Presses Esc to return to list
# Presses 'q' to quit
```

### Scenario 2: Create a New Task

```bash
$ clodputer manage

# User presses 'n' for new task
# Wizard guides through:
#   1. Name: "weekly-report"
#   2. Type: Cron schedule
#   3. Schedule: "0 9 * * 1" (Mondays at 9 AM)
#   4. Prompt: (opens in $EDITOR to write)
#   5. Review: Shows preview
# Presses 's' to save
# Returns to list, sees new "weekly-report" task
# Presses 't' to test/validate
# Sees "✅ Task is valid"
```

### Scenario 3: Edit Existing Task

```bash
$ clodputer manage

# User navigates to "todo-triage"
# Presses 'e' to edit
# Opens ~/.clodputer/tasks/todo-triage.yaml in VS Code
# User modifies the prompt
# Saves and closes editor
# Manager detects change, reloads
# Presses 't' to validate
# Sees "✅ Task is valid"
# Presses 'r' to test run
```

## Visual Design (Colors & Formatting)

### Color Scheme (Using Rich)

- **Task Types**:
  - 🔵 Scheduled (Cron) - `blue`
  - 🟢 Active/Running - `green`
  - ⚪ Manual - `white`
  - 🟡 File Watcher - `yellow`
  - 🔴 Failed/Error - `red`

- **Status Indicators**:
  - ✅ Success - `green bold`
  - ❌ Failed - `red bold`
  - ⏱️ Timeout - `yellow bold`
  - ⚠️ Warning - `yellow`
  - ℹ️ Info - `blue`

- **UI Elements**:
  - Headers - `cyan bold`
  - Selected item - `reverse` (inverted colors)
  - Actions/Hotkeys - `magenta`
  - Borders - `dim white`

### Box Drawing

Use Rich's `Panel`, `Table`, and box characters for clean borders:

```python
from rich.panel import Panel
from rich.box import ROUNDED

panel = Panel(
    content,
    title="Task Manager",
    border_style="cyan",
    box=ROUNDED
)
```

## Success Metrics

How do we know this feature is successful?

1. **Adoption**: % of Clodputer users who use `clodputer manage` at least once
2. **Task Creation**: Increase in user-created tasks (vs. just using templates)
3. **User Feedback**: Positive sentiment in issues/discussions
4. **CLI vs. Manager**: Track ratio of CLI commands vs. manager usage
5. **Reduced Errors**: Fewer invalid YAML files created

## Rollout Plan

### Phase 1: MVP (Week 1-2)
- Task list view with navigation
- View task details
- Run task from manager
- Edit task (opens in $EDITOR)
- Delete task (with confirmation)

### Phase 2: Task Creation (Week 3)
- New task wizard
- Template import from manager
- Task validation

### Phase 3: Polish (Week 4)
- Colors and formatting
- Search and filter
- Keyboard shortcuts
- Help overlay
- Better error messages

### Phase 4: Advanced Features (Future)
- Bulk operations
- Task history and analytics
- Inline editing mode
- Mouse support (if using Textual)

## Open Questions

1. **Mouse Support**: Do we need it, or keyboard-only?
   - Recommendation: Keyboard-only for MVP, mouse later with Textual

2. **Concurrent Editing**: What if user edits YAML while manager is open?
   - Recommendation: Reload on focus return, show "File changed" warning

3. **Task Templates in Manager**: Browse/preview before import?
   - Recommendation: Yes, add template browser in wizard

4. **Integration with Dashboard**: Single unified view or separate?
   - Recommendation: Keep separate, but allow launching dashboard from manager

5. **Mobile/SSH Sessions**: Does it work over SSH?
   - Recommendation: Yes, ensure works in limited terminal environments

## Alternative: Simpler Menu-Based Approach

If full TUI is too complex, we could start with a simpler menu system:

```bash
$ clodputer manage

╔══════════════════════════════════════════════════════════════╗
║                  Clodputer Task Manager                      ║
╠══════════════════════════════════════════════════════════════╣

Tasks in ~/.clodputer/tasks/:

  1. 📅 daily-email.yaml          [Cron: 0 8 * * *]
  2. 📁 file-watcher.yaml         [Watch: ~/projects]
  3. 📋 todo-triage.yaml          [Manual]
  4. 📧 calendar-sync.yaml        [Cron: 0 9 * * 1]
  5. ⚙️  manual-task.yaml          [Manual]

Actions:
  [1-5] View task details
  [n] New task
  [i] Import template
  [q] Quit

Select: █
```

This uses simple numbered menus instead of arrow key navigation. Easier to implement but less polished.

## Recommendation

**Start with Phase 1 MVP using Rich + Click**:
- Task list view with arrow key navigation
- View details, run, edit (in $EDITOR), delete
- Clean, colorful output like Claude Code
- Can always add wizard and advanced features later

**Why?** Gets 80% of value with 20% of effort. Users can already manage tasks, just with a nice interface.

## Next Steps

1. ✅ Get feedback on this plan
2. ⬜ Implement basic task list view
3. ⬜ Add navigation and actions
4. ⬜ Add colors and formatting
5. ⬜ Test with real users
6. ⬜ Iterate based on feedback

---

**Questions for discussion:**
- MVP approach (Rich + Click) vs. Full TUI (Textual)?
- Wizard vs. simple edit-in-$EDITOR approach?
- Keep dashboard separate or merge with manager?
- Any must-have features for MVP?
