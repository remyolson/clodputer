from __future__ import annotations

from pathlib import Path

import pytest

from clodputer import watcher
from clodputer.config import TaskConfig


def make_watch_task(name: str = "watch-task") -> TaskConfig:
    return TaskConfig.model_validate(
        {
            "name": name,
            "enabled": True,
            "priority": "normal",
            "trigger": {
                "type": "file_watch",
                "path": "~/watched",
                "pattern": "*.txt",
                "event": "created",
                "debounce": 500,
            },
            "task": {
                "prompt": "Handle files",
                "allowed_tools": ["Read"],
            },
        }
    )


def test_file_watch_tasks_filters_only_watchers() -> None:
    manual = TaskConfig.model_validate(
        {
            "name": "manual",
            "enabled": True,
            "task": {"prompt": "Manual", "allowed_tools": ["Read"]},
        }
    )
    tasks = watcher.file_watch_tasks([make_watch_task(), manual])
    assert len(tasks) == 1
    assert tasks[0].name == "watch-task"


def test_is_daemon_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pid_file = tmp_path / "watcher.pid"
    log_file = tmp_path / "watcher.log"
    monkeypatch.setattr(watcher, "WATCHER_PID_FILE", pid_file)
    monkeypatch.setattr(watcher, "WATCHER_LOG_FILE", log_file)
    pid_file.write_text("123")
    monkeypatch.setattr(watcher.psutil, "pid_exists", lambda pid: pid == 123)
    assert watcher.is_daemon_running()


def test_start_daemon_raises_if_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pid_file = tmp_path / "watcher.pid"
    log_file = tmp_path / "watcher.log"
    monkeypatch.setattr(watcher, "WATCHER_PID_FILE", pid_file)
    monkeypatch.setattr(watcher, "WATCHER_LOG_FILE", log_file)
    pid_file.write_text("999")
    monkeypatch.setattr(watcher.psutil, "pid_exists", lambda pid: True)
    with pytest.raises(watcher.WatcherError):
        watcher.start_daemon()


def test_run_watch_service_without_tasks_raises() -> None:
    with pytest.raises(watcher.WatcherError):
        watcher.run_watch_service([])
