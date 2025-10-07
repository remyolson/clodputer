# Menu Bar Icon & Interface Design

**Date**: October 7, 2025
**Status**: Refined based on user feedback

---

## Menu Bar Icon Design

### Visual Design

**Icon in menu bar**: `🤖` or simplified robot icon (monochrome to match macOS style)

**States**:
- **Idle**: Gray robot icon (no tasks running)
- **Running**: Blue robot icon + subtle animation (task executing)
- **Error**: Red dot badge on icon (recent failure)

---

## Menu Bar Dropdown

### Click icon → Small dropdown menu appears

```
┌──────────────────────────────────────┐
│ 🤖 Clodputer                         │
├──────────────────────────────────────┤
│ STATUS                               │
│ ● Running: email-management (2m 15s) │
│ ⏸️  Queue: 0 tasks waiting            │
│                                      │
│ RECENT (Last 3)                      │
│ ✅ email-management (8:00 AM)        │
│ ✅ weekly-research (Mon 9:00 AM)     │
│ ❌ todo-automation (Failed)          │
│                                      │
│ TODAY: 3 tasks (2 ✅ | 1 ❌)         │
├──────────────────────────────────────┤
│ 📊 Open Dashboard...                 │
│ 📁 Open Tasks Folder                 │
│ ⚙️  Settings...                      │
├──────────────────────────────────────┤
│ 🔄 Refresh                           │
│ 🚪 Quit Clodputer                    │
└──────────────────────────────────────┘
```

### Primary Action: "Open Dashboard"

**Clicks "📊 Open Dashboard..."**

**Two implementation options**:

---

## Option A: Terminal-Based Dashboard (Recommended)

**Click "Open Dashboard" → Opens Terminal window with interactive CLI**

```
┌─────────────────────────────────────────────────────────┐
│ Terminal                                       🔴 🟡 🟢 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  🤖 Clodputer Dashboard                                 │
│  ═══════════════════════════════════════════════════    │
│                                                          │
│  ┌─ QUEUE ─────────────────────────────────────┐       │
│  │ 🔵 RUNNING: email-management (2m 30s)        │       │
│  │ ⏸️  QUEUED: 0 tasks                           │       │
│  └──────────────────────────────────────────────┘       │
│                                                          │
│  ┌─ CONFIGURED TASKS ───────────────────────────┐      │
│  │ SCHEDULED (2 tasks):                         │       │
│  │  ✅ email-management - Daily 8:00 AM         │       │
│  │  ✅ weekly-research - Mon 9:00 AM            │       │
│  │                                              │       │
│  │ WATCHERS (1 task):                           │       │
│  │  ✅ project-assignments                       │       │
│  │     ~/todos/claude-assignments/*.md          │       │
│  └──────────────────────────────────────────────┘       │
│                                                          │
│  ┌─ RECENT EXECUTIONS ──────────────────────────┐      │
│  │ ✅ 08:00 | email-management | 45s | Success   │      │
│  │ ✅ 07:30 | project-sync | 2m 10s | Success    │      │
│  │ ❌ 12:00 | todo-automation | 15s | Failed     │      │
│  │    └─ Error: Permission denied                │      │
│  │ ✅ 08:00 | email-management | 52s | Success   │      │
│  └──────────────────────────────────────────────┘       │
│                                                          │
│  ┌─ ACTIONS ─────────────────────────────────────┐     │
│  │ [R] Refresh  [L] Logs  [Q] Queue  [H] Help    │     │
│  └──────────────────────────────────────────────┘       │
│                                                          │
│  Press key or Ctrl+C to exit                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Interactive Commands**:
- Press **R** → Refresh status
- Press **L** → View full logs (scrollable)
- Press **Q** → View queue details
- Press **H** → Help menu
- Press **Ctrl+C** → Exit dashboard

**Implementation**: Python with `curses` library (built-in, no dependencies)

**Advantages**:
- No web browser required
- Fast and lightweight
- Keyboard-friendly
- Follows terminal aesthetic
- Easy to implement

---

## Option B: Browser-Based Dashboard

**Click "Open Dashboard" → Opens `http://localhost:8765/` in default browser**

### Dashboard Layout

```html
┌─────────────────────────────────────────────────┐
│ 🤖 Clodputer Dashboard          [Refresh] [⚙️]  │
├─────────────────────────────────────────────────┤
│                                                  │
│  📊 Status                                       │
│  ┌──────────────────────────────────────────┐  │
│  │ 🔵 RUNNING                                │  │
│  │    email-management (2m 30s elapsed)     │  │
│  │                                          │  │
│  │ ⏸️  QUEUE: 0 tasks                        │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  📋 Configured Tasks                            │
│  ┌──────────────────────────────────────────┐  │
│  │ Scheduled Tasks (2)                       │  │
│  │ ✅ email-management                       │  │
│  │    Daily at 8:00 AM                      │  │
│  │    [▶️ Run Now] [📝 Edit] [🗑️ Delete]     │  │
│  │                                          │  │
│  │ ✅ weekly-research                        │  │
│  │    Mondays at 9:00 AM                    │  │
│  │    [▶️ Run Now] [📝 Edit] [🗑️ Delete]     │  │
│  │                                          │  │
│  │ File Watchers (1)                        │  │
│  │ ✅ project-assignments                    │  │
│  │    ~/todos/claude-assignments/*.md       │  │
│  │    [⏸️ Pause] [📝 Edit] [🗑️ Delete]       │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  📜 Recent Executions                           │
│  ┌──────────────────────────────────────────┐  │
│  │ ✅ 2025-10-08 08:00 | email-management   │  │
│  │    Duration: 45s | Cost: $0.03          │  │
│  │    Drafted 3 responses, archived 4       │  │
│  │    [📝 View Details]                     │  │
│  │                                          │  │
│  │ ❌ 2025-10-08 12:00 | todo-automation    │  │
│  │    Duration: 15s | Failed                │  │
│  │    Error: Permission denied              │  │
│  │    [📝 View Details] [🔄 Retry]          │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  [+ Create New Task via Claude Code]            │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Implementation**:
- Python Flask app (lightweight web server)
- Simple HTML/CSS (no React/frameworks needed)
- WebSocket for live updates (optional)

**Advantages**:
- Richer UI (buttons, colors, layout)
- Clickable actions
- Copy-paste friendly
- Familiar interface

**Disadvantages**:
- Requires web server running
- More complex implementation
- Browser dependency

---

## Recommended: Hybrid Approach

### Menu Bar Icon with Smart Routing

**Level 1: Menu Bar Icon**
- Shows current status (running/idle/error)
- Click opens dropdown with quick info + actions

**Level 2: Click "Open Dashboard"**
- **First time**: Opens Terminal dashboard (Option A)
- Shows onboarding: "Welcome to Clodputer! Here's how it works..."
- Teaches keyboard shortcuts (R, L, Q, etc.)

**Level 3: Advanced (Optional)**
- Menu dropdown has both options:
  - "📊 Open Dashboard (Terminal)"
  - "🌐 Open Dashboard (Browser)"
- User can choose preference
- Browser dashboard requires `clodputer serve` running in background

**For MVP**: Menu bar icon → Terminal dashboard only

**Post-MVP**: Add browser dashboard as optional feature

---

## Onboarding Flow with Menu Bar

### First Launch After Installation

**Menu bar icon appears** with notification:

```
┌─────────────────────────────────────┐
│  🤖 Clodputer                       │
│                                     │
│  Welcome! Clodputer is installed.  │
│                                     │
│  Click menu bar icon to get started│
└─────────────────────────────────────┘
```

**User clicks icon → Dropdown shows**:

```
┌──────────────────────────────────────┐
│ 🤖 Clodputer - Welcome!              │
├──────────────────────────────────────┤
│ 👋 Getting Started                   │
│                                      │
│ Clodputer lets Claude Code work      │
│ autonomously with scheduled tasks    │
│ and file watchers.                   │
│                                      │
│ Next Steps:                          │
│  1️⃣ Open Dashboard to learn more     │
│  2️⃣ Ask Claude Code to create a task│
│  3️⃣ Check back here for status      │
│                                      │
│ 📖 Read Documentation                │
│ 📊 Open Dashboard                    │
│ 💬 Ask Claude Code                   │
└──────────────────────────────────────┘
```

**Click "📊 Open Dashboard" → Terminal opens**:

```
┌─────────────────────────────────────────────────────────┐
│  🤖 Clodputer - Getting Started                         │
│  ═══════════════════════════════════════════════════    │
│                                                          │
│  Welcome to Clodputer!                                  │
│                                                          │
│  What is Clodputer?                                     │
│  Clodputer automates Claude Code tasks:                 │
│   • Schedule tasks (daily email drafting)              │
│   • Watch files (auto-execute projects)                │
│   • Run tasks in background                            │
│                                                          │
│  You have 0 tasks configured.                           │
│                                                          │
│  ┌─ Quick Start ─────────────────────────────────┐     │
│  │                                               │     │
│  │ 1. Open Claude Code in Terminal:              │     │
│  │    $ claude                                   │     │
│  │                                               │     │
│  │ 2. Ask Claude to create a task:               │     │
│  │    "Create a task to draft emails daily      │     │
│  │     at 8 AM"                                  │     │
│  │                                               │     │
│  │ 3. Claude Code will:                          │     │
│  │    • Create task config                       │     │
│  │    • Install cron job                         │     │
│  │    • Show you status here                     │     │
│  │                                               │     │
│  └───────────────────────────────────────────────┘     │
│                                                          │
│  When you have tasks, this dashboard will show:         │
│   • Running tasks                                       │
│   • Queue status                                        │
│   • Recent executions                                   │
│   • Task configurations                                 │
│                                                          │
│  [N] Next: View example tasks                          │
│  [D] Documentation                                      │
│  [Q] Quit                                               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Press N → Shows example task templates**

**Press D → Opens documentation in browser**

---

## Menu Bar App Implementation

### Background Process

**Install creates LaunchAgent** (macOS):

```xml
~/Library/LaunchAgents/com.clodputer.menubar.plist

<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.clodputer.menubar</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/clodputer-menubar</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

**Auto-starts on login**, runs in background.

### Tech Stack

**Menu Bar App**:
- Python with `rumps` library (super lightweight)
- Reads `~/.clodputer/queue.json` and `execution.log`
- Updates icon state every 5 seconds

**Terminal Dashboard**:
- Python with `curses` library
- Launched via `open -a Terminal "clodputer dashboard"`

**Example rumps code**:
```python
import rumps

class ClodputerApp(rumps.App):
    def __init__(self):
        super().__init__("🤖", quit_button=None)
        self.menu = [
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Open Tasks Folder", callback=self.open_tasks),
            rumps.separator,
            rumps.MenuItem("Refresh", callback=self.refresh),
            rumps.MenuItem("Quit", callback=rumps.quit_application)
        ]

    @rumps.timer(5)  # Update every 5 seconds
    def update_status(self, _):
        status = self.get_status()
        if status['running']:
            self.icon = "🔵"  # Blue when running
        elif status['errors']:
            self.icon = "🔴"  # Red when errors
        else:
            self.icon = "🤖"  # Gray when idle

    def open_dashboard(self, _):
        os.system("osascript -e 'tell app \"Terminal\" to do script \"clodputer dashboard\"'")

if __name__ == "__main__":
    ClodputerApp().run()
```

---

## Settings Menu

**Click "⚙️ Settings..." in dropdown**:

Opens Terminal with config editor:

```
┌─────────────────────────────────────────────────────────┐
│  ⚙️  Clodputer Settings                                  │
│  ═══════════════════════════════════════════════════    │
│                                                          │
│  General                                                 │
│  ┌───────────────────────────────────────────────┐     │
│  │ Auto-start menu bar on login:    [✓] Yes      │     │
│  │ Check for updates:               [✓] Weekly   │     │
│  │ Notification sound:              [✓] Enabled  │     │
│  └───────────────────────────────────────────────┘     │
│                                                          │
│  Execution                                               │
│  ┌───────────────────────────────────────────────┐     │
│  │ Max concurrent tasks:            [1]          │     │
│  │ Default timeout:                 [3600s]      │     │
│  │ Retry failed tasks:              [ ] Disabled │     │
│  └───────────────────────────────────────────────┘     │
│                                                          │
│  Notifications                                           │
│  ┌───────────────────────────────────────────────┐     │
│  │ Notify on success:               [ ] Disabled │     │
│  │ Notify on failure:               [✓] Enabled  │     │
│  │ Show in menu bar:                [✓] Always   │     │
│  └───────────────────────────────────────────────┘     │
│                                                          │
│  Advanced                                                │
│  ┌───────────────────────────────────────────────┐     │
│  │ Claude Code path:    /usr/local/bin/claude   │     │
│  │ Log location:        ~/.clodputer/            │     │
│  │ Debug mode:          [ ] Disabled             │     │
│  └───────────────────────────────────────────────┘     │
│                                                          │
│  [S] Save  [R] Reset to defaults  [Q] Quit              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

Saves to: `~/.clodputer/config.yaml`

---

## Summary: Menu Bar Experience

### What User Sees

1. **Menu bar icon** (🤖) - always visible, shows status
2. **Click icon** → Quick dropdown with recent info
3. **Click "Open Dashboard"** → Terminal with full interactive interface
4. **Settings** → Terminal-based config editor

### Key Features

- **Minimal UI**: Terminal-based, no heavy frameworks
- **Quick access**: Menu bar always visible
- **Rich dashboard**: Full status, logs, task list
- **Onboarding**: First-time guide in dashboard
- **Settings**: Simple config management

### Implementation Complexity

- **Menu bar app**: ~200 lines Python (rumps)
- **Terminal dashboard**: ~500 lines Python (curses)
- **Settings editor**: ~100 lines Python
- **Total**: ~800 lines, very manageable for MVP

---

## Your Choice

Which do you prefer?

**Option 1**: Menu bar → Terminal dashboard only (cleaner, simpler)

**Option 2**: Menu bar → Terminal dashboard + optional browser dashboard

**Option 3**: Menu bar → Browser dashboard only (richer UI, more complex)

I'd recommend **Option 1** for MVP, with Option 2 as post-MVP enhancement.

What do you think?
