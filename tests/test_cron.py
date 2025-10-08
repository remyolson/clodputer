from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

import pytest

from clodputer import cron
from clodputer.config import TaskConfig


def make_scheduled_task(name: str = "sample") -> TaskConfig:
    return TaskConfig.model_validate(
        {
            "name": name,
            "enabled": True,
            "priority": "normal",
            "schedule": {
                "type": "cron",
                "expression": "0 8 * * *",
                "timezone": "America/Los_Angeles",
            },
            "task": {
                "prompt": "Hello world",
                "allowed_tools": ["Read"],
            },
        }
    )


def test_validate_cron_expression_accepts_macros() -> None:
    assert cron.validate_cron_expression("@daily")
    assert not cron.validate_cron_expression("invalid expression")


def test_generate_cron_section_includes_timezone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cron, "CRON_LOG_FILE", tmp_path / "cron.log")
    section = cron.generate_cron_section([make_scheduled_task()])
    assert "CRON_TZ=America/Los_Angeles" in section
    assert " run sample" in section


def test_install_cron_jobs_writes_section(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cron, "CRON_BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(cron, "CRON_LOG_FILE", tmp_path / "cron.log")

    written_inputs: List[str] = []

    def fake_call(args, input_text=None):
        if args == ["-l"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args == ["-"]:
            written_inputs.append(input_text or "")
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(f"Unexpected args: {args}")

    monkeypatch.setattr(cron, "_call_crontab", fake_call)

    result = cron.install_cron_jobs([make_scheduled_task()])
    assert result["installed"] == 1
    assert written_inputs, "crontab - should be invoked"


def test_cron_section_present(monkeypatch: pytest.MonkeyPatch) -> None:
    content = f"{cron.CRON_SECTION_BEGIN}\n# test\n{cron.CRON_SECTION_END}\n"
    monkeypatch.setattr(cron, "read_crontab", lambda: content)
    assert cron.cron_section_present()


def test_is_cron_daemon_running(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProc:
        def __init__(self, name: str):
            self.info = {"name": name}

    monkeypatch.setattr(cron.psutil, "process_iter", lambda attrs: [FakeProc("cron")])
    assert cron.is_cron_daemon_running()


def test_format_command_includes_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLODPUTER_CLAUDE_BIN", "/usr/bin/claude")
    monkeypatch.setenv("CLODPUTER_EXTRA_ARGS", "--foo bar")
    cmd = cron._format_command(make_scheduled_task())
    assert "CLODPUTER_CLAUDE_BIN=/usr/bin/claude" in cmd
    assert "--foo" in cmd


def test_uninstall_cron_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    content = f"{cron.CRON_SECTION_BEGIN}\n* * * * * echo hi\n{cron.CRON_SECTION_END}\n"
    monkeypatch.setattr(cron, "_call_crontab", lambda args, input_text=None: subprocess.CompletedProcess(args, 0, "", ""))

    calls: List[str] = []

    def fake_read():
        return content

    def fake_call(args, input_text=None):
        if args == ["-l"]:
            return subprocess.CompletedProcess(args, 0, content, "")
        if args == ["-"]:
            calls.append(input_text or "")
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError

    monkeypatch.setattr(cron, "_call_crontab", fake_call)
    monkeypatch.setattr(cron, "read_crontab", fake_read)

    result = cron.uninstall_cron_jobs()
    assert result["removed"]
    assert calls and cron.CRON_SECTION_BEGIN not in calls[0]


def test_uninstall_cron_jobs_no_section(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cron, "read_crontab", lambda: "# no clodputer jobs")
    result = cron.uninstall_cron_jobs()
    assert not result["removed"]


def test_scheduled_tasks_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduled = make_scheduled_task("has-schedule")
    disabled = make_scheduled_task("disabled")
    disabled.enabled = False
    manual = TaskConfig.model_validate(
        {
            "name": "manual",
            "task": {"prompt": "hi", "allowed_tools": ["Read"]},
        }
    )
    tasks = cron.scheduled_tasks([scheduled, disabled, manual])
    assert [task.name for task in tasks] == ["has-schedule"]
