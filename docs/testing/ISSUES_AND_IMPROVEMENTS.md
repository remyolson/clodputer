# Clodputer Testing: Issues and Improvements Tracker

**Last Updated**: 2025-10-09

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
**Status**: ✅ Verified
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

**Resolution**:
- **Fixed In**: Commit 94a25a5 - 2025-10-09
- **Fix Description**:
  - Added CLI flags: `--claude-cli <path>`, `--yes`, `--no-templates`, `--no-automation`
  - Environment variable support: `CLODPUTER_CLAUDE_BIN`
  - Updated all onboarding helper functions to accept `non_interactive` parameter
  - Functions gracefully handle non-interactive mode with appropriate defaults
  - All 164 tests pass (backward compatible implementation)
- **Verified By**: Test Run #002 - 2025-10-09
- **Verification Results**: ✅ All non-interactive modes working perfectly
  - Explicit path: PASS (no prompts, completed successfully)
  - Environment variable: PASS (auto-detected from CLODPUTER_CLAUDE_BIN)
  - Pure auto-detection: PASS (found Claude via `which`)
  - All flags working: --yes, --no-templates, --no-automation
- **Usage Examples**:
  ```bash
  # Full non-interactive mode
  clodputer init --claude-cli /path/to/claude --yes --no-templates --no-automation

  # With environment variable
  export CLODPUTER_CLAUDE_BIN=/path/to/claude
  clodputer init --yes

  # Pure auto-detection
  clodputer init --yes
  ```

---

## Medium Priority Issues 🟡

### Issue #2: Incorrect Default Claude CLI Path

**Priority**: 🟡 Medium
**Status**: ✅ Verified
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

**Resolution**:
- **Fixed In**: Commit 94a25a5 - 2025-10-09
- **Fix Description**:
  - Confirmed auto-detection logic already exists in `environment.py:claude_cli_path()`
  - Updated `_choose_claude_cli()` to properly utilize auto-detection in priority order:
    1. Explicit CLI flag (`--claude-cli`)
    2. Environment variable (`CLODPUTER_CLAUDE_BIN`)
    3. Stored path from state file
    4. Runtime detection via `which claude`
    5. Common installation paths (`~/.claude/local/claude`, `/opt/homebrew/bin/claude`)
  - Interactive mode now prompts with detected path as default
  - Non-interactive mode uses auto-detection without prompts
- **Verified By**: Test Run #002 - 2025-10-09
- **Verification Results**: ✅ Auto-detection working perfectly
  - Successfully detected: `/Users/ro/.claude/local/claude`
  - Message displayed: "Auto-detected Claude CLI at /Users/ro/.claude/local/claude"
  - Detection worked via `which claude` command
  - No manual path entry required
- **Auto-Detection Order**: Explicit → Env Var → Stored → `which` → Common Paths

---

### Issue #3: Installation Method Unclear for macOS Users

**Priority**: 🟡 Medium
**Status**: ✅ Verified
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

**Resolution**:
- **Fixed In**: Commit 94a25a5 - 2025-10-09
- **Fix Description**:
  - Updated README.md Installation section with clear guidance:
    - Added note that package is currently developer preview (source-only)
    - Reorganized to show "From Source" as current installation method
    - Added "Platform Notes" section highlighting macOS PEP 668 issue
    - Included warning against using `--break-system-packages`
    - Documented future pipx installation method (when published to PyPI)
    - Clarified Linux also has externally managed Python
  - Clear distinction between:
    - Current: Source installation with venv (developer preview)
    - Future: pipx installation (when published to PyPI)
- **Verified By**: Test Run #002 - 2025-10-09
- **Verification Results**: ✅ Documentation is clear and helpful
  - README Installation section reorganized with "From Source (Current Method)" prominent
  - Platform Notes section clearly explains PEP 668 issue
  - Warning against `--break-system-packages` included
  - Users have clear path: clone → venv → pip install -e .
- **User Impact**: Clear installation path reduces confusion and prevents system Python damage

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
- **High Open**: 0
- **Medium Open**: 0
- **Low Open**: 0
- **In Progress**: 0
- **Fixed (Pending Verification)**: 0
- **Verified**: 3 (Issues #1, #2, #3)
- **Test Runs Completed**: 2
  - Test Run #001 - Fresh Install (2025-10-09): 3 issues found
  - Test Run #002 - Onboarding Improvements (2025-10-09): 0 new issues, 3 verified fixed
