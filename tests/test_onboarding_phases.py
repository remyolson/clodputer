"""Tests for onboarding phases: templates, CLAUDE.md, automation, runtime shortcuts, and smoke tests."""

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


def test_onboarding_template_copy_flow(monkeypatch, tmp_path):
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

    monkeypatch.setattr(
        onboarding, "ensure_queue_dir", lambda: queue_dir.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(
        onboarding, "ensure_tasks_dir", lambda: tasks_dir.mkdir(parents=True, exist_ok=True)
    )

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

    copied: dict[str, Path] = {}

    def fake_export(name: str, destination: Path | str) -> Path:
        path = Path(destination)
        path.write_text("template-contents", encoding="utf-8")
        copied["path"] = path
        copied["name"] = name
        return path

    monkeypatch.setattr(
        onboarding, "available_templates", lambda: ["daily-email.yaml", "manual-task.yaml"]
    )
    monkeypatch.setattr(onboarding, "export_template", fake_export)

    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input="\n\n\n\n")

    assert result.exit_code == 0, result.output
    expected_path = tasks_dir / "daily-email.yaml"
    assert expected_path.exists()
    assert expected_path.read_text(encoding="utf-8") == "template-contents"
    assert copied["name"] == "daily-email.yaml"


def test_onboarding_updates_claude_md(monkeypatch, tmp_path):
    from clodputer import config, environment, queue, onboarding
    from clodputer.cli import cli

    home = tmp_path / "home"
    claude_path = tmp_path / "bin" / "claude"
    claude_path.parent.mkdir(parents=True)
    claude_path.write_text("#!/bin/sh\necho 'Claude CLI 1.0'\n")
    claude_path.chmod(0o755)

    claude_md = home / "CLAUDE.md"
    claude_md.parent.mkdir(parents=True, exist_ok=True)
    claude_md.write_text("# Existing instructions\n", encoding="utf-8")

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

    monkeypatch.setattr(onboarding, "available_templates", lambda: [])
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
    result = runner.invoke(cli, ["init"], input="\n\n\n")

    assert result.exit_code == 0, result.output
    updated_text = claude_md.read_text(encoding="utf-8")
    assert onboarding.CLAUDE_MD_SENTINEL in updated_text
    assert "# Existing instructions" in updated_text
    backups = list(claude_md.parent.glob("CLAUDE.md.backup-*"))
    assert backups, "Expected a CLAUDE.md backup to be created"


def test_onboarding_template_skip_when_declined(monkeypatch, tmp_path):
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

    monkeypatch.setattr(
        onboarding, "ensure_queue_dir", lambda: queue_dir.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(
        onboarding, "ensure_tasks_dir", lambda: tasks_dir.mkdir(parents=True, exist_ok=True)
    )

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

    monkeypatch.setattr(onboarding, "available_templates", lambda: ["manual-task.yaml"])

    exports: dict[str, int] = {"count": 0}

    def fake_export(name: str, destination: Path | str) -> Path:
        exports["count"] += 1
        path = Path(destination)
        path.write_text("template", encoding="utf-8")
        return path

    monkeypatch.setattr(onboarding, "export_template", fake_export)

    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input="\nn\n")

    assert result.exit_code == 0, result.output
    assert exports["count"] == 0
    assert not any(tasks_dir.glob("*.yaml"))


def test_apply_claude_md_update_noop_when_present(tmp_path):
    from clodputer import onboarding

    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(f"{onboarding.CLAUDE_MD_SENTINEL}\nExisting guidance\n", encoding="utf-8")

    onboarding._apply_claude_md_update(claude_md)

    contents = claude_md.read_text(encoding="utf-8")
    assert contents.startswith(onboarding.CLAUDE_MD_SENTINEL)
    assert "Existing guidance" in contents


def test_apply_claude_md_update_skips_on_decline(monkeypatch, tmp_path):
    from clodputer import onboarding

    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Existing\n", encoding="utf-8")

    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: False)

    onboarding._apply_claude_md_update(claude_md)

    contents = claude_md.read_text(encoding="utf-8")
    assert onboarding.CLAUDE_MD_SENTINEL not in contents
    assert contents == "# Existing\n"


def test_onboarding_manual_claude_md_path(monkeypatch, tmp_path):
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

    monkeypatch.setattr(
        onboarding, "ensure_queue_dir", lambda: queue_dir.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(
        onboarding, "ensure_tasks_dir", lambda: tasks_dir.mkdir(parents=True, exist_ok=True)
    )

    monkeypatch.setattr(onboarding, "available_templates", lambda: [])
    monkeypatch.setattr(onboarding, "_detect_claude_md_candidates", lambda: [])
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

    recorded: dict[str, Path] = {}

    def fake_apply(path: Path) -> None:
        recorded["path"] = path

    monkeypatch.setattr(onboarding, "_apply_claude_md_update", fake_apply)

    target_path = home / "Documents" / "CustomCLAUDE.md"

    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input=f"\ny\n{target_path}\n")

    assert result.exit_code == 0, result.output
    assert recorded["path"] == target_path
    assert target_path.exists()


def test_onboarding_selects_claude_md_from_candidates(monkeypatch, tmp_path):
    from clodputer import config, environment, queue, onboarding
    from clodputer.cli import cli

    home = tmp_path / "home"
    claude_path = tmp_path / "bin" / "claude"
    claude_path.parent.mkdir(parents=True)
    claude_path.write_text("#!/bin/sh\necho 'Claude CLI 1.0'\n")
    claude_path.chmod(0o755)

    candidate_one = home / "CLAUDE.md"
    candidate_two = home / "Documents" / "CLAUDE.md"
    candidate_one.parent.mkdir(parents=True, exist_ok=True)
    candidate_two.parent.mkdir(parents=True, exist_ok=True)
    candidate_one.write_text("# One\n", encoding="utf-8")
    candidate_two.write_text("# Two\n", encoding="utf-8")

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

    monkeypatch.setattr(onboarding, "available_templates", lambda: [])
    monkeypatch.setattr(
        onboarding, "_detect_claude_md_candidates", lambda: [candidate_one, candidate_two]
    )
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

    recorded: dict[str, Path] = {}

    def fake_apply(path: Path) -> None:
        recorded["path"] = path

    monkeypatch.setattr(onboarding, "_apply_claude_md_update", fake_apply)

    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input="\n2\n")

    assert result.exit_code == 0, result.output
    assert recorded["path"] == candidate_two


def test_offer_cron_setup_installs_jobs_when_confirmed(monkeypatch):
    from datetime import datetime

    from clodputer import onboarding
    from clodputer.config import ScheduleConfig, TaskConfig, TaskSpec

    task = TaskConfig(
        name="scheduled",
        task=TaskSpec(prompt="Do the thing"),
        schedule=ScheduleConfig(type="cron", expression="0 * * * *"),
    )

    install_calls: dict[str, object] = {}

    def fake_install(entries):
        install_calls["count"] = len(entries)
        return {"installed": len(entries), "backup": "/tmp/cron.bak"}

    monkeypatch.setattr(onboarding, "install_cron_jobs", fake_install)
    monkeypatch.setattr(
        onboarding,
        "preview_schedule",
        lambda entry, count=3: [datetime(2025, 1, 1, 0, 0)] * count,
    )

    confirmations = iter([True])
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: next(confirmations))
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._offer_cron_setup([task])

    assert install_calls["count"] == 1
    assert any("Installed 1 cron job" in message for message in outputs)


def test_offer_watcher_setup_creates_path_and_starts_daemon(monkeypatch, tmp_path):
    from clodputer import onboarding
    from clodputer.config import FileWatchTrigger, TaskConfig, TaskSpec

    watch_dir = tmp_path / "watched"
    trigger = FileWatchTrigger(path=str(watch_dir), pattern="*.md", event="created")
    task = TaskConfig(name="watch", task=TaskSpec(prompt="watch"), trigger=trigger)

    confirmations = iter([True, True])
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: next(confirmations))
    monkeypatch.setattr(
        onboarding,
        "watcher_status",
        lambda: {"running": False, "pid": None, "log_file": "log"},
    )

    start_called: dict[str, int] = {}

    def fake_start() -> int:
        start_called["pid"] = 4242
        return 4242

    monkeypatch.setattr(onboarding, "start_watch_daemon", fake_start)

    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._offer_watcher_setup([task])

    assert watch_dir.exists()
    assert start_called["pid"] == 4242
    assert any("Watcher daemon started" in message for message in outputs)


def test_offer_smoke_test_runs_selected_task(monkeypatch):
    from clodputer import onboarding
    from clodputer.config import TaskConfig, TaskSpec

    task = TaskConfig(name="demo", task=TaskSpec(prompt="hello"))

    confirmations = iter([True])
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: next(confirmations))
    monkeypatch.setattr(onboarding.click, "prompt", lambda *_, **__: 1)

    executed: dict[str, str] = {}

    class FakeExecutor:
        def run_task_by_name(self, name: str):
            executed["name"] = name
            return SimpleNamespace(
                status="success",
                task_name=name,
                duration=2.5,
                output_json={"ok": True},
                output_parse_error=None,
                error=None,
                cleanup=SimpleNamespace(
                    actions=["cleanup"],
                ),
            )

    monkeypatch.setattr(onboarding, "TaskExecutor", lambda: FakeExecutor())
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._offer_smoke_test([task])

    assert executed["name"] == "demo"
    assert any("success" in message for message in outputs)


def test_offer_runtime_shortcuts_invokes_launchers(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(onboarding.sys, "platform", "darwin")
    confirmations = iter([True, True])
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: next(confirmations))

    launches: list[str] = []
    monkeypatch.setattr(onboarding, "_launch_menu_bar_app", lambda: launches.append("menu"))
    monkeypatch.setattr(
        onboarding, "_launch_dashboard_terminal", lambda: launches.append("dashboard")
    )

    onboarding._offer_runtime_shortcuts()

    assert launches == ["menu", "dashboard"]


def test_offer_automation_skips_on_validation_errors(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(
        onboarding, "validate_all_tasks", lambda: ([], [(Path("bad.yaml"), "invalid")])
    )
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    result = onboarding._offer_automation()

    assert result == []
    assert any("Resolve task validation errors" in message for message in outputs)


def test_offer_cron_setup_skips_install_when_declined(monkeypatch):
    from clodputer import onboarding
    from clodputer.config import ScheduleConfig, TaskConfig, TaskSpec

    task = TaskConfig(
        name="scheduled",
        task=TaskSpec(prompt="run"),
        schedule=ScheduleConfig(type="cron", expression="0 0 * * *"),
    )

    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: False)
    monkeypatch.setattr(onboarding.click, "echo", lambda *_: None)
    monkeypatch.setattr(
        onboarding,
        "install_cron_jobs",
        lambda *_: (_ for _ in ()).throw(AssertionError("install_cron_jobs should not be called")),
    )

    onboarding._offer_cron_setup([task])


def test_offer_watcher_setup_skips_when_running(monkeypatch, tmp_path):
    from clodputer import onboarding
    from clodputer.config import FileWatchTrigger, TaskConfig, TaskSpec

    watch_dir = tmp_path / "watch"
    watch_dir.mkdir(parents=True)
    trigger = FileWatchTrigger(path=str(watch_dir), pattern="*.txt", event="created")
    task = TaskConfig(name="watch", task=TaskSpec(prompt="watch"), trigger=trigger)

    monkeypatch.setattr(
        onboarding, "watcher_status", lambda: {"running": True, "pid": 123, "log_file": "log"}
    )
    monkeypatch.setattr(onboarding.click, "echo", lambda *_: None)
    monkeypatch.setattr(
        onboarding,
        "start_watch_daemon",
        lambda: (_ for _ in ()).throw(AssertionError("start_watch_daemon called unexpectedly")),
    )

    onboarding._offer_watcher_setup([task])


def test_offer_runtime_shortcuts_non_darwin(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(onboarding.sys, "platform", "linux")
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._offer_runtime_shortcuts()

    assert any("Menu bar is only available" in message for message in outputs)


def test_launch_menu_bar_app_handles_failure(monkeypatch):
    from clodputer import onboarding

    def failing_popen(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(onboarding.subprocess, "Popen", failing_popen)
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._launch_menu_bar_app()

    assert any("Failed to launch menu bar" in message for message in outputs)


def test_launch_dashboard_terminal_success(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(
        onboarding.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=0),
    )
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._launch_dashboard_terminal()

    assert any("Dashboard opened" in message for message in outputs)


def test_offer_smoke_test_decline(monkeypatch):
    from clodputer import onboarding
    from clodputer.config import TaskConfig, TaskSpec

    task = TaskConfig(name="demo", task=TaskSpec(prompt="hello"))

    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: False)
    monkeypatch.setattr(onboarding.click, "echo", lambda *_: None)
    monkeypatch.setattr(onboarding.click, "prompt", lambda *_, **__: 1)

    onboarding._offer_smoke_test([task])


def test_offer_smoke_test_handles_execution_error(monkeypatch):
    from clodputer import onboarding
    from clodputer.config import TaskConfig, TaskSpec
    from clodputer.executor import TaskExecutionError

    task = TaskConfig(name="demo", task=TaskSpec(prompt="hello"))

    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: True)
    monkeypatch.setattr(onboarding.click, "prompt", lambda *_, **__: 1)

    class FailingExecutor:
        def run_task_by_name(self, name: str) -> None:
            raise TaskExecutionError("fail")

    monkeypatch.setattr(onboarding, "TaskExecutor", lambda: FailingExecutor())
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._offer_smoke_test([task])

    assert any("Task execution failed" in message for message in outputs)


def test_offer_template_install_overwrite_declined(monkeypatch, tmp_path):
    from clodputer import onboarding

    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    existing = tasks_dir / "manual.yaml"
    existing.write_text("old", encoding="utf-8")

    monkeypatch.setattr(onboarding, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(onboarding, "available_templates", lambda: ["manual.yaml"])
    monkeypatch.setattr(
        onboarding,
        "export_template",
        lambda *_: (_ for _ in ()).throw(AssertionError("export_template should not be called")),
    )

    confirms = iter([True, False])
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: next(confirms))
    prompts = iter([1, ""])
    monkeypatch.setattr(onboarding.click, "prompt", lambda *_, **__: next(prompts))

    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._offer_template_install()

    assert any("Skipped template import" in message for message in outputs)


def test_offer_claude_md_update_single_candidate_decline(monkeypatch, tmp_path):
    from clodputer import onboarding

    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("content", encoding="utf-8")

    monkeypatch.setattr(onboarding, "_detect_claude_md_candidates", lambda: [claude_md])
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: False)
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._offer_claude_md_update()

    assert any("Skipped CLAUDE.md update" in message for message in outputs)


def test_offer_claude_md_update_no_candidate_decline(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(onboarding, "_detect_claude_md_candidates", lambda: [])
    confirms = iter([False])
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: next(confirms))
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))
    monkeypatch.setattr(onboarding.click, "prompt", lambda *_, **__: "")

    onboarding._offer_claude_md_update()

    assert any("Skipped CLAUDE.md integration" in message for message in outputs)


def test_offer_automation_no_tasks(monkeypatch):
    from clodputer import onboarding

    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    result = onboarding._offer_automation([])

    assert result == []
    assert any("No tasks detected" in message for message in outputs)


def test_offer_runtime_shortcuts_decline_dashboard(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(onboarding.sys, "platform", "darwin")
    confirmations = iter([False, False])
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: next(confirmations))
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._offer_runtime_shortcuts()

    assert any("Run `clodputer dashboard` anytime" in message for message in outputs)


def test_launch_menu_bar_app_success(monkeypatch):
    from clodputer import onboarding

    launches: dict[str, object] = {}

    def fake_popen(command, **kwargs):
        launches["command"] = command
        return SimpleNamespace()

    monkeypatch.setattr(onboarding.subprocess, "Popen", fake_popen)
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._launch_menu_bar_app()

    assert launches["command"][-1] == "menu"
    assert any("Menu bar launched" in message for message in outputs)


def test_launch_dashboard_terminal_failure(monkeypatch):
    import subprocess

    from clodputer import onboarding

    def failing_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(onboarding.subprocess, "run", failing_run)
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._launch_dashboard_terminal()

    assert any("Failed to launch dashboard" in message for message in outputs)


def test_offer_smoke_test_skips_due_to_errors(monkeypatch):
    from clodputer import onboarding

    monkeypatch.setattr(onboarding, "_load_task_configs", lambda: ([], [(Path("bad"), "err")]))
    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._offer_smoke_test(None)

    assert any("Skipping smoke test" in message for message in outputs)


def test_detect_claude_md_candidates(monkeypatch, tmp_path):
    from clodputer import onboarding

    home = tmp_path / "home"
    home.mkdir()
    claude_md = home / "CLAUDE.md"
    claude_md.write_text("content", encoding="utf-8")
    docs_claude = home / "Documents" / "CLAUDE.md"
    docs_claude.parent.mkdir(parents=True)
    docs_claude.write_text("content", encoding="utf-8")

    monkeypatch.setattr(onboarding.Path, "home", lambda: home)

    candidates = onboarding._detect_claude_md_candidates()

    assert len(candidates) == 2
    assert claude_md in candidates
    assert docs_claude in candidates


def test_render_smoke_test_result_success(monkeypatch):
    from clodputer import onboarding

    result = SimpleNamespace(
        status="success",
        task_name="test",
        duration=2.5,
        output_json={"result": "ok"},
        output_parse_error=None,
        error=None,
        cleanup=SimpleNamespace(actions=["cleanup1", "cleanup2"]),
    )

    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._render_smoke_test_result(result)

    assert any(
        "✅" in message and "test" in message and "success" in message for message in outputs
    )
    assert any("2s" in message for message in outputs)


def test_render_smoke_test_result_with_parse_error(monkeypatch):
    from clodputer import onboarding

    result = SimpleNamespace(
        status="success",
        task_name="test",
        duration=1.0,
        output_json=None,
        output_parse_error="Invalid JSON",
        error=None,
        cleanup=SimpleNamespace(actions=[]),
    )

    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._render_smoke_test_result(result)

    assert any("Output parse error" in message and "Invalid JSON" in message for message in outputs)


def test_render_smoke_test_result_failure(monkeypatch):
    from clodputer import onboarding

    result = SimpleNamespace(
        status="error",
        task_name="test",
        duration=0.5,
        output_json=None,
        output_parse_error=None,
        error="Something went wrong",
        cleanup=SimpleNamespace(actions=[]),
    )

    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda message: outputs.append(message))

    onboarding._render_smoke_test_result(result)

    assert any("⚠️" in message and "test" in message and "error" in message for message in outputs)
    assert any("Error: Something went wrong" in message for message in outputs)


def test_apply_claude_md_invalid_utf8(monkeypatch, tmp_path):
    """Test handling of CLAUDE.md with invalid UTF-8 encoding."""
    from clodputer import onboarding

    claude_md = tmp_path / "CLAUDE.md"
    # Write invalid UTF-8 bytes
    claude_md.write_bytes(b"\xff\xfe Invalid UTF-8")

    # Should raise ClickException with helpful message
    try:
        onboarding._apply_claude_md_update(claude_md)
        assert False, "Should have raised ClickException"
    except Exception as exc:
        # Could be ClickException or UnicodeDecodeError depending on implementation
        assert "Failed to read" in str(exc) or "decode" in str(exc).lower()


def test_apply_claude_md_large_file_warning(monkeypatch, tmp_path):
    """Test that large CLAUDE.md files trigger size warnings."""
    from clodputer import onboarding

    claude_md = tmp_path / "CLAUDE.md"
    # Create a 2MB file
    large_content = "x" * (2 * 1024 * 1024)
    claude_md.write_text(large_content, encoding="utf-8")

    outputs: list[str] = []
    monkeypatch.setattr(onboarding.click, "echo", lambda msg: outputs.append(msg))
    monkeypatch.setattr(onboarding.click, "confirm", lambda *_, **__: False)

    # Should skip update when user declines
    onboarding._apply_claude_md_update(claude_md)

    # Should have warned about large file
    assert any("large" in msg.lower() for msg in outputs)
    assert any("2MB" in msg or "2 MB" in msg for msg in outputs)
