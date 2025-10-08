"""Tests for environment and state management functionality."""

import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner


def _stub_doctor(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(
        onboarding,
        "gather_diagnostics",
        lambda: [SimpleNamespace(name="Doctor", passed=True, details=[])],
    )


def test_environment_store_and_resolve(monkeypatch, tmp_path):
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    env.store_claude_cli_path("/custom/claude")

    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["claude_cli"] == "/custom/claude"
    assert env.claude_cli_path(None) == "/custom/claude"


def test_environment_fallback_detection(monkeypatch, tmp_path):
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)
    fake_cli = tmp_path / "claude"
    fake_cli.write_text("#!/bin/sh\n")
    fake_cli.chmod(0o755)

    monkeypatch.setattr(env.shutil, "which", lambda _: str(fake_cli))
    assert env.claude_cli_path(None) == str(fake_cli)

    monkeypatch.setattr(env.shutil, "which", lambda _: None)
    monkeypatch.setattr(env.Path, "home", lambda: tmp_path)
    default_cli = tmp_path / ".claude" / "local" / "claude"
    default_cli.parent.mkdir(parents=True, exist_ok=True)
    default_cli.write_text("#!/bin/sh\n")
    default_cli.chmod(0o755)
    assert env.claude_cli_path(None) == str(default_cli)


def test_cli_init_creates_state(monkeypatch, tmp_path):
    from clodputer import config, environment, queue, onboarding
    from clodputer.cli import cli

    home = tmp_path / "home"
    claude_path = tmp_path / "bin" / "claude"
    claude_path.parent.mkdir(parents=True)
    claude_path.write_text("#!/bin/sh\necho 'Claude CLI 1.0'\n")
    claude_path.chmod(0o755)

    queue_dir = home / ".clodputer"
    tasks_dir = queue_dir / "tasks"
    state_file = queue_dir / "env.json"

    monkeypatch.setenv("HOME", str(home))

    monkeypatch.setattr(config, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(onboarding, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(environment, "STATE_FILE", state_file)
    monkeypatch.setattr(onboarding, "STATE_FILE", state_file)
    monkeypatch.setattr(queue, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(onboarding, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(onboarding, "LOG_DIR", queue_dir / "logs")
    monkeypatch.setattr(onboarding, "ARCHIVE_DIR", queue_dir / "archive")
    _stub_doctor(monkeypatch)

    _stub_doctor(monkeypatch)
    monkeypatch.setattr(
        onboarding, "ensure_queue_dir", lambda: queue_dir.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(
        onboarding, "ensure_tasks_dir", lambda: tasks_dir.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(onboarding, "_offer_template_install", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_claude_md_update", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_automation", lambda *_: [])
    monkeypatch.setattr(onboarding, "_offer_runtime_shortcuts", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_smoke_test", lambda *_: None)
    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: str(claude_path))
    monkeypatch.setattr(
        onboarding,
        "subprocess",
        SimpleNamespace(
            run=lambda *_, **__: SimpleNamespace(returncode=0, stdout="Claude CLI 1.0")
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input="\n")

    assert result.exit_code == 0, result.output
    data = json.loads(state_file.read_text())
    assert data["claude_cli"] == str(claude_path)
    assert data.get("onboarding_runs") == 1
    assert "onboarding_last_run" in data
    assert tasks_dir.exists()
    assert (queue_dir / "onboarding.log").exists()


def test_cli_init_manual_path(monkeypatch, tmp_path):
    from clodputer import config, environment, queue, onboarding
    from clodputer.cli import cli

    home = tmp_path / "home"
    claude_path = tmp_path / "bin" / "claude"
    claude_path.parent.mkdir(parents=True)
    claude_path.write_text("#!/bin/sh\n")
    claude_path.chmod(0o755)

    queue_dir = home / ".clodputer"
    tasks_dir = queue_dir / "tasks"
    state_file = queue_dir / "env.json"

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(config, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(onboarding, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(environment, "STATE_FILE", state_file)
    monkeypatch.setattr(onboarding, "STATE_FILE", state_file)
    monkeypatch.setattr(queue, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(onboarding, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(onboarding, "LOG_DIR", queue_dir / "logs")
    monkeypatch.setattr(onboarding, "ARCHIVE_DIR", queue_dir / "archive")
    _stub_doctor(monkeypatch)
    monkeypatch.setattr(
        onboarding, "ensure_queue_dir", lambda: queue_dir.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(
        onboarding, "ensure_tasks_dir", lambda: tasks_dir.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(onboarding, "_offer_template_install", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_claude_md_update", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_automation", lambda *_: [])
    monkeypatch.setattr(onboarding, "_offer_runtime_shortcuts", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_smoke_test", lambda *_: None)

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: None)
    monkeypatch.setattr(
        onboarding,
        "subprocess",
        SimpleNamespace(
            run=lambda *_, **__: SimpleNamespace(returncode=0, stdout="Claude CLI 1.0")
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input=f"{claude_path}\n")

    assert result.exit_code == 0, result.output
    data = json.loads(state_file.read_text())
    assert data["claude_cli"] == str(claude_path)
    assert data.get("onboarding_runs") == 1
    assert "onboarding_last_run" in data


def test_cli_init_reset_clears_state(monkeypatch, tmp_path):
    from clodputer import config, environment, queue, onboarding
    from clodputer.cli import cli

    home = tmp_path / "home"
    claude_path = tmp_path / "bin" / "claude"
    claude_path.parent.mkdir(parents=True)
    claude_path.write_text("#!/bin/sh\necho 'Claude CLI 1.0'\n")
    claude_path.chmod(0o755)

    queue_dir = home / ".clodputer"
    tasks_dir = queue_dir / "tasks"
    state_file = queue_dir / "env.json"
    log_file = queue_dir / "onboarding.log"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"stale": True}), encoding="utf-8")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("old log\n", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))

    monkeypatch.setattr(config, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(onboarding, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(environment, "STATE_FILE", state_file)
    monkeypatch.setattr(onboarding, "STATE_FILE", state_file)
    monkeypatch.setattr(queue, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(onboarding, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(onboarding, "LOG_DIR", queue_dir / "logs")
    monkeypatch.setattr(onboarding, "ARCHIVE_DIR", queue_dir / "archive")

    _stub_doctor(monkeypatch)
    monkeypatch.setattr(
        onboarding, "ensure_queue_dir", lambda: queue_dir.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(
        onboarding, "ensure_tasks_dir", lambda: tasks_dir.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(onboarding, "_offer_template_install", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_claude_md_update", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_automation", lambda *_: [])
    monkeypatch.setattr(onboarding, "_offer_runtime_shortcuts", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_smoke_test", lambda *_: None)

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: str(claude_path))
    monkeypatch.setattr(
        onboarding,
        "subprocess",
        SimpleNamespace(
            run=lambda *_, **__: SimpleNamespace(returncode=0, stdout="Claude CLI 1.0")
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--reset"], input="\n")

    assert result.exit_code == 0, result.output
    data = json.loads(state_file.read_text())
    assert "stale" not in data
    assert data.get("onboarding_runs") == 1
    assert "onboarding_last_run" in data
    assert "old log" not in log_file.read_text()


def test_environment_onboarding_state(monkeypatch, tmp_path):
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    env.update_state({"onboarding_runs": 3, "some_key": "value"})

    state = env.onboarding_state()
    assert state["onboarding_runs"] == 3
    assert state["some_key"] == "value"


def test_environment_reset_state(monkeypatch, tmp_path):
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    env.update_state({"key": "value"})
    assert state_file.exists()

    env.reset_state()
    assert not state_file.exists()


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
    import json

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
    backup_data = json.loads(backup_file.read_text())
    assert backup_data["version"] == 1

    # Main file should have new version
    main_data = json.loads(state_file.read_text())
    assert main_data["version"] == 2


def test_state_migration_v0_to_v1(monkeypatch, tmp_path):
    """Test migration from unversioned to versioned state."""
    import json

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
    import json

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
    import json

    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Persist state without version
    env._persist_state({"key": "value"})

    # Should have version added
    persisted = json.loads(state_file.read_text())
    assert persisted["schema_version"] == 1
    assert persisted["key"] == "value"


def test_state_migration_newer_version_warning(monkeypatch, tmp_path, capsys):
    """Test warning when state has newer schema version."""
    import json

    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Create state with future version
    future_state = {"schema_version": 999, "key": "value"}
    state_file.write_text(json.dumps(future_state))

    # Load should warn but still return data
    state = env._load_state()
    assert state["schema_version"] == 999
    assert state["key"] == "value"

    # Should have printed warning
    captured = capsys.readouterr()
    assert "newer than supported" in captured.err.lower()


def test_environment_persist_handles_disk_full(monkeypatch, tmp_path):
    """Test that state persistence handles disk full errors gracefully."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Mock write_text to raise OSError (disk full)
    def mock_write_text(self, *args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    # Should raise OSError when trying to persist
    try:
        env._persist_state({"test": "data"})
        assert False, "Should have raised OSError"
    except OSError as exc:
        assert "No space left on device" in str(exc)


def test_environment_load_handles_permission_error(monkeypatch, tmp_path, capsys):
    """Test that state loading handles permission errors gracefully."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    state_file.write_text('{"key": "value"}')
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Mock read_text to raise permission error
    def mock_read_text(self, *args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    # Should return empty dict and print warning
    result = env._load_state()
    assert result == {}

    captured = capsys.readouterr()
    assert "Cannot read state file" in captured.err


def test_state_validation_rejects_empty_claude_cli(monkeypatch, tmp_path):
    """Test that state validation rejects empty claude_cli path."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Should raise ValueError for empty string
    try:
        env._persist_state({"claude_cli": ""})
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "Invalid state data" in str(exc)


def test_state_validation_rejects_negative_runs(monkeypatch, tmp_path):
    """Test that state validation rejects negative onboarding_runs."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Should raise ValueError for negative runs
    try:
        env._persist_state({"onboarding_runs": -1})
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "Invalid state data" in str(exc)


def test_state_validation_allows_valid_state(monkeypatch, tmp_path):
    """Test that state validation allows valid state."""
    from clodputer import environment as env

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(env, "STATE_FILE", state_file)

    # Should succeed with valid data
    env._persist_state({"claude_cli": "/usr/bin/claude", "onboarding_runs": 1})

    # Verify it was written
    assert state_file.exists()
    data = env._load_state()
    assert data["claude_cli"] == "/usr/bin/claude"
    assert data["onboarding_runs"] == 1
