import json
from types import SimpleNamespace

from click.testing import CliRunner


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

    monkeypatch.setattr(onboarding, "ensure_queue_dir", lambda: queue_dir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(onboarding, "ensure_tasks_dir", lambda: tasks_dir.mkdir(parents=True, exist_ok=True))

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: str(claude_path))
    monkeypatch.setattr(
        onboarding,
        "subprocess",
        SimpleNamespace(run=lambda *_, **__: SimpleNamespace(returncode=0, stdout="Claude CLI 1.0")),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input="\n")

    assert result.exit_code == 0, result.output
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["claude_cli"] == str(claude_path)
    assert tasks_dir.exists()


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
    monkeypatch.setattr(onboarding, "ensure_queue_dir", lambda: queue_dir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(onboarding, "ensure_tasks_dir", lambda: tasks_dir.mkdir(parents=True, exist_ok=True))

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: None)
    monkeypatch.setattr(
        onboarding,
        "subprocess",
        SimpleNamespace(run=lambda *_, **__: SimpleNamespace(returncode=0, stdout="Claude CLI 1.0")),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input=f"{claude_path}\n")

    assert result.exit_code == 0, result.output
    data = json.loads(state_file.read_text())
    assert data["claude_cli"] == str(claude_path)
