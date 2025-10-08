"""Shared pytest fixtures for Clodputer test suite.

This module provides reusable fixtures that eliminate duplication across
test files, particularly for onboarding tests that require mocking state
files, subprocess calls, and directory structures.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pytest


@pytest.fixture
def isolated_state(monkeypatch, tmp_path):
    """Provide an isolated state file for testing environment operations.

    Sets up a temporary state file in tmp_path and monkeypatches both
    environment and onboarding modules to use it. This prevents tests
    from interfering with each other or with real user state.

    Returns:
        Path: The temporary state file path (env.json in tmp_path).

    Example:
        >>> def test_something(isolated_state):
        ...     # State operations will use isolated_state path
        ...     env.update_state({"key": "value"})
        ...     assert isolated_state.exists()
    """
    from clodputer import environment, onboarding

    state_file = tmp_path / "env.json"
    monkeypatch.setattr(environment, "STATE_FILE", state_file)
    monkeypatch.setattr(onboarding, "STATE_FILE", state_file)
    return state_file


@pytest.fixture
def fake_claude_cli(tmp_path):
    """Create a fake Claude CLI executable for testing.

    Returns:
        Path: Path to executable fake Claude CLI that outputs "Claude CLI 1.0".

    Example:
        >>> def test_something(fake_claude_cli, monkeypatch):
        ...     monkeypatch.setattr(shutil, "which", lambda _: str(fake_claude_cli))
        ...     result = subprocess.run([str(fake_claude_cli)], capture_output=True)
        ...     assert "Claude CLI 1.0" in result.stdout.decode()
    """
    claude_path = tmp_path / "bin" / "claude"
    claude_path.parent.mkdir(parents=True, exist_ok=True)
    claude_path.write_text("#!/bin/sh\necho 'Claude CLI 1.0'\n")
    claude_path.chmod(0o755)
    return claude_path


@pytest.fixture
def mock_subprocess_success():
    """Provide a mock subprocess module that returns successful results.

    Returns:
        SimpleNamespace: Mock subprocess with run() that always succeeds.

    Example:
        >>> def test_something(monkeypatch, mock_subprocess_success):
        ...     monkeypatch.setattr(onboarding, "subprocess", mock_subprocess_success)
        ...     # All subprocess.run() calls will succeed
    """
    return SimpleNamespace(
        run=lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="Claude CLI 1.0",
            stderr=""
        )
    )


@pytest.fixture
def mock_subprocess_failure():
    """Provide a mock subprocess module that returns failure results.

    Returns:
        SimpleNamespace: Mock subprocess with run() that always fails.

    Example:
        >>> def test_something(monkeypatch, mock_subprocess_failure):
        ...     monkeypatch.setattr(onboarding, "subprocess", mock_subprocess_failure)
        ...     # All subprocess.run() calls will fail
    """
    return SimpleNamespace(
        run=lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Command failed"
        )
    )


@pytest.fixture
def isolated_home(monkeypatch, tmp_path):
    """Provide an isolated home directory for testing.

    Creates a temporary home directory and sets HOME environment variable,
    along with standard Clodputer directories (TASKS_DIR, QUEUE_DIR, etc.).

    Returns:
        dict: Dictionary with paths: home, queue_dir, tasks_dir, state_file.

    Example:
        >>> def test_something(isolated_home):
        ...     home = isolated_home["home"]
        ...     queue_dir = isolated_home["queue_dir"]
        ...     # Test operations won't touch real home directory
    """
    from clodputer import config, environment, queue, onboarding

    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)

    queue_dir = home / ".clodputer"
    tasks_dir = queue_dir / "tasks"
    state_file = queue_dir / "env.json"
    log_dir = queue_dir / "logs"
    archive_dir = queue_dir / "archive"

    # Set HOME environment variable
    monkeypatch.setenv("HOME", str(home))

    # Monkeypatch all directory paths
    monkeypatch.setattr(config, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(onboarding, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(environment, "STATE_FILE", state_file)
    monkeypatch.setattr(onboarding, "STATE_FILE", state_file)
    monkeypatch.setattr(queue, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(onboarding, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(onboarding, "LOG_DIR", log_dir)
    monkeypatch.setattr(onboarding, "ARCHIVE_DIR", archive_dir)

    return {
        "home": home,
        "queue_dir": queue_dir,
        "tasks_dir": tasks_dir,
        "state_file": state_file,
        "log_dir": log_dir,
        "archive_dir": archive_dir,
    }


@pytest.fixture
def stub_doctor(monkeypatch):
    """Stub out diagnostics gathering for faster tests.

    Monkeypatches gather_diagnostics() to return a successful mock result
    without actually running diagnostic checks.

    Example:
        >>> def test_something(stub_doctor):
        ...     # onboarding.gather_diagnostics() will return mock success
        ...     diagnostics = gather_diagnostics()
        ...     assert diagnostics[0].passed
    """
    from clodputer import onboarding

    monkeypatch.setattr(
        onboarding,
        "gather_diagnostics",
        lambda: [SimpleNamespace(name="Doctor", passed=True, details=[])],
    )


@pytest.fixture
def stub_onboarding_phases(monkeypatch):
    """Stub out all onboarding phases for integration tests.

    Monkeypatches all phase functions (template install, CLAUDE.md update,
    automation, runtime shortcuts, smoke test) to no-ops. Useful for tests
    that need onboarding flow without executing actual phases.

    Example:
        >>> def test_something(stub_onboarding_phases):
        ...     # All onboarding phases will be skipped
        ...     run_onboarding()  # Fast, no user prompts
    """
    from clodputer import onboarding

    monkeypatch.setattr(onboarding, "_offer_template_install", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_claude_md_update", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_automation", lambda *_: [])
    monkeypatch.setattr(onboarding, "_offer_runtime_shortcuts", lambda: None)
    monkeypatch.setattr(onboarding, "_offer_smoke_test", lambda *_: None)


@pytest.fixture
def mock_click_confirm():
    """Factory fixture for mocking click.confirm() with preset responses.

    Returns:
        Callable: Function that creates a mock click.confirm returning given value.

    Example:
        >>> def test_something(monkeypatch, mock_click_confirm):
        ...     # User always confirms
        ...     monkeypatch.setattr("click.confirm", mock_click_confirm(True))
        ...
        ...     # User always rejects
        ...     monkeypatch.setattr("click.confirm", mock_click_confirm(False))
    """
    def _mock_confirm(return_value: bool) -> Callable:
        return lambda *args, **kwargs: return_value

    return _mock_confirm


@pytest.fixture
def mock_click_prompt():
    """Factory fixture for mocking click.prompt() with preset responses.

    Returns:
        Callable: Function that creates a mock click.prompt returning given value.

    Example:
        >>> def test_something(monkeypatch, mock_click_prompt):
        ...     # User enters "option1"
        ...     monkeypatch.setattr("click.prompt", mock_click_prompt("option1"))
    """
    def _mock_prompt(return_value: str) -> Callable:
        return lambda *args, **kwargs: return_value

    return _mock_prompt


@pytest.fixture
def sample_state_data():
    """Provide sample valid state data for testing.

    Returns:
        dict: Valid onboarding state with all required fields.

    Example:
        >>> def test_something(sample_state_data):
        ...     state_data = sample_state_data.copy()
        ...     state_data["onboarding_runs"] = 5
        ...     _persist_state(state_data)
    """
    return {
        "schema_version": 1,
        "claude_cli": "/usr/local/bin/claude",
        "onboarding_runs": 1,
        "onboarding_last_run": "2025-01-15T10:00:00",
        "onboarding_completed_at": "2025-01-15T10:05:00",
    }


@pytest.fixture
def write_state(isolated_state):
    """Provide a helper function to write state to isolated state file.

    Returns:
        Callable: Function that writes dict to state file as JSON.

    Example:
        >>> def test_something(write_state):
        ...     write_state({"claude_cli": "/path/to/claude"})
        ...     # State file now contains the data
    """
    def _write(data: dict) -> None:
        isolated_state.write_text(json.dumps(data, indent=2))

    return _write
