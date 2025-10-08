"""Tests for onboarding utility functions, validators, and logger."""

from pathlib import Path
from types import SimpleNamespace


def test_render_doctor_summary_reports_failures(monkeypatch):
    from clodputer import onboarding

    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._render_doctor_summary(
        [
            SimpleNamespace(name="pass", passed=True, details=[]),
            SimpleNamespace(name="fail", passed=False, details=["issue"]),
        ]
    )

    assert any("Issues detected" in message for message in outputs)
    assert any("❌ fail" in message for message in outputs)
    assert any("issue" in message for message in outputs)


def test_format_seconds():
    from clodputer import onboarding

    assert onboarding._format_seconds(0.5) == "0s"
    assert onboarding._format_seconds(1.0) == "1s"
    assert onboarding._format_seconds(59.9) == "59s"
    assert onboarding._format_seconds(60.0) == "1m00s"
    assert onboarding._format_seconds(61.5) == "1m01s"
    assert onboarding._format_seconds(125.0) == "2m05s"


def test_onboarding_logger_rotates_large_logs(monkeypatch, tmp_path):
    """Test that OnboardingLogger rotates logs when they exceed size limit."""
    from clodputer import onboarding

    # Create a large log file (> 10MB)
    log_path = tmp_path / "onboarding.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Write > 10MB of data
    large_content = "x" * (11 * 1024 * 1024)  # 11 MB
    log_path.write_text(large_content, encoding="utf-8")

    # Mock _onboarding_log_path to return our test path
    monkeypatch.setattr(onboarding, "_onboarding_log_path", lambda: log_path)

    # Use the logger - should trigger rotation
    with onboarding.OnboardingLogger():
        pass

    # Original log should be rotated to .1
    backup_path = tmp_path / "onboarding.log.1"
    assert backup_path.exists()
    assert backup_path.stat().st_size > 10 * 1024 * 1024

    # New log should exist (empty or with minimal content)
    assert log_path.exists()
    assert log_path.stat().st_size < 1024  # Should be much smaller


def test_onboarding_logger_keeps_max_backups(monkeypatch, tmp_path):
    """Test that OnboardingLogger maintains max backup count."""
    from clodputer import onboarding

    log_path = tmp_path / "onboarding.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create existing backup files
    for i in range(1, 6):  # Create .1 through .5
        backup = tmp_path / f"onboarding.log.{i}"
        backup.write_text(f"backup {i}", encoding="utf-8")

    # Create large current log
    large_content = "x" * (11 * 1024 * 1024)
    log_path.write_text(large_content, encoding="utf-8")

    # Mock _onboarding_log_path
    monkeypatch.setattr(onboarding, "_onboarding_log_path", lambda: log_path)

    # Use the logger - should rotate and delete oldest
    with onboarding.OnboardingLogger():
        pass

    # Should have rotated to .1, and existing ones shifted
    assert (tmp_path / "onboarding.log.1").exists()  # New rotation
    assert (tmp_path / "onboarding.log.2").exists()  # Was .1
    assert (tmp_path / "onboarding.log.3").exists()  # Was .2
    assert (tmp_path / "onboarding.log.4").exists()  # Was .3
    assert (tmp_path / "onboarding.log.5").exists()  # Was .4

    # The old .5 should have been deleted (now .6 doesn't exist)
    assert not (tmp_path / "onboarding.log.6").exists()


def test_validate_user_path_allows_home_subdirs(tmp_path, monkeypatch):
    """Test that _validate_user_path allows paths under home directory."""
    from pathlib import Path

    from clodputer import onboarding

    # Mock Path.home() to return tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Path under home should be allowed
    valid_path = tmp_path / "Documents" / "test.md"
    result = onboarding._validate_user_path(valid_path, allow_create=True)

    assert result == valid_path.resolve()


def test_validate_user_path_rejects_outside_home(tmp_path, monkeypatch):
    """Test that _validate_user_path rejects paths outside home directory."""
    from pathlib import Path

    import click

    from clodputer import onboarding

    # Mock Path.home() to return tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Path outside home should be rejected
    malicious_path = Path("/etc/passwd")

    try:
        onboarding._validate_user_path(malicious_path, allow_create=True)
        assert False, "Should have raised ClickException"
    except click.ClickException as exc:
        assert "must be within your home directory" in str(exc)


def test_validate_user_path_requires_existing(tmp_path, monkeypatch):
    """Test that _validate_user_path can require paths to exist."""
    from pathlib import Path

    import click

    from clodputer import onboarding

    # Mock Path.home() to return tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Non-existent path with allow_create=False should be rejected
    nonexistent = tmp_path / "does_not_exist.md"

    try:
        onboarding._validate_user_path(nonexistent, allow_create=False)
        assert False, "Should have raised ClickException"
    except click.ClickException as exc:
        assert "does not exist" in str(exc)


def test_ensure_directories_handles_permission_error(monkeypatch, tmp_path):
    """Test that directory creation handles permission errors."""
    from clodputer import onboarding

    # Mock mkdir to raise permission error for logs directory
    original_mkdir = Path.mkdir

    def mock_mkdir(self, *args, **kwargs):
        if "logs" in str(self) or "archive" in str(self):
            raise OSError("Permission denied")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    # Should raise OSError
    try:
        onboarding._ensure_directories()
        assert False, "Should have raised OSError"
    except OSError as exc:
        assert "Permission denied" in str(exc)


def test_check_network_connectivity_success(monkeypatch):
    """Test network connectivity check when network is available."""
    from clodputer import onboarding
    import socket

    # Mock socket.create_connection to succeed
    def mock_create_connection(*args, **kwargs):
        return SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(socket, "create_connection", mock_create_connection)

    assert onboarding._check_network_connectivity() is True


def test_check_network_connectivity_failure(monkeypatch):
    """Test network connectivity check when network is unavailable."""
    from clodputer import onboarding
    import socket

    # Mock socket.create_connection to raise timeout
    def mock_create_connection(*args, **kwargs):
        raise socket.timeout("Connection timed out")

    monkeypatch.setattr(socket, "create_connection", mock_create_connection)

    assert onboarding._check_network_connectivity() is False
