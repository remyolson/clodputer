# Clodputer User Experience & Interface Design

**Date**: October 7, 2025
**Focus**: Installation, daily use, visibility, and control

---

## User Experience Philosophy

**Core Principle**: Clodputer runs invisibly in the background. You interact with it primarily through **Claude Code conversations** and occasionally through a **CLI** for status checks.

**Key Insight**: You're not "using an app" - you're telling Claude Code what to automate, and Clodputer makes it happen.

---

## Installation & Onboarding

### Installation Method: Homebrew (Recommended)

**Goal**: Install in under 2 minutes with one command.

```bash
# Install Clodputer
brew install clodputer

# Setup (creates directories, checks dependencies)
clodputer setup

# Done! No app opens, no GUI appears.
```

**What happens during setup**:
1. Creates `~/.clodputer/` directory structure
2. Checks for Claude Code installation
3. Installs Python dependencies (watchdog, psutil, etc.)
4. Copies task templates to `~/.clodputer/templates/`
5. Shows success message with next steps

**Alternative**: Manual Installation (for developers)
```bash
git clone https://github.com/yourusername/clodputer.git
cd clodputer
./install.sh
```

### First-Run Experience

After installation, user sees this terminal output:

```
✅ Clodputer installed successfully!

What is Clodputer?
  Clodputer lets Claude Code work autonomously. Schedule tasks,
  watch files, and automate your workflows.

Next Steps:
  1. Ask Claude Code to create an automated task:
     "Create a daily task to draft email responses at 8 AM"

  2. Check status anytime:
     clodputer status

  3. View available commands:
     clodputer --help

📚 Documentation: https://github.com/yourusername/clodputer

🤖 Menu bar icon shows status. Click for dashboard and logs!
```

**Key Point**: User doesn't open any app. They just installed a tool that Claude Code can now use.

---

## Interface: Menu Bar + CLI (No Heavy GUI)

**Important**: Clodputer is **NOT a traditional desktop application**. There is:
- ❌ No app icon in Dock
- ✅ **Menu bar status indicator** (shows running/idle/error state)
- ❌ No heavy GUI windows or settings panels
- ✅ **Terminal dashboard** (launched from menu bar)

**Why Menu Bar?**: For a background daemon, a persistent status indicator builds user trust. Users can glance at the menu bar to see if Clodputer is working, idle, or has errors. The menu bar provides:
1. **At-a-glance status** (🟢 idle, 🔵 running, 🔴 error)
2. **Quick access** to dashboard and logs
3. **Visibility** without being intrusive

**Primary Interfaces**:
1. **Menu bar icon** (status visibility)
2. **Claude Code conversations** (creating/managing tasks)
3. **Terminal dashboard** (detailed monitoring)
4. **CLI commands** (quick status checks)

---

## Primary Interface: Claude Code Conversations

### How Users Interact

**User talks to Claude Code in terminal**:

```
User: "I want you to draft email responses every morning at 8 AM"

Claude Code:
I'll create an automated task for you.

[Creates ~/.clodputer/tasks/email-management.yaml]

✅ Task created: email-management
📍 Location: ~/.clodputer/tasks/email-management.yaml
⏰ Schedule: Daily at 8:00 AM
🔧 To activate: Run `clodputer install`

Want me to activate it now? (Yes/No)

User: "Yes"

Claude Code:
[Runs: clodputer install]

✅ Cron job installed
📅 Next run: Tomorrow at 8:00 AM
📊 Test it now: clodputer run email-management
📝 View logs: clodputer logs

Your email automation is ready!
```

**User doesn't**:
- Open any app
- Click any buttons
- See any GUI

**User does**:
- Talk to Claude Code naturally
- Let Claude Code create and manage tasks
- Use CLI for quick status checks

---

## Secondary Interface: CLI Commands

### Quick Status Checks

**User wants to know what's happening**:

```bash
$ clodputer status
```

**Output**:
```
🤖 Clodputer Status

QUEUE: 1 running, 0 waiting
  🔵 [RUNNING] email-management (2m 30s elapsed)

RECENT EXECUTIONS (last 10):
  ✅ 2025-10-07 08:00 | email-management | 45s | Success
  ✅ 2025-10-06 17:30 | project-sync | 2m 10s | Success
  ❌ 2025-10-06 12:00 | todo-automation | 15s | Failed: Permission denied
  ✅ 2025-10-06 08:00 | email-management | 52s | Success

STATS TODAY:
  ✅ 3 successful | ❌ 1 failed
  ⏱️  3m 47s total runtime

📝 Full logs: clodputer logs
📋 View queue: clodputer queue
```

### View Logs

```bash
$ clodputer logs
```

**Output**: Displays `~/.clodputer/execution.log` (auto-updates, tail -f style)

### List Tasks

```bash
$ clodputer list
```

**Output**:
```
📋 Configured Tasks

SCHEDULED TASKS (2):
  ✅ email-management - Daily at 8:00 AM
  ✅ weekly-research - Mondays at 9:00 AM

FILE WATCHERS (1):
  ✅ project-assignments - ~/todos/claude-assignments/*.md

MANUAL TASKS (0):
  (none)

💡 Create tasks by asking Claude Code
📍 Configs: ~/.clodputer/tasks/
```

### Manual Task Execution

```bash
$ clodputer run email-management
```

**Output**:
```
🚀 Running: email-management

⏳ Starting Claude Code instance...
🔄 Executing task...
✅ Task completed successfully in 48s

📊 Results:
  - Drafted 3 email responses
  - Archived 5 old drafts
  - Saved to: ~/email-responses/

📝 Full log: clodputer logs
```

### System Diagnostics

```bash
$ clodputer doctor
```

**Output**:
```
🩺 Clodputer System Diagnostics

CHECKING INSTALLATION:
  ✅ ~/.clodputer directory exists
  ✅ Config directory writable
  ✅ Log directory exists

CHECKING DEPENDENCIES:
  ✅ Claude Code installed (version 2.5.0)
  ✅ Python 3.11.5 (>= 3.9 required)
  ✅ All Python packages installed

CHECKING CONFIGURATION:
  ✅ Found 3 task configs
  ✅ All YAML files valid
  ✅ All task configs pass Pydantic validation

CHECKING PROCESS STATE:
  ✅ No stale lock file
  ✅ No orphaned MCP processes
  ⚠️  Queue has 1 task stuck in 'running' state for 2 hours
      Run: clodputer queue reset

CHECKING INTEGRATION:
  ✅ CLAUDE.md integration present
  ✅ Cron jobs installed (2 tasks)
  ✅ File watcher running (PID 12345)

SUMMARY: 15 checks passed, 1 warning

💡 For help, run: clodputer --help
📝 View logs: clodputer logs
```

**Use Cases**:
- Troubleshooting when something isn't working
- Verifying installation completed successfully
- Checking for stale processes or locks
- Validating task configurations

**What It Checks**:
1. Directory structure exists and is writable
2. Dependencies installed (Claude Code, Python packages)
3. All task YAML files are valid
4. No stale lockfiles or orphaned processes
5. CLAUDE.md integration is present
6. Scheduled tasks are properly installed
7. File watchers are running

---

## File System Structure (User-Visible)

### Where Everything Lives

```
~/.clodputer/                          # Main directory
├── tasks/                             # 👀 USER LOOKS HERE
│   ├── email-management.yaml          # Task configs
│   ├── project-assignments.yaml
│   └── weekly-research.yaml
│
├── templates/                         # Reference examples
│   ├── daily-task.yaml
│   ├── file-watcher.yaml
│   └── manual-task.yaml
│
├── execution.log                      # 👀 USER LOOKS HERE
│                                      # Current status & history
│
├── queue.json                         # Queue state (usually ignore)
├── clodputer.lock                     # Lock file (usually ignore)
│
└── archive/                           # Historical logs
    ├── 2025-10.log
    └── 2025-09.log
```

### User Can Browse Tasks

**Open in Finder**:
```bash
$ open ~/.clodputer/tasks/
```

**See all task configs as YAML files**:
- `email-management.yaml`
- `project-assignments.yaml`
- `weekly-research.yaml`

**User can**:
- Read configs to understand what tasks do
- Edit configs manually (if comfortable with YAML)
- Delete configs to remove tasks
- Duplicate configs to create similar tasks

**But most users will**:
- Ask Claude Code to manage tasks instead

---

## Visibility: How Users Know It's Working

### 1. Terminal Notifications (Failures Only)

When a task fails, user sees macOS notification:

```
┌─────────────────────────────────────┐
│  🤖 Clodputer                       │
│                                     │
│  ❌ Task Failed: email-management   │
│                                     │
│  Error: Permission denied           │
│  accessing ~/email-responses/       │
│                                     │
│  📝 Details: clodputer logs         │
└─────────────────────────────────────┘
```

**No notification for successes** (to avoid spam).

### 2. Log File (Always Current)

User can open `~/.clodputer/execution.log` anytime:

```bash
$ cat ~/.clodputer/execution.log
```

**Or** use:
```bash
$ clodputer logs       # Pretty-printed version
```

**This shows**:
- What's currently running
- What's in the queue
- Recent execution history
- Today's stats

### 3. Results in Expected Locations

**For email task**: User opens `~/email-responses/` folder
- Sees new draft files: `2025-10-07-meeting-followup.md`
- Knows task ran successfully

**For project task**: User checks project file
- Sees status updates: `🟢 complete`
- Knows tasks were executed

**Silent success**: If task runs successfully, user just sees the results where they expect them.

---

## Daily Usage Patterns

### Typical Day for a User

**Morning (8:00 AM)**:
- Email task runs automatically (user doesn't notice)
- User later opens `~/email-responses/` folder
- Sees 3 new draft emails ready to review and send

**Afternoon (2:00 PM)**:
- User drops `new-project.md` into `~/todos/claude-assignments/`
- File watcher triggers immediately (user doesn't see this)
- 5 minutes later, user opens the file
- Sees tasks marked complete: `🟢 complete`

**Evening (checking status)**:
- User curious about what ran today:
  ```bash
  $ clodputer status
  ```
- Sees summary of tasks executed
- Everything looks good

**On failure** (rare):
- User gets macOS notification
- Checks logs: `clodputer logs`
- Sees error message
- Asks Claude Code to fix issue

### Power User Workflow

**Creating new automation**:
```
Terminal: claude

User: "I want to research AI news every Monday morning and save a summary"

Claude Code: [Creates weekly-research.yaml task]

User: "Show me the config"

Claude Code: [Displays ~/.clodputer/tasks/weekly-research.yaml contents]

User: "Looks good, activate it"

Claude Code: [Runs: clodputer install]
```

**Checking what's automated**:
```bash
$ clodputer list

# See all tasks, schedules, status
```

**Testing a task manually**:
```bash
$ clodputer run weekly-research

# Watch it execute in real-time
```

---

## Menu Bar Option (Future Enhancement)

### Optional: Lightweight Status Indicator

**If we add a menu bar icon later** (not in MVP):

```
Menu bar: [🤖] icon

Click icon:
┌─────────────────────────────────┐
│ 🤖 Clodputer                    │
├─────────────────────────────────┤
│ ● Running: email-management     │
│ ⏸️  Queued: 0 tasks              │
│                                 │
│ Recent: 3 ✅ | 0 ❌             │
│                                 │
├─────────────────────────────────┤
│ 📊 View Status                  │
│ 📝 View Logs                    │
│ ⚙️  Open Tasks Folder           │
│ 🔄 Refresh                      │
└─────────────────────────────────┘
```

**But for MVP**: No menu bar icon. Just CLI.

**Why defer?**:
- Adds development complexity
- Most users won't use it
- CLI is sufficient for status checks
- Can add later if users request it

---

## Onboarding Flow (Complete Example)

### Step 1: Installation

```bash
$ brew install clodputer

==> Installing clodputer
🍺  clodputer was installed successfully!

$ clodputer setup

✅ Clodputer setup complete!

📁 Created:
  - ~/.clodputer/tasks/
  - ~/.clodputer/templates/
  - ~/.clodputer/execution.log

✅ Dependencies verified:
  - Claude Code: v2.0.0
  - fswatch: 1.17.1
  - jq: 1.7.1
  - yq: 4.40.5

🚀 Ready to go!

Next: Ask Claude Code to create your first automated task.
Example: "Create a task to draft emails every morning at 8 AM"
```

### Step 2: Create First Task (via Claude Code)

```bash
$ claude

User: "Create a task that drafts email responses every morning at 8 AM and saves them to ~/email-responses/"

Claude Code:
I'll create a daily email automation task for you.

[Creates ~/.clodputer/tasks/email-management.yaml]

Task Configuration:
  Name: email-management
  Schedule: Daily at 8:00 AM (America/Los_Angeles)
  Actions:
    - Read unread emails from past 24 hours
    - Draft responses based on context and your writing style
    - Save to ~/email-responses/YYYY-MM-DD-[subject].md
    - Archive old drafts

To activate this task:
  clodputer install

Would you like me to activate it now?

User: "Yes"

Claude Code:
[Executes: clodputer install]

✅ Cron job installed successfully!

Your email automation is active:
  • Next run: Tomorrow at 8:00 AM
  • Test now: clodputer run email-management
  • View status: clodputer status

I'll draft email responses automatically every morning.
```

### Step 3: First Execution (Next Morning)

**8:00 AM - Task runs automatically**

User doesn't see anything (runs in background).

**8:01 AM - User checks email responses**

```bash
$ open ~/email-responses/

# Folder contents:
2025-10-08-meeting-followup.md
2025-10-08-project-update-request.md
2025-10-08-vendor-inquiry.md
```

User opens files, reviews drafts, sends emails.

**If user is curious**:
```bash
$ clodputer status

🤖 Clodputer Status

RECENT EXECUTIONS:
  ✅ 2025-10-08 08:00 | email-management | 52s | Success
     Drafted 3 responses, archived 4 old drafts

# User sees it worked perfectly
```

### Step 4: Ongoing Use

**User creates more tasks over time**:
- "Create a weekly research summary task"
- "Watch my todos folder and execute project files"
- "Sync my calendar with my todo list daily"

**Claude Code creates all these**. User just talks naturally.

**User checks status occasionally**:
```bash
$ clodputer status       # Quick check
$ clodputer list         # See all tasks
$ clodputer logs         # Detailed history
```

**User rarely thinks about Clodputer** - it just works invisibly.

---

## Error Handling UX

### When a Task Fails

**User sees notification**:
```
┌─────────────────────────────────────┐
│  🤖 Clodputer                       │
│  ❌ Task Failed: email-management   │
│  Check logs for details             │
└─────────────────────────────────────┘
```

**User checks logs**:
```bash
$ clodputer logs

RECENT EXECUTIONS:
  ❌ 2025-10-08 08:00 | email-management | 15s | Failed
     Error: Gmail MCP authentication expired
     Solution: Run `npx @gongrzhe/server-gmail-autoauth-mcp auth`
```

**User asks Claude Code to fix**:
```bash
$ claude

User: "Clodputer failed to run email task - Gmail auth expired"

Claude Code:
I'll help you re-authenticate the Gmail MCP.

[Runs: npx @gongrzhe/server-gmail-autoauth-mcp auth]

Please complete the OAuth flow in your browser...

[User completes OAuth]

✅ Gmail MCP re-authenticated successfully!

Let me test the email task now:
[Runs: clodputer run email-management]

✅ Task completed successfully!

Your automation is working again. Tomorrow's scheduled run should succeed.
```

---

## Comparison: What Clodputer Is and Isn't

### What Clodputer IS:
- ✅ Background automation system
- ✅ CLI tool for status checks
- ✅ Set of files in `~/.clodputer/`
- ✅ Integration with Claude Code
- ✅ Cron jobs + file watchers

### What Clodputer is NOT:
- ❌ Desktop application with GUI
- ❌ App icon in Dock
- ❌ Menu bar app (at least not in MVP)
- ❌ Settings panel or preferences window
- ❌ Something you "open" and "use"

### Mental Model:

**Wrong mental model**: "Clodputer is an app I open to automate things"

**Correct mental model**: "Clodputer is a tool Claude Code uses to run tasks automatically. I just tell Claude Code what to automate, and Clodputer handles it in the background."

---

## Summary: User Journey

1. **Install** via Homebrew (`brew install clodputer && clodputer setup`)
2. **Create tasks** by talking to Claude Code ("automate my email drafting")
3. **Tasks run automatically** in background (cron, file watchers)
4. **See results** in expected locations (files, folders)
5. **Check status** occasionally via CLI (`clodputer status`)
6. **Fix issues** by asking Claude Code (if notifications appear)

**Key takeaway**: User interacts with **Claude Code**, not with Clodputer directly. Clodputer is the invisible infrastructure that makes automation work.

---

## Open Questions

1. **Do you want a menu bar icon** (even as optional future enhancement)?

2. **Should `clodputer status` auto-run** after task completions? (So terminal shows brief status update)

3. **Should there be a dashboard command** (`clodputer dashboard`) that opens a browser-based view of task history? (Like a simple HTML report)

4. **Notification detail level**: Should notifications show more context (e.g., first line of error), or keep them brief?

Let me know your thoughts on the UX as described!
