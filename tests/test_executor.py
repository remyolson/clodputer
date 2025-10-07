from __future__ import annotations

from pathlib import Path

import subprocess

from clodputer.cleanup import CleanupReport
from clodputer.config import ConfigError, TaskConfig
from clodputer.executor import NullExecutionLogger, TaskExecutor, _extract_json, build_command
from clodputer.queue import QueueManager


def make_task_config() -> TaskConfig:
    return TaskConfig.model_validate(
        {
            "name": "sample",
            "task": {
                "prompt": "Say hello",
                "allowed_tools": ["Read", "Write"],
                "permission_mode": "acceptEdits",
                "timeout": 60,
            },
        }
    )


def test_build_command_includes_flags(monkeypatch) -> None:
    monkeypatch.setenv("CLODPUTER_CLAUDE_BIN", "/usr/bin/claude")
    config = make_task_config()
    cmd = build_command(config)
    assert cmd[0] == "/usr/bin/claude"
    assert "--allowed-tools" in cmd
    assert "--permission-mode" in cmd


def test_extract_json_handles_code_block() -> None:
    stdout = """```json
{"ok": true}
```"""
    parsed, error = _extract_json(stdout)
    assert error is None
    assert parsed == {"ok": True}


def test_run_config_path_success(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "task.yaml"
    config_path.write_text(
        """
name: temp-task
task:
  prompt: "Say hi"
  allowed_tools: ["Read"]
  timeout: 10
        """,
        encoding="utf-8",
    )

    class FakeProcess:
        def __init__(self) -> None:
            self.pid = 1234
            self.returncode = 0

        def communicate(self, timeout=None):
            return ('{"ok": true}', "")

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr(
        "clodputer.executor.subprocess.Popen",
        lambda *a, **k: FakeProcess(),
    )
    monkeypatch.setattr(
        "clodputer.executor.cleanup_process_tree",
        lambda pid: CleanupReport([], [], []),
    )

    executor = TaskExecutor(execution_logger=NullExecutionLogger())
    result = executor.run_config_path(config_path)
    assert result.status == "success"
    assert result.output_json == {"ok": True}


def test_process_queue_handles_config_error(monkeypatch, tmp_path: Path) -> None:
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    with QueueManager(queue_file=queue_file, lock_file=lock_file) as queue:
        queue.enqueue("bad-task")

    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)

    def fake_load_task(name: str):
        raise ConfigError("broken config")

    monkeypatch.setattr("clodputer.executor.load_task_by_name", fake_load_task)
    executor = TaskExecutor(queue_manager=queue, execution_logger=NullExecutionLogger())
    outcome = executor.process_queue_once()
    assert outcome is None
    status = queue.get_status()
    assert status["queued_counts"]["total"] == 0


def test_process_queue_success(monkeypatch, tmp_path: Path) -> None:
    config = make_task_config()

    class FakeProcess:
        def __init__(self) -> None:
            self.pid = 5678
            self.returncode = 0

        def communicate(self, timeout=None):
            return ('{"task": "sample"}', "")

        def kill(self):
            self.returncode = -9

    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    with QueueManager(queue_file=queue_file, lock_file=lock_file) as queue:
        queue.enqueue("sample")

    monkeypatch.setenv("CLODPUTER_CLAUDE_BIN", "/usr/bin/claude")
    monkeypatch.setattr("clodputer.executor.load_task_by_name", lambda name: config)
    monkeypatch.setattr(
        "clodputer.executor.subprocess.Popen",
        lambda *a, **k: FakeProcess(),
    )
    monkeypatch.setattr(
        "clodputer.executor.cleanup_process_tree",
        lambda pid: CleanupReport([], [], []),
    )

    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    executor = TaskExecutor(queue_manager=queue, execution_logger=NullExecutionLogger())
    result = executor.process_queue_once()
    assert result is not None
    assert result.status == "success"
    status = queue.get_status()
    assert status["queued_counts"]["total"] == 0


def test_process_queue_json_failure(monkeypatch, tmp_path: Path) -> None:
    config = make_task_config()

    class FakeProcess:
        def __init__(self) -> None:
            self.pid = 91011
            self.returncode = 0

        def communicate(self, timeout=None):
            return ("not json", "")

        def kill(self):
            self.returncode = -9

    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    with QueueManager(queue_file=queue_file, lock_file=lock_file) as queue:
        queue.enqueue("sample")

    monkeypatch.setenv("CLODPUTER_CLAUDE_BIN", "/usr/bin/claude")
    monkeypatch.setattr("clodputer.executor.load_task_by_name", lambda name: config)
    monkeypatch.setattr(
        "clodputer.executor.subprocess.Popen",
        lambda *a, **k: FakeProcess(),
    )
    monkeypatch.setattr(
        "clodputer.executor.cleanup_process_tree",
        lambda pid: CleanupReport([], [], []),
    )

    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    executor = TaskExecutor(queue_manager=queue, execution_logger=NullExecutionLogger())
    result = executor.process_queue_once()
    assert result is not None
    assert result.status == "failure"
    status = queue.get_status()
    assert status["failed_recent"]


def test_run_config_path_timeout(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "timeout.yaml"
    config_path.write_text(
        """
name: timeout-task
task:
  prompt: "Wait"
  allowed_tools: ["Read"]
  timeout: 1
        """,
        encoding="utf-8",
    )

    class TimeoutProcess:
        def __init__(self) -> None:
            self.pid = 4242
            self.returncode = 0
            self._first = True

        def communicate(self, timeout=None):
            if self._first:
                self._first = False
                raise subprocess.TimeoutExpired(cmd="claude", timeout=timeout)
            self.returncode = -9
            return ("", "")

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr(
        "clodputer.executor.subprocess.Popen",
        lambda *a, **k: TimeoutProcess(),
    )
    monkeypatch.setattr(
        "clodputer.executor.cleanup_process_tree",
        lambda pid: CleanupReport([], [], []),
    )

    executor = TaskExecutor(execution_logger=NullExecutionLogger())
    result = executor.run_config_path(config_path)
    assert result.status == "timeout"


def test_run_config_path_failure(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "failure.yaml"
    config_path.write_text(
        """
name: failure-task
task:
  prompt: "Fail"
  allowed_tools: ["Read"]
  timeout: 10
        """,
        encoding="utf-8",
    )

    class FailingProcess:
        def __init__(self) -> None:
            self.pid = 555
            self.returncode = 1

        def communicate(self, timeout=None):
            return ("{\"ok\": false}", "error")

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr(
        "clodputer.executor.subprocess.Popen",
        lambda *a, **k: FailingProcess(),
    )
    monkeypatch.setattr(
        "clodputer.executor.cleanup_process_tree",
        lambda pid: CleanupReport([], [], []),
    )

    executor = TaskExecutor(execution_logger=NullExecutionLogger())
    result = executor.run_config_path(config_path)
    assert result.status == "failure"
    assert "code 1" in (result.error or "")
