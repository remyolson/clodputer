# Clodputer Testing: Issues and Improvements Tracker

**Last Updated**: 2025-01-09

This document tracks all issues, bugs, and improvements discovered during testing. Each entry references the test run where it was found and includes priority, status, and resolution tracking.

## Priority Levels
- 🔴 **Critical**: Blocks core functionality, causes data loss, or crashes
- 🟠 **High**: Significantly impacts user experience or causes frequent issues
- 🟡 **Medium**: Minor functionality issues or UX improvements
- 🟢 **Low**: Nice-to-have improvements, edge cases, polish

## Status Legend
- 🔵 **Open**: Issue identified, not yet addressed
- 🟣 **In Progress**: Actively being worked on
- 🟢 **Fixed**: Issue resolved, pending verification
- ✅ **Verified**: Fix confirmed through testing
- 🚫 **Won't Fix**: Issue acknowledged but will not be addressed
- 📦 **Deferred**: Will address in future release

---

## Critical Issues 🔴

_No critical issues identified yet._

---

## High Priority Issues 🟠

### Issue #1: No Non-Interactive Onboarding Mode

**Priority**: 🟠 High
**Status**: 🔵 Open
**Found In**: Test Run #001 - 2025-10-09
**Affects**: Onboarding, Testing, CI/CD

**Description**:
The `clodputer init` onboarding command is fully interactive, requiring terminal input at multiple steps. This blocks automated testing, CI/CD workflows, and scripted deployments. When run non-interactively, the command fails when waiting for user input.

**Steps to Reproduce**:
1. Run `./.venv/bin/clodputer init` in a non-interactive context
2. Command starts Step 1/7 (Directory Setup) successfully
3. Command blocks at Step 2/7 (Claude CLI Configuration) waiting for input
4. No way to provide inputs via flags, environment variables, or config file

**Expected Behavior**:
Should support non-interactive mode via:
- Command-line flags (e.g., `--claude-cli-path /path/to/claude`)
- Environment variables (e.g., `CLODPUTER_CLAUDE_CLI=/path/to/claude`)
- Config file read (e.g., `--config onboarding.yaml`)
- Auto-detection with confirmation bypass (e.g., `--yes` flag)

**Actual Behavior**:
- Onboarding always requires interactive terminal
- No flags available for automation
- Cannot test onboarding in CI/CD
- Cannot script fresh installations

**Impact**:
- Blocks automated testing of onboarding flow
- Prevents integration testing in CI/CD pipelines
- Makes scripted deployments impossible
- Increases manual testing burden

**Proposed Solution**:
Add support for non-interactive mode:
```bash
# Option 1: Command-line flags
clodputer init --claude-cli /path/to/claude --no-templates --yes

# Option 2: Environment variables
export CLODPUTER_CLAUDE_CLI=/path/to/claude
export CLODPUTER_SKIP_INTERACTIVE=true
clodputer init

# Option 3: Config file
clodputer init --config onboarding.yaml
```

**Related Issues**: None

**Resolution** (if Fixed/Verified):
_Not yet fixed_

---

## Medium Priority Issues 🟡

### Issue #2: Incorrect Default Claude CLI Path

**Priority**: 🟡 Medium
**Status**: 🔵 Open
**Found In**: Test Run #001 - 2025-10-09
**Affects**: Onboarding (Step 2/7 - Claude CLI Configuration)

**Description**:
The onboarding process offers `/usr/bin/claude` as the default Claude CLI path, but this path does not exist on macOS systems with Claude Code installed. The actual path is `/Users/[username]/.claude/local/claude`, requiring users to manually enter the correct path.

**Steps to Reproduce**:
1. Install Claude Code on macOS
2. Run `clodputer init`
3. Observe default path offered: `/usr/bin/claude`
4. Check if path exists: `ls -la /usr/bin/claude` → File not found
5. Find actual path: `which claude` → `/Users/ro/.claude/local/claude` (via alias)

**Expected Behavior**:
- Auto-detect Claude CLI path using `which claude` or similar discovery
- Offer correct default path based on detection
- If detection fails, provide helpful guidance on where to find the path

**Actual Behavior**:
- Always suggests `/usr/bin/claude` which doesn't exist
- User must know or discover the actual path manually
- No auto-detection attempted

**Impact**:
- Poor first-time user experience
- Confusing for users unfamiliar with their Claude installation
- Extra manual step required in onboarding

**Proposed Solution**:
1. Implement auto-detection logic:
   ```python
   def detect_claude_cli():
       # Try common paths
       paths = [
           Path.home() / ".claude" / "local" / "claude",
           Path("/usr/local/bin/claude"),
           Path("/usr/bin/claude"),
       ]
       for path in paths:
           if path.exists():
               return str(path)

       # Try which/where command
       result = subprocess.run(["which", "claude"], capture_output=True, text=True)
       if result.returncode == 0:
           return result.stdout.strip()

       return None  # No default if not found
   ```

2. Update onboarding prompt to use detected path or guide user if not found

**Related Issues**: None

**Resolution** (if Fixed/Verified):
_Not yet fixed_

---

### Issue #3: Installation Method Unclear for macOS Users

**Priority**: 🟡 Medium
**Status**: 🔵 Open
**Found In**: Test Run #001 - 2025-10-09
**Affects**: Installation, Documentation

**Description**:
When attempting to install Clodputer using `python3 -m pip install -e .` on macOS, users encounter an "externally-managed-environment" error due to PEP 668. The error message suggests using pipx or a virtual environment, but README documentation doesn't clearly guide users on the recommended installation method for macOS.

**Steps to Reproduce**:
1. On macOS with system Python, run: `python3 -m pip install -e .`
2. Error: `error: externally-managed-environment`
3. Error message suggests multiple options but doesn't clarify best practice
4. README doesn't have clear "Installation" section with platform-specific guidance

**Expected Behavior**:
- Clear installation instructions in README
- Platform-specific guidance (macOS vs Linux)
- Recommendation: "Use pipx for CLI installation" prominently featured
- Development setup clearly separated from user installation

**Actual Behavior**:
- No clear installation instructions in README
- Users hit PEP 668 error without guidance
- Must choose between venv, pipx, or --break-system-packages without knowing implications

**Impact**:
- Confusing first-time installation experience
- Users may choose wrong installation method
- Increases support burden
- Potential system Python breakage if users use --break-system-packages

**Proposed Solution**:
Add clear installation section to README:

```markdown
## Installation

### For Users (Recommended)
Install via pipx for isolated CLI installation:
```bash
pipx install clodputer
```

### For Development
Clone and install in editable mode:
```bash
git clone https://github.com/user/clodputer.git
cd clodputer
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Platform Notes
- **macOS**: System Python is externally managed (PEP 668). Use pipx or venv.
- **Linux**: May also have externally managed Python. Use pipx or venv.
```

**Related Issues**: None

**Resolution** (if Fixed/Verified):
_Not yet fixed_

---

## Low Priority Issues 🟢

_No low priority issues identified yet._

---

## Issue Template

Use this template when adding new issues:

```markdown
### Issue #[N]: [Brief Description]

**Priority**: [Critical/High/Medium/Low]
**Status**: [Open/In Progress/Fixed/Verified/Won't Fix/Deferred]
**Found In**: Test Run #[X] - [YYYY-MM-DD]
**Affects**: [Installation/Onboarding/Execution/etc.]

**Description**:
[Detailed description of the issue]

**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]
3. [etc.]

**Expected Behavior**:
[What should happen]

**Actual Behavior**:
[What actually happens]

**Impact**:
[How this affects users]

**Proposed Solution**:
[Optional: Suggested fix or workaround]

**Related Issues**:
[Reference to related issues if any]

**Resolution** (if Fixed/Verified):
- **Fixed In**: Commit [hash] - [date]
- **Fix Description**: [What was changed]
- **Verified By**: Test Run #[Y] - [YYYY-MM-DD]
```

---

## Testing Insights

### Patterns Observed
_Section for noting recurring patterns across multiple test runs_

### User Experience Notes
_Section for documenting UX observations that aren't bugs but impact usability_

### Performance Observations
_Section for tracking resource usage patterns and performance trends_

---

## Improvement Ideas

### Feature Enhancements
_Ideas for new features or significant improvements discovered during testing_

### Documentation Needs
_Areas where documentation is missing, unclear, or needs expansion_

### Testing Infrastructure
_Improvements needed to the testing process itself_

---

## Resolved Issues Archive

Once an issue is Verified, it will be moved to this archive section after 30 days.

_No archived issues yet._

---

## Statistics

- **Total Issues Logged**: 3
- **Critical Open**: 0
- **High Open**: 1 (Issue #1)
- **Medium Open**: 2 (Issues #2, #3)
- **Low Open**: 0
- **In Progress**: 0
- **Fixed (Pending Verification)**: 0
- **Verified**: 0
- **Test Runs Completed**: 1 (Test Run #001 - In Progress)
