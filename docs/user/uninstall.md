# Uninstall Guide

This guide explains how to uninstall Clodputer completely or reset it for fresh testing.

## Quick Uninstall (Complete Removal)

To completely remove Clodputer from your system, **copy and paste this single line**:

```bash
clodputer uninstall 2>/dev/null; clodputer watch --stop 2>/dev/null; pipx uninstall clodputer; rm -rf ~/.clodputer; echo "✅ Clodputer completely removed"
```

<details>
<summary>Or run these commands step-by-step</summary>

```bash
clodputer uninstall 2>/dev/null
clodputer watch --stop 2>/dev/null
pipx uninstall clodputer
rm -rf ~/.clodputer
echo "✅ Clodputer completely removed"
```

**Note**: Run each line separately, not all at once with the comments.

</details>

## What Gets Removed

The complete uninstall removes:

- ✅ **Cron jobs** - All scheduled task automation
- ✅ **File watchers** - Any running file monitoring daemons
- ✅ **Package** - The clodputer CLI itself
- ✅ **Data directory** (`~/.clodputer/`) including:
  - Task definitions (YAML files)
  - State file (env.json)
  - Execution logs
  - Onboarding logs
  - Queue state
  - Archive directory

## Reset for Testing (Keep Package Installed)

If you want to test the onboarding process repeatedly without reinstalling:

### Method 1: Built-in Reset (Recommended)

```bash
clodputer init --reset
```

This will:
- Clear state file (`env.json`)
- Clear onboarding log
- Run the onboarding wizard from scratch

### Method 2: Manual Reset

```bash
# Remove all data
rm -rf ~/.clodputer

# Run onboarding again
clodputer init
```

### Method 3: Selective Reset

If you only want to reset specific parts:

```bash
# Clear just the state file (keeps tasks and logs)
rm ~/.clodputer/env.json

# Clear just the queue
clodputer queue --clear

# Clear just the onboarding log
rm ~/.clodputer/onboarding.log
```

## Reinstall After Uninstall

After complete removal, reinstall with:

```bash
# Install from PyPI
pipx install clodputer

# Run onboarding
clodputer init
```

## Troubleshooting

### "Command not found" after uninstall

This is expected - the package has been removed. Reinstall with `pipx install clodputer`.

### Cron jobs still running after uninstall

Manually check and remove them:

```bash
# View crontab
crontab -l

# Edit and remove clodputer entries
crontab -e
```

### File watcher still running

Kill it manually:

```bash
# Find the process
ps aux | grep clodputer

# Kill by PID (replace <PID> with actual number)
kill <PID>
```

### Permission errors when removing ~/.clodputer

Add sudo if needed:

```bash
sudo rm -rf ~/.clodputer
```

## Partial Uninstall

If you want to keep the package but remove automation:

```bash
# Remove cron scheduling only
clodputer uninstall

# Stop file watcher only
clodputer watch --stop

# Clear task queue only
clodputer queue --clear
```

## Upgrade vs. Uninstall

To upgrade Clodputer without losing your data:

```bash
# Upgrade in place (keeps ~/.clodputer/ intact)
pipx upgrade clodputer

# Verify new version
clodputer --version
```

Your tasks, state, and logs are preserved during upgrades.

## See Also

- [Installation Guide](installation.md) - How to install Clodputer
- [Quick Start](quick-start.md) - First-time setup walkthrough
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
