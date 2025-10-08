"""Integration tests for the full onboarding flow.

These tests run the actual onboarding flow end-to-end with minimal mocking,
using a real temporary directory structure to verify all components work together.
"""

import json
from pathlib import Path


def test_full_directory_and_state_setup(monkeypatch, tmp_path):
    """Integration test: Directory creation and state persistence work together.

    Verifies that _ensure_directories() and state management functions
    work correctly when called in sequence.
    """
    from clodputer import config, environment, onboarding, queue

    # Setup
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    # Patch module paths
    queue_dir = home / ".clodputer"
    tasks_dir = queue_dir / "tasks"
    log_dir = queue_dir / "logs"
    archive_dir = queue_dir / "archive"
    state_file = queue_dir / "env.json"

    monkeypatch.setattr(queue, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(config, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(environment, "STATE_FILE", state_file)
    monkeypatch.setattr(onboarding, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(onboarding, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(onboarding, "LOG_DIR", log_dir)
    monkeypatch.setattr(onboarding, "ARCHIVE_DIR", archive_dir)

    # Mock directory creation functions to use our test paths
    # NOTE: Must patch in onboarding module since it imports these functions directly
    def mock_ensure_queue_dir():
        queue_dir.mkdir(parents=True, exist_ok=True)

    def mock_ensure_tasks_dir():
        tasks_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(onboarding, "ensure_queue_dir", mock_ensure_queue_dir)
    monkeypatch.setattr(onboarding, "ensure_tasks_dir", mock_ensure_tasks_dir)

    # Mock click.echo to avoid output
    monkeypatch.setattr(onboarding.click, "echo", lambda *args, **kwargs: None)

    # Step 1: Ensure directories
    onboarding._ensure_directories()

    # Verify directories created
    assert queue_dir.exists()
    assert tasks_dir.exists()
    assert log_dir.exists()
    assert archive_dir.exists()

    # Step 2: Store Claude CLI path
    claude_path = "/usr/local/bin/claude"
    environment.store_claude_cli_path(claude_path)

    # Verify state file created
    assert state_file.exists()
    state_data = json.loads(state_file.read_text())
    assert state_data["claude_cli"] == claude_path
    assert state_data["schema_version"] == 1

    # Step 3: Update state with more data
    environment.update_state({"onboarding_completed_at": "2025-01-15"})

    # Verify state updated
    updated_state = environment.onboarding_state()
    assert updated_state["claude_cli"] == claude_path
    assert updated_state["onboarding_completed_at"] == "2025-01-15"
    assert updated_state["schema_version"] == 1

    # Step 4: Verify backup file created
    backup_file = state_file.parent / f"{state_file.name}.backup"
    assert backup_file.exists()


def test_onboarding_with_reset(monkeypatch, tmp_path):
    """Integration test: Onboarding with reset clears previous state.

    Verifies that running onboarding with reset=True properly clears
    existing state and creates fresh configuration.
    """
    from clodputer import environment, onboarding

    # Setup
    queue_dir = tmp_path / ".clodputer"
    state_file = queue_dir / "env.json"
    log_path = queue_dir / "onboarding.log"

    # Patch STATE_FILE in both modules
    monkeypatch.setattr(environment, "STATE_FILE", state_file)
    monkeypatch.setattr("clodputer.onboarding.STATE_FILE", state_file)
    monkeypatch.setattr(onboarding, "_onboarding_log_path", lambda: log_path)

    # Create existing state and log
    queue_dir.mkdir(parents=True, exist_ok=True)
    state_file.write_text('{"old_key": "old_value", "schema_version": 1}')
    log_path.write_text("[2025-01-01] Old log entry")

    assert state_file.exists()
    assert log_path.exists()

    # Run reset
    result = onboarding._reset_onboarding_state()

    # Verify state was cleared
    assert not state_file.exists()
    assert not log_path.exists()
    assert len(result) == 2  # Should report 2 cleared paths


def test_onboarding_detects_and_uses_claude_cli(monkeypatch, tmp_path):
    """Integration test: Onboarding detects Claude CLI in PATH.

    Verifies that the onboarding can detect and configure Claude CLI
    when it's available in the system PATH.
    """
    from clodputer import environment
    import shutil as shutil_module

    home = tmp_path / "home"
    home.mkdir()
    claude_path = tmp_path / "usr" / "local" / "bin" / "claude"
    claude_path.parent.mkdir(parents=True)
    claude_path.write_text("#!/bin/sh\necho 'Claude'\n")
    claude_path.chmod(0o755)

    # Clear any existing state
    state_file = home / ".clodputer" / "env.json"
    monkeypatch.setattr(environment, "STATE_FILE", state_file)

    # Mock shutil.which to return our test path
    def mock_which(name):
        if name == "claude":
            return str(claude_path)
        return None

    monkeypatch.setattr(shutil_module, "which", mock_which)

    # Test detection
    detected = environment.claude_cli_path(None)
    assert detected == str(claude_path)


def test_onboarding_state_persistence_across_operations(monkeypatch, tmp_path):
    """Integration test: State persists correctly across multiple operations.

    Verifies that state updates are properly persisted and can be loaded
    back correctly, including schema version tracking.
    """
    from clodputer import environment

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(environment, "STATE_FILE", state_file)

    # First operation: Store Claude CLI path
    environment.store_claude_cli_path("/path/to/claude")

    # Verify immediate state
    state1 = environment.onboarding_state()
    assert state1["claude_cli"] == "/path/to/claude"
    assert state1["schema_version"] == 1

    # Second operation: Add more state
    environment.update_state({"onboarding_completed_at": "2025-01-15"})

    # Verify combined state
    state2 = environment.onboarding_state()
    assert state2["claude_cli"] == "/path/to/claude"
    assert state2["onboarding_completed_at"] == "2025-01-15"
    assert state2["schema_version"] == 1

    # Third operation: Load from disk (fresh read)
    state3 = environment._load_state()
    assert state3["claude_cli"] == "/path/to/claude"
    assert state3["onboarding_completed_at"] == "2025-01-15"
    assert state3["schema_version"] == 1

    # Verify backup was created
    backup_file = state_file.parent / f"{state_file.name}.backup"
    assert backup_file.exists()
