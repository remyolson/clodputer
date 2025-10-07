# Installation & Claude Code Integration

**Date**: October 7, 2025
**Question**: How does Claude Code know about Clodputer?

---

## The CLAUDE.md Problem

**You're exactly right!** Claude Code needs to know:
1. That Clodputer exists
2. How to use it
3. When to create task configs
4. What the YAML schema is

**Solution**: The installation process **automatically updates your CLAUDE.md file**.

---

## Installation Flow (Complete)

### Step 1: User Installs Clodputer

```bash
$ brew install clodputer
```

**Homebrew installs**:
- `clodputer` CLI binary → `/usr/local/bin/`
- Python package → `/usr/local/lib/python3.x/site-packages/`
- Menu bar app → `/Applications/Clodputer.app`

### Step 2: User Runs Setup

```bash
$ clodputer setup
```

**Setup script does**:
1. Creates directory structure (`~/.clodputer/`)
2. Checks dependencies (Claude Code, fswatch, etc.)
3. Copies templates
4. **Automatically adds Clodputer section to CLAUDE.md** ⭐
5. Starts menu bar app

### Step 3: CLAUDE.md Auto-Update

**The setup command detects your CLAUDE.md location** and appends Clodputer instructions.

**Detection logic**:
```python
# Clodputer setup looks for CLAUDE.md in common locations:
claude_md_paths = [
    "~/CLAUDE.md",                    # Your current location
    "~/.config/claude/CLAUDE.md",     # Alternative
    "~/Documents/CLAUDE.md",          # Alternative
]

# If found, append Clodputer section
if claude_md_exists:
    append_to_claude_md()
else:
    # Ask user where their CLAUDE.md is
    print("Where is your CLAUDE.md file?")
    path = input("Path: ")
    append_to_file(path)
```

### Step 4: What Gets Added to CLAUDE.md

**Installation appends this section** (from the `CLAUDE-MD-ADDITION.md` file we created earlier):

```markdown
## Clodputer: Autonomous Task Automation

Clodputer enables you to create autonomous tasks that run automatically via cron schedules or file watchers.

### Creating Automated Tasks

When a user asks you to create an automated task (e.g., "I want you to draft email responses every morning at 8 AM"), follow these steps:

1. **Determine task type**:
   - **Scheduled**: Runs on a cron schedule (e.g., daily, hourly)
   - **File-triggered**: Runs when files appear/change in a directory
   - **Manual**: Runs only when explicitly invoked

2. **Create task configuration file** in `~/.clodputer/tasks/[task-name].yaml`

3. **Use this YAML schema**:
[... full schema from earlier ...]

4. **After creating the config**, tell the user:
   - "I've created the task configuration at ~/.clodputer/tasks/[name].yaml"
   - If scheduled: "Run `clodputer install` to activate the cron job"
   - If file-watch: "Run `clodputer watch --daemon` to start monitoring"
   - "You can test it manually with: `clodputer run [task-name]`"

[... rest of instructions ...]
```

**This is the KEY**: Once this is in CLAUDE.md, every Claude Code session knows about Clodputer!

---

## Installation Implementation

### Installer Script (`clodputer/install.py`)

```python
#!/usr/bin/env python3
"""
Clodputer Setup Script
Installs Clodputer and integrates with Claude Code
"""

import os
import sys
from pathlib import Path
import shutil

CLAUDE_MD_ADDITION = """
## Clodputer: Autonomous Task Automation

[... full content from CLAUDE-MD-ADDITION.md ...]
"""

def find_claude_md():
    """Find user's CLAUDE.md file"""
    possible_paths = [
        Path.home() / "CLAUDE.md",
        Path.home() / ".config" / "claude" / "CLAUDE.md",
        Path.home() / "Documents" / "CLAUDE.md",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None

def add_to_claude_md(claude_md_path):
    """
    Safely append Clodputer instructions to CLAUDE.md

    SAFETY FEATURES:
    - Creates backup before modification
    - Only appends, never deletes existing content
    - Checks if already added to prevent duplicates
    - Validates file integrity before and after
    """
    # 1. Create backup first
    backup_path = claude_md_path.parent / f"{claude_md_path.name}.backup-{int(time.time())}"
    shutil.copy2(claude_md_path, backup_path)
    print(f"   📦 Created backup: {backup_path}")

    # 2. Read existing content
    with open(claude_md_path, 'r', encoding='utf-8') as f:
        original_content = f.read()

    # 3. Validate file is readable
    if not original_content:
        print("   ⚠️  CLAUDE.md appears to be empty")
        user_input = input("   Continue anyway? (y/n): ")
        if user_input.lower() != 'y':
            return

    # 4. Check if already added
    if "## Clodputer:" in original_content or "# CLODPUTER INTEGRATION" in original_content:
        print("   ✅ Clodputer section already in CLAUDE.md")
        print("   Skipping to avoid duplicates")
        return

    # 5. Prepare new content (APPEND ONLY)
    new_content = original_content

    # Ensure ends with newline
    if not new_content.endswith('\n'):
        new_content += '\n'

    # Add clear separator
    new_content += '\n'
    new_content += "# " + "="*70 + "\n"
    new_content += "# CLODPUTER INTEGRATION (Auto-added by clodputer setup)\n"
    new_content += "# Do not remove this section - Claude Code needs it to create tasks\n"
    new_content += "# " + "="*70 + "\n"
    new_content += CLAUDE_MD_ADDITION

    # 6. Write atomically (write to temp file, then move)
    temp_path = claude_md_path.parent / f"{claude_md_path.name}.tmp"
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # Verify temp file
        with open(temp_path, 'r', encoding='utf-8') as f:
            verify_content = f.read()

        # Ensure nothing was lost
        if original_content not in verify_content:
            raise ValueError("Original content missing from new file!")

        # Move temp file to replace original
        shutil.move(str(temp_path), str(claude_md_path))

        print(f"   ✅ Added Clodputer section to {claude_md_path}")
        print(f"   📏 Original size: {len(original_content)} chars")
        print(f"   📏 New size: {len(new_content)} chars")
        print(f"   ➕ Added: {len(new_content) - len(original_content)} chars")

    except Exception as e:
        print(f"   ❌ Error updating CLAUDE.md: {e}")
        print(f"   🔄 Restoring from backup...")
        shutil.copy2(backup_path, claude_md_path)
        print(f"   ✅ Restored original CLAUDE.md")
        raise

    print(f"   💾 Backup kept at: {backup_path}")
    print(f"   (You can delete this backup if everything looks good)")

def setup():
    """Run Clodputer setup"""
    print("🚀 Setting up Clodputer...\n")

    # 1. Create directories
    print("📁 Creating directories...")
    clodputer_dir = Path.home() / ".clodputer"
    (clodputer_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (clodputer_dir / "templates").mkdir(exist_ok=True)
    (clodputer_dir / "archive").mkdir(exist_ok=True)
    (clodputer_dir / "watches").mkdir(exist_ok=True)
    print("   ✅ Created ~/.clodputer/")

    # 2. Copy templates
    print("\n📋 Installing task templates...")
    templates_src = Path(__file__).parent / "templates"
    templates_dst = clodputer_dir / "templates"
    if templates_src.exists():
        for template in templates_src.glob("*.yaml"):
            shutil.copy(template, templates_dst)
        print(f"   ✅ Copied {len(list(templates_src.glob('*.yaml')))} templates")

    # 3. Check dependencies
    print("\n🔍 Checking dependencies...")
    dependencies = {
        'claude': 'Claude Code',
        'fswatch': 'fswatch',
        'jq': 'jq',
        'yq': 'yq (brew install yq)',
    }

    missing = []
    for cmd, name in dependencies.items():
        if shutil.which(cmd):
            print(f"   ✅ {name}")
        else:
            print(f"   ❌ {name} not found")
            missing.append(name)

    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("   Install with: brew install " + " ".join(missing))
        sys.exit(1)

    # 4. Find and update CLAUDE.md
    print("\n📝 Integrating with Claude Code...")
    claude_md = find_claude_md()

    if claude_md:
        add_to_claude_md(claude_md)
    else:
        print("   ⚠️  CLAUDE.md not found in standard locations")
        print("   Where is your CLAUDE.md file?")
        custom_path = input("   Path (or press Enter to skip): ").strip()

        if custom_path:
            custom_path = Path(custom_path).expanduser()
            if custom_path.exists():
                add_to_claude_md(custom_path)
            else:
                print(f"   ❌ File not found: {custom_path}")
        else:
            print("   ⚠️  Skipped CLAUDE.md integration")
            print("   Claude Code won't know about Clodputer automatically")

    # 5. Initialize empty files
    print("\n📄 Creating initial files...")
    (clodputer_dir / "execution.log").touch()
    (clodputer_dir / "queue.json").write_text('{"running": null, "queued": []}')
    print("   ✅ Created log and queue files")

    # 6. Install menu bar app (macOS LaunchAgent)
    print("\n📍 Installing menu bar app...")
    if sys.platform == 'darwin':
        install_menubar_app()
        print("   ✅ Menu bar app installed (will start on next login)")
        print("   Start now: open -a Clodputer")
    else:
        print("   ⚠️  Menu bar app only supported on macOS")

    # 7. Done!
    print("\n" + "="*60)
    print("✅ Clodputer setup complete!")
    print("="*60)
    print("\n📚 Next Steps:")
    print("   1. Open Claude Code: claude")
    print('   2. Ask: "Create a daily email task at 8 AM"')
    print("   3. Claude Code will create the task config")
    print("   4. Check status: clodputer status")
    print("\n🤖 The menu bar icon shows current status")
    print("   Click it for quick access to dashboard\n")

def install_menubar_app():
    """Install menu bar app as LaunchAgent"""
    launchagent_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
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
</plist>"""

    launchagents_dir = Path.home() / "Library" / "LaunchAgents"
    launchagents_dir.mkdir(exist_ok=True)

    plist_path = launchagents_dir / "com.clodputer.menubar.plist"
    plist_path.write_text(launchagent_plist)

    # Load the agent
    os.system(f"launchctl load {plist_path}")

if __name__ == '__main__':
    setup()
```

---

## How Claude Code Becomes Aware

### Before Installation

**User asks Claude Code**: "Create a task to draft emails daily"

**Claude Code response**: "I don't have information about how to create automated tasks. Could you clarify what system you're using?"

❌ Claude Code doesn't know about Clodputer

### After Installation (CLAUDE.md Updated)

**User asks Claude Code**: "Create a task to draft emails daily"

**Claude Code response** (reads CLAUDE.md, sees Clodputer section):

```
I'll create a Clodputer task for daily email drafting.

[Creates ~/.clodputer/tasks/email-management.yaml with proper schema]

Task created successfully!

To activate:
  clodputer install

Test now:
  clodputer run email-management

This task will run automatically every day at your specified time.
```

✅ Claude Code knows exactly what to do

---

## User Experience Summary

### Installation Day

```bash
# 1. User installs
$ brew install clodputer
$ clodputer setup

✅ Clodputer setup complete!
✅ Added Clodputer section to ~/CLAUDE.md
🤖 Menu bar icon will appear on next login

# 2. User immediately tries it
$ claude

User: "Create a task to draft emails at 8 AM daily"

Claude Code: [Reads updated CLAUDE.md]
Claude Code: "I'll create a Clodputer task..."
Claude Code: [Creates ~/.clodputer/tasks/email-management.yaml]
Claude Code: "Task created! Run 'clodputer install' to activate."

User: "Activate it now"

Claude Code: [Runs: clodputer install]
Claude Code: "✅ Cron job installed. First run: tomorrow 8 AM"

# 3. Done!
```

**Key insight**: The installation automatically teaches Claude Code how to use Clodputer by updating CLAUDE.md.

---

## What If User Doesn't Have CLAUDE.md?

### Scenario: Fresh Claude Code User

**If `clodputer setup` doesn't find CLAUDE.md**:

```
⚠️  CLAUDE.md not found in standard locations.

Clodputer needs to add instructions to your CLAUDE.md file
so Claude Code knows how to create automated tasks.

Options:
  1. Provide path to existing CLAUDE.md
  2. Create a new CLAUDE.md at ~/CLAUDE.md
  3. Skip (Claude Code won't know about Clodputer)

Your choice (1/2/3): 2

✅ Created ~/CLAUDE.md with Clodputer instructions

Next: Restart any active Claude Code sessions to pick up changes.
```

**What gets created**:
```markdown
# Claude Configuration

[Minimal header with your info]

## Clodputer: Autonomous Task Automation

[Full Clodputer instructions from CLAUDE-MD-ADDITION.md]
```

---

## Alternative: Manual Integration

### If User Wants to Add Manually

**Documentation includes**:

```markdown
# Manual Integration with CLAUDE.md

If you prefer to manually add Clodputer support to your CLAUDE.md:

1. Open your CLAUDE.md file:
   $ code ~/CLAUDE.md

2. Copy the contents of this file:
   $ cat ~/.clodputer/docs/CLAUDE-MD-ADDITION.md

3. Paste at the end of your CLAUDE.md

4. Save and restart Claude Code sessions

Done! Claude Code now knows about Clodputer.
```

**The addition file is included** at `~/.clodputer/docs/CLAUDE-MD-ADDITION.md`

---

## Keeping CLAUDE.md Updated

### When Clodputer Updates

**If Clodputer gains new features** (e.g., multi-turn support in Phase 2):

```bash
$ brew upgrade clodputer
$ clodputer update-docs
```

**`update-docs` command**:
- Checks current CLAUDE.md Clodputer section
- Compares to latest template
- Shows diff
- Asks to update

```
📝 Clodputer Documentation Update Available

Changes:
  + Added: Multi-turn task support
  + Added: Cost tracking features
  ~ Updated: YAML schema with new fields

Update your CLAUDE.md? (y/n): y

✅ Updated Clodputer section in ~/CLAUDE.md
✨ Claude Code now knows about new features
```

---

## Uninstallation

### If User Wants to Remove Clodputer

```bash
$ clodputer uninstall
```

**Uninstaller does**:
1. Removes cron jobs
2. Stops file watchers
3. Removes menu bar app
4. **Removes Clodputer section from CLAUDE.md** ⭐
5. Optionally deletes `~/.clodputer/` directory

```
🗑️  Uninstalling Clodputer...

✅ Removed cron jobs
✅ Stopped file watchers
✅ Removed menu bar app
✅ Removed Clodputer section from ~/CLAUDE.md

Keep task configs and logs? (y/n): n

✅ Deleted ~/.clodputer/

Clodputer has been completely removed.
Claude Code will no longer know about Clodputer.
```

---

## Summary: The Integration Flow

1. **User installs** Clodputer via Homebrew
2. **Setup script runs**, finds CLAUDE.md
3. **Automatically appends** Clodputer instructions to CLAUDE.md
4. **Claude Code reads** CLAUDE.md on every session start
5. **Claude Code now knows** how to create Clodputer tasks
6. **User just talks** to Claude Code naturally
7. **Claude Code creates** properly formatted task configs
8. **Clodputer executes** tasks autonomously

**The magic**: Updating CLAUDE.md makes Claude Code instantly aware of Clodputer without any code changes to Claude Code itself.

---

## Questions Answered

**Q: Does installation edit CLAUDE.md?**
✅ Yes, automatically appends Clodputer section

**Q: How does Claude Code know about Clodputer?**
✅ Reads instructions from CLAUDE.md on every session

**Q: What if CLAUDE.md doesn't exist?**
✅ Setup creates one or asks for location

**Q: Can I see what will be added before installation?**
✅ Yes: `cat ~/.clodputer/docs/CLAUDE-MD-ADDITION.md`

**Q: Can I manually add instead of auto-install?**
✅ Yes, copy from CLAUDE-MD-ADDITION.md

**Q: What if I update Clodputer later?**
✅ Run `clodputer update-docs` to refresh CLAUDE.md section

---

Does this clarify the installation and integration process?
