"""Tests for Claude CLI detection and verification."""

import subprocess
from pathlib import Path
from types import SimpleNamespace


def test_choose_claude_cli_reprompts_until_valid(monkeypatch, tmp_path):
    from clodputer import onboarding

    candidate = tmp_path / "missing"
    valid_path = tmp_path / "bin" / "claude"
    valid_path.parent.mkdir(parents=True, exist_ok=True)
    valid_path.write_text("#!/bin/sh\n", encoding="utf-8")

    responses = iter([str(tmp_path / "invalid"), str(valid_path)])

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: str(candidate))
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: False)
    monkeypatch.setattr(onboarding.click, "prompt", lambda *_, **__: next(responses))

    echoes: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: echoes.append(message))

    result = onboarding._choose_claude_cli()

    assert result == str(valid_path)
    assert any("Path not found" in msg for msg in echoes)


def test_choose_claude_cli_handles_path_errors(monkeypatch, tmp_path):
    """Test that _choose_claude_cli handles OS/ValueError gracefully."""
    from clodputer import onboarding

    valid_path = tmp_path / "bin" / "claude"
    valid_path.parent.mkdir(parents=True, exist_ok=True)
    valid_path.write_text("#!/bin/sh\n", encoding="utf-8")

    # Mock claude_cli_path to return a path that will cause OSError
    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: "/dev/null/bad_path")

    # Track click.echo calls to verify error message
    echoes: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: echoes.append(message))

    # Provide valid path on first prompt
    monkeypatch.setattr(onboarding.click, "prompt", lambda *_, **__: str(valid_path))

    # Mock Path.exists to raise OSError on first call, then work normally
    call_count = {"count": 0}
    original_exists = Path.exists

    def mock_exists(self):
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise OSError("Permission denied")
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", mock_exists)

    result = onboarding._choose_claude_cli()

    assert result == str(valid_path)
    assert any("Cannot access" in msg or "Invalid path" in msg for msg in echoes)


def test_verify_claude_cli_success(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(
        onboarding.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=0, stdout="Claude CLI 1.0\n", stderr=""),
    )
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._verify_claude_cli("/path/to/claude")

    assert any("Detected Claude CLI" in message for message in outputs)


def test_verify_claude_cli_failure(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(
        onboarding.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=1, stdout="", stderr=""),
    )
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._verify_claude_cli("/path/to/claude")

    assert any("Unable to confirm Claude CLI version" in message for message in outputs)


def test_verify_claude_cli_timeout(monkeypatch):
    """Test that Claude CLI verification handles timeouts gracefully."""
    from clodputer import onboarding

    def timeout_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=10)

    monkeypatch.setattr(onboarding.subprocess, "run", timeout_run)
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda msg: outputs.append(msg))

    # Should not raise, should print warning
    onboarding._verify_claude_cli("/path/to/claude")

    assert any("timed out" in msg for msg in outputs)
    assert any("10 seconds" in msg for msg in outputs)
