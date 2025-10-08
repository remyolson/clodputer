# Phase 1: Critical Fixes - Implementation Checklist

**Target Timeline**: 1-2 days
**Priority**: Must complete before user testing
**Status**: Ready to start

---

## Overview

This document provides a concrete implementation plan for the 5 critical fixes identified in the pre-launch improvements review. Each fix includes specific code changes, test requirements, and verification steps.

---

## Fix 1: Add Subprocess Timeouts ✅

**Priority**: 🔴 Critical
**Estimated Time**: 30 minutes
**Risk**: Low
**Status**: ✅ Complete

### Problem
`_verify_claude_cli()` subprocess calls lack timeout, users could hang indefinitely if Claude CLI freezes.

### Implementation

**File**: `src/clodputer/onboarding.py:639-649`

**Current Code**:
```python
def _verify_claude_cli(path: str) -> None:
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(f"Claude CLI not executable at {path}") from exc
```

**Updated Code**:
```python
def _verify_claude_cli(path: str) -> None:
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,  # Add 10 second timeout
        )
    except FileNotFoundError as exc:
        raise click.ClickException(f"Claude CLI not executable at {path}") from exc
    except subprocess.TimeoutExpired:
        click.echo("  ⚠️ Claude CLI --version timed out after 10 seconds.")
        click.echo("     This may indicate an issue with the Claude installation.")
```

### Testing

Add test case:
```python
def test_verify_claude_cli_timeout(monkeypatch):
    from clodputer import onboarding
    import subprocess

    def timeout_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=10)

    monkeypatch.setattr(onboarding.subprocess, "run", timeout_run)
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda msg: outputs.append(msg))

    onboarding._verify_claude_cli("/path/to/claude")

    assert any("timed out" in msg for msg in outputs)
```

**Location**: `tests/test_onboarding.py`

### Verification
- [ ] Run new test: `pytest tests/test_onboarding.py::test_verify_claude_cli_timeout -v`
- [ ] Run full test suite: `pytest`
- [ ] Manual test with slow binary (create test script that sleeps)

---

## Fix 2: State File Corruption Handling ✅

**Priority**: 🔴 Critical
**Estimated Time**: 1-2 hours
**Risk**: Medium (state management is critical)
**Status**: ✅ Complete

### Problem
Corrupted `env.json` causes hard crash with JSONDecodeError, no recovery path for users.

### Implementation

**File**: `src/clodputer/environment.py:64-75`

**Current Code**:
```python
def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
```

**Updated Code**:
```python
def _load_state() -> dict:
    """Load state from file with corruption recovery."""
    if not STATE_FILE.exists():
        return {}

    try:
        content = STATE_FILE.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as exc:
        # Attempt recovery from backup
        backup_file = STATE_FILE.parent / f"{STATE_FILE.name}.backup"
        if backup_file.exists():
            try:
                content = backup_file.read_text(encoding="utf-8")
                data = json.loads(content)
                # Restore from backup
                _persist_state(data)
                return data
            except (json.JSONDecodeError, OSError):
                pass

        # No recovery possible, log and return empty state
        import sys
        print(f"Warning: State file corrupted at {STATE_FILE}", file=sys.stderr)
        print(f"  Error: {exc}", file=sys.stderr)
        print(f"  Starting with clean state. Run 'clodputer init' to reconfigure.", file=sys.stderr)

        # Archive corrupted file for debugging
        corrupted_file = STATE_FILE.parent / f"{STATE_FILE.name}.corrupted"
        try:
            STATE_FILE.rename(corrupted_file)
            print(f"  Corrupted file saved to: {corrupted_file}", file=sys.stderr)
        except OSError:
            pass

        return {}
    except OSError as exc:
        import sys
        print(f"Warning: Cannot read state file: {exc}", file=sys.stderr)
        return {}


def _persist_state(data: dict) -> None:
    """Persist state with backup."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Create backup of existing state before overwriting
    if STATE_FILE.exists():
        backup_file = STATE_FILE.parent / f"{STATE_FILE.name}.backup"
        try:
            import shutil
            shutil.copy2(STATE_FILE, backup_file)
        except OSError:
            pass  # Non-fatal if backup fails

    # Write new state atomically
    temp_file = STATE_FILE.parent / f"{STATE_FILE.name}.tmp"
    temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp_file.replace(STATE_FILE)
```

### Testing

Add test cases:
```python
def test_environment_corrupted_state_recovery(monkeypatch, tmp_path):
    """Test recovery from corrupted state file using backup."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    backup_file = tmp_path / "env.json.backup"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Create valid backup
    backup_file.write_text('{"key": "value"}')

    # Create corrupted main file
    state_file.write_text("not valid json{")

    # Should recover from backup
    state = env._load_state()
    assert state == {"key": "value"}
    assert state_file.exists()  # Should be restored


def test_environment_corrupted_state_no_backup(monkeypatch, tmp_path, capsys):
    """Test handling corrupted state with no backup available."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Create corrupted file
    state_file.write_text("not valid json{")

    # Should return empty state and archive corrupted file
    state = env._load_state()
    assert state == {}

    # Should have archived corrupted file
    corrupted_file = tmp_path / "env.json.corrupted"
    assert corrupted_file.exists()
    assert not state_file.exists()

    # Should print warning
    captured = capsys.readouterr()
    assert "corrupted" in captured.err.lower()


def test_environment_persist_creates_backup(monkeypatch, tmp_path):
    """Test that persist creates backup before overwriting."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    backup_file = tmp_path / "env.json.backup"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Create initial state
    env._persist_state({"version": 1})
    assert state_file.exists()
    assert not backup_file.exists()

    # Update state - should create backup
    env._persist_state({"version": 2})
    assert state_file.exists()
    assert backup_file.exists()

    # Backup should have old version
    import json
    backup_data = json.loads(backup_file.read_text())
    assert backup_data["version"] == 1

    # Main file should have new version
    main_data = json.loads(state_file.read_text())
    assert main_data["version"] == 2
```

**Location**: `tests/test_onboarding.py` (or create `tests/test_environment.py`)

### Verification
- [ ] Run new tests: `pytest tests/test_onboarding.py -k corrupted -v`
- [ ] Manual test: corrupt `~/.clodputer/env.json` and run `clodputer status`
- [ ] Verify backup is created on state updates
- [ ] Check error message clarity

---

## Fix 3: State Migration Infrastructure ✅

**Priority**: 🟡 High
**Estimated Time**: 2-3 hours
**Risk**: Medium
**Status**: ✅ Complete

### Problem
No version tracking in env.json, future state schema changes will break existing installs.

### Implementation

**File**: `src/clodputer/environment.py`

**Add Constants**:
```python
STATE_SCHEMA_VERSION = 1  # Current schema version

# Migration functions registry
_MIGRATIONS = {}


def migration(from_version: int, to_version: int):
    """Decorator to register a state migration."""
    def decorator(func):
        _MIGRATIONS[(from_version, to_version)] = func
        return func
    return decorator
```

**Add Migration Logic**:
```python
def _migrate_state(data: dict) -> dict:
    """Migrate state to current schema version."""
    current_version = data.get("schema_version", 0)

    if current_version == STATE_SCHEMA_VERSION:
        return data  # Already current

    if current_version > STATE_SCHEMA_VERSION:
        import sys
        print(
            f"Warning: State file schema version {current_version} is newer than "
            f"supported version {STATE_SCHEMA_VERSION}. Some features may not work.",
            file=sys.stderr
        )
        return data

    # Apply migrations in sequence
    migrated_data = data.copy()
    version = current_version

    while version < STATE_SCHEMA_VERSION:
        next_version = version + 1
        migration_func = _MIGRATIONS.get((version, next_version))

        if migration_func is None:
            raise RuntimeError(
                f"No migration defined from version {version} to {next_version}"
            )

        migrated_data = migration_func(migrated_data)
        migrated_data["schema_version"] = next_version
        version = next_version

    return migrated_data


# Example migration (currently no-op, but demonstrates pattern)
@migration(from_version=0, to_version=1)
def migrate_v0_to_v1(data: dict) -> dict:
    """Add schema_version field to unversioned state."""
    # v0 (no version field) -> v1 (adds schema_version)
    # No data transformation needed, just adds version tracking
    return data


def _load_state() -> dict:
    """Load state from file with corruption recovery and migration."""
    # ... existing corruption handling code ...

    # After successful load, migrate if needed
    try:
        data = json.loads(content)
        migrated = _migrate_state(data)

        # If migration occurred, persist immediately
        if migrated.get("schema_version") != data.get("schema_version"):
            _persist_state(migrated)

        return migrated
    except json.JSONDecodeError as exc:
        # ... existing error handling ...


def _persist_state(data: dict) -> None:
    """Persist state with backup and version tracking."""
    # Ensure schema_version is set
    if "schema_version" not in data:
        data["schema_version"] = STATE_SCHEMA_VERSION

    # ... existing backup and write code ...
```

### Testing

Add test cases:
```python
def test_state_migration_v0_to_v1(monkeypatch, tmp_path):
    """Test migration from unversioned to versioned state."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Create v0 state (no schema_version)
    v0_state = {"claude_cli": "/usr/bin/claude", "onboarding_runs": 1}
    state_file.write_text(json.dumps(v0_state))

    # Load should trigger migration
    state = env._load_state()

    # Should have schema_version added
    assert state["schema_version"] == 1
    assert state["claude_cli"] == "/usr/bin/claude"
    assert state["onboarding_runs"] == 1

    # Should have persisted migrated state
    persisted = json.loads(state_file.read_text())
    assert persisted["schema_version"] == 1


def test_state_migration_already_current(monkeypatch, tmp_path):
    """Test that current version state is not migrated."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Create current version state
    current_state = {"schema_version": 1, "key": "value"}
    state_file.write_text(json.dumps(current_state))

    # Load should not trigger migration
    state = env._load_state()
    assert state == current_state


def test_state_persist_adds_version(monkeypatch, tmp_path):
    """Test that persisting state adds schema_version if missing."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Persist state without version
    env._persist_state({"key": "value"})

    # Should have version added
    persisted = json.loads(state_file.read_text())
    assert persisted["schema_version"] == 1
    assert persisted["key"] == "value"
```

**Location**: `tests/test_environment.py` (create this file)

### Verification
- [ ] Run new tests: `pytest tests/test_environment.py -v`
- [ ] Test migration from v0: manually create unversioned env.json
- [ ] Verify backward compatibility: old installs migrate smoothly
- [ ] Document migration pattern in code comments

---

## Fix 4: Improve Error Messages ✅

**Priority**: 🟡 High
**Estimated Time**: 1 hour
**Risk**: Low
**Status**: ✅ Complete

### Problem
Error messages lack actionable guidance, just say "failed" without next steps.

### Implementation

**File**: `src/clodputer/onboarding.py` (multiple locations)

**Pattern**: For each error, add context and next steps.

**Examples**:

1. **Claude CLI not found** (line ~185):
```python
# Before
raise click.ClickException("Claude CLI not found in PATH or common locations.")

# After
raise click.ClickException(
    "Claude CLI not found in PATH or common install locations.\n"
    "  Install from: https://docs.claude.com/cli/installation\n"
    "  Or specify path manually when prompted."
)
```

2. **Template export failure** (line ~229):
```python
# Before
click.echo(f"  ❌ Failed to export template: {exc}")

# After
click.echo(f"  ❌ Failed to export template: {exc}")
click.echo(f"     Try: clodputer template export {template_name}")
click.echo(f"     Or check permissions on ~/.clodputer/tasks/")
```

3. **Cron installation failure** (line ~340):
```python
# Before
click.echo(f"  ❌ Cron installation failed: {exc}")

# After
click.echo(f"  ❌ Cron installation failed: {exc}")
click.echo(f"     macOS users: grant Full Disk Access to Terminal in System Preferences")
click.echo(f"     Or install manually with: clodputer install")
```

4. **Smoke test failure** (line ~490):
```python
# Before
click.echo(f"  ⚠️ Task execution failed: {error}")

# After
click.echo(f"  ⚠️ Task execution failed: {error}")
click.echo(f"     Check logs: clodputer logs --tail 20")
click.echo(f"     Verify Claude CLI: {claude_cli_path(None)} --version")
click.echo(f"     Run diagnostics: clodputer doctor")
```

### Testing

Update existing tests to check for guidance in error messages:
```python
def test_error_messages_include_next_steps(monkeypatch):
    """Verify error messages include actionable guidance."""
    from clodputer import onboarding

    # Test Claude CLI not found error
    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: None)
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: False)

    # Should include installation URL
    with pytest.raises(click.ClickException) as exc_info:
        onboarding._choose_claude_cli()

    assert "https://docs.claude.com" in str(exc_info.value)
    assert "install" in str(exc_info.value).lower()
```

### Verification
- [ ] Manually trigger each error condition
- [ ] Verify all error messages include next steps
- [ ] Check links are valid
- [ ] Update tests to validate error content

---

## Fix 5: Add Integration Test ⬜

**Priority**: 🟡 High
**Estimated Time**: 2-3 hours
**Risk**: Medium
**Status**: Not started

### Problem
Unit tests mock heavily, never run real end-to-end flow. Integration bugs could slip through.

### Implementation

**File**: `tests/test_onboarding_integration.py` (new file)

```python
"""Integration tests for onboarding flow.

These tests run with minimal mocking to catch integration issues.
"""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from clodputer.cli import cli


@pytest.fixture
def temp_home(monkeypatch, tmp_path):
    """Create temporary home directory for integration tests."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    # Create minimal Claude CLI mock
    fake_cli = home / ".local" / "bin" / "claude"
    fake_cli.parent.mkdir(parents=True)
    fake_cli.write_text("#!/bin/bash\necho 'Claude CLI 1.0'")
    fake_cli.chmod(0o755)

    return home


def test_full_onboarding_flow_minimal(temp_home):
    """Test complete onboarding flow with minimal configuration."""
    runner = CliRunner()

    # Run init with all declines (minimal setup)
    result = runner.invoke(
        cli,
        ["init"],
        input="\n".join([
            "",  # Accept detected Claude CLI
            "n",  # Decline template import
            "n",  # Decline CLAUDE.md update
            "n",  # Decline cron setup
            "n",  # Decline watcher setup
            "n",  # Decline smoke test
            "n",  # Decline menu bar
            "n",  # Decline dashboard
        ])
    )

    assert result.exit_code == 0, f"Onboarding failed: {result.output}"

    # Verify state was created
    state_file = temp_home / ".clodputer" / "env.json"
    assert state_file.exists()

    state = json.loads(state_file.read_text())
    assert "claude_cli" in state
    assert "onboarding_runs" in state
    assert state["onboarding_runs"] == 1

    # Verify directories were created
    assert (temp_home / ".clodputer" / "tasks").exists()
    assert (temp_home / ".clodputer" / "logs").exists()
    assert (temp_home / ".clodputer" / "archive").exists()

    # Verify onboarding log was created
    assert (temp_home / ".clodputer" / "onboarding.log").exists()


def test_full_onboarding_flow_with_template(temp_home):
    """Test onboarding flow with template import."""
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["init"],
        input="\n".join([
            "",  # Accept detected Claude CLI
            "y",  # Accept template import
            "\n",  # Accept first template
            "",  # Keep default destination
            "n",  # Decline CLAUDE.md update
            "n",  # Decline automation
        ])
    )

    assert result.exit_code == 0, f"Onboarding failed: {result.output}"

    # Verify template was copied
    tasks_dir = temp_home / ".clodputer" / "tasks"
    yaml_files = list(tasks_dir.glob("*.yaml"))
    assert len(yaml_files) > 0, "No template files found"


def test_onboarding_idempotency(temp_home):
    """Test that running init twice doesn't break."""
    runner = CliRunner()

    # Run init first time
    result1 = runner.invoke(cli, ["init"], input="\nn\nn\nn\n")
    assert result1.exit_code == 0

    state_file = temp_home / ".clodputer" / "env.json"
    state1 = json.loads(state_file.read_text())

    # Run init second time
    result2 = runner.invoke(cli, ["init"], input="\nn\nn\nn\n")
    assert result2.exit_code == 0

    state2 = json.loads(state_file.read_text())

    # Should increment run count
    assert state2["onboarding_runs"] == 2
    assert state1["claude_cli"] == state2["claude_cli"]


def test_onboarding_reset(temp_home):
    """Test that --reset clears state and starts fresh."""
    runner = CliRunner()

    # Run init first time
    runner.invoke(cli, ["init"], input="\nn\nn\nn\n")

    state_file = temp_home / ".clodputer" / "env.json"
    state1 = json.loads(state_file.read_text())

    # Run init with reset
    result = runner.invoke(cli, ["init", "--reset"], input="\nn\nn\nn\n")
    assert result.exit_code == 0

    state2 = json.loads(state_file.read_text())

    # Should reset run count
    assert state2["onboarding_runs"] == 1
```

### Verification
- [ ] Run integration tests: `pytest tests/test_onboarding_integration.py -v`
- [ ] Verify tests work in clean environment
- [ ] Check tests catch real integration bugs
- [ ] Add to CI pipeline

---

## Implementation Order

1. **Fix 1: Subprocess Timeouts** (30 min) - Quick win, low risk
2. **Fix 4: Error Messages** (1 hour) - Low risk, improves UX immediately
3. **Fix 2: State Corruption** (2 hours) - Critical for reliability
4. **Fix 3: State Migration** (3 hours) - Builds on Fix 2
5. **Fix 5: Integration Test** (3 hours) - Validates all fixes

**Total Estimated Time**: 9-10 hours (1-2 days)

---

## Testing Strategy

### Unit Tests
- Run after each fix: `pytest tests/test_onboarding.py -v`
- Verify coverage: `pytest --cov=src/clodputer/onboarding --cov=src/clodputer/environment`

### Integration Tests
- Run after Fix 5: `pytest tests/test_onboarding_integration.py -v`
- Run full suite: `pytest`

### Manual Testing
- [ ] Clean install: rm -rf ~/.clodputer && clodputer init
- [ ] Corrupt state: echo "bad json" > ~/.clodputer/env.json && clodputer status
- [ ] Timeout: patch Claude CLI to sleep 60 seconds
- [ ] Idempotency: run init 3 times
- [ ] Reset: clodputer init --reset

---

## Success Criteria

Before marking Phase 1 complete:

- [ ] All 5 fixes implemented and tested
- [ ] Test coverage ≥ 87% (current level)
- [ ] All tests passing: 113+ tests
- [ ] Manual testing complete
- [ ] Code reviewed (self or peer)
- [ ] Documentation updated (if needed)
- [ ] Git commit with clear message

---

## Rollback Plan

If issues arise:
1. Each fix is independent - can revert individually
2. State migration is backward compatible - old code reads new state
3. Integration tests can be disabled if blocking
4. All changes behind feature flag if needed

---

## Next Steps After Phase 1

Once Phase 1 is complete:
1. Deploy to staging environment
2. Conduct internal user testing
3. Gather feedback
4. Prioritize Phase 2 items based on findings
5. Update pre-launch improvements doc with lessons learned
