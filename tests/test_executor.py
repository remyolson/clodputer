from __future__ import annotations

from pathlib import Path

import subprocess

from clodputer import metrics as metrics_module
from clodputer import settings as settings_module
from clodputer.cleanup import CleanupReport
from clodputer.config import ConfigError, TaskConfig
from clodputer.executor import (
    ExecutionResult,
    NullExecutionLogger,
    TaskExecutor,
    TaskExecutionError,
    _extract_json,
    build_command,
    main,
)
from clodputer.queue import QueueManager


def _configure_environment(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    metrics_path = home / ".clodputer" / "metrics.json"
    monkeypatch.setattr(metrics_module, "METRICS_FILE", metrics_path)
    settings_path = home / ".clodputer" / "config.yaml"
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", settings_path)
    monkeypatch.setattr(settings_module, "_CACHE", None)
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 5.0)
    monkeypatch.setattr("psutil.virtual_memory", lambda: type("vm", (), {"percent": 5.0})())


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
    _configure_environment(tmp_path, monkeypatch)
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
    assert result.return_code == 0


def test_process_queue_handles_config_error(monkeypatch, tmp_path: Path) -> None:
    _configure_environment(tmp_path, monkeypatch)
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
    _configure_environment(tmp_path, monkeypatch)
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
    assert status["completed_recent"][-1]["result"]["return_code"] == 0


def test_process_queue_json_failure(monkeypatch, tmp_path: Path) -> None:
    _configure_environment(tmp_path, monkeypatch)
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
    assert status["failed_recent"][-1]["error"]["return_code"] == 0


def test_run_config_path_timeout(monkeypatch, tmp_path: Path) -> None:
    _configure_environment(tmp_path, monkeypatch)
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
    assert result.return_code == -9


def test_run_config_path_failure(monkeypatch, tmp_path: Path) -> None:
    _configure_environment(tmp_path, monkeypatch)
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
            return ('{"ok": false}', "error")

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
    assert result.return_code == 1
    assert "code 1" in (result.error or "")


def test_process_queue_skips_disabled(monkeypatch, tmp_path: Path) -> None:
    _configure_environment(tmp_path, monkeypatch)
    disabled = make_task_config()
    disabled.enabled = False

    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    with QueueManager(queue_file=queue_file, lock_file=lock_file) as queue:
        queue.enqueue("disabled-task")

    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    monkeypatch.setattr("clodputer.executor.load_task_by_name", lambda name: disabled)
    executor = TaskExecutor(queue_manager=queue, execution_logger=NullExecutionLogger())
    outcome = executor.process_queue_once()
    assert outcome is None
    failure = queue.get_status()["failed_recent"][0]["error"]
    assert failure["error"] == "task_disabled"


def test_run_task_by_name_success(monkeypatch, tmp_path: Path) -> None:
    _configure_environment(tmp_path, monkeypatch)
    config = make_task_config()

    class FakeProcess:
        def __init__(self) -> None:
            self.pid = 999
            self.returncode = 0

        def communicate(self, timeout=None):
            return ('{"ok": true}', "")

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr("clodputer.executor.load_task_by_name", lambda name: config)
    monkeypatch.setattr("clodputer.executor.subprocess.Popen", lambda *a, **k: FakeProcess())
    monkeypatch.setattr(
        "clodputer.executor.cleanup_process_tree",
        lambda pid: CleanupReport([], [], []),
    )

    executor = TaskExecutor(execution_logger=NullExecutionLogger())
    result = executor.run_task_by_name("sample")
    assert result.status == "success"
    assert result.return_code == 0


def test_retry_on_failure(monkeypatch, tmp_path: Path) -> None:
    _configure_environment(tmp_path, monkeypatch)
    config = make_task_config()
    config.task.max_retries = 1
    config.task.retry_backoff_seconds = 1

    class FailingProcess:
        def __init__(self) -> None:
            self.pid = 111
            self.returncode = 1

        def communicate(self, timeout=None):
            return ("", "error")

        def kill(self):
            self.returncode = -9

    class SuccessProcess:
        def __init__(self) -> None:
            self.pid = 222
            self.returncode = 0

        def communicate(self, timeout=None):
            return ('{"ok": true}', "")

        def kill(self):
            self.returncode = -9

    processes = [FailingProcess(), SuccessProcess()]

    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    with QueueManager(queue_file=queue_file, lock_file=lock_file) as queue:
        queue.enqueue("sample")

    monkeypatch.setattr("clodputer.executor.load_task_by_name", lambda name: config)
    monkeypatch.setattr(
        "clodputer.executor.cleanup_process_tree", lambda pid: CleanupReport([], [], [])
    )
    monkeypatch.setattr(
        "clodputer.executor.subprocess.Popen",
        lambda *a, **k: processes.pop(0),
    )

    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    executor = TaskExecutor(queue_manager=queue, execution_logger=NullExecutionLogger())

    first = executor.process_queue_once()
    assert first is not None and first.status == "failure"

    # Fast-forward retry delay
    queue._state.queued[0].not_before = None
    queue._persist_state()

    second = executor.process_queue_once()
    assert second is not None and second.status == "success"

    summary = metrics_module.metrics_summary()
    assert summary["sample"]["failure"] >= 1
    assert summary["sample"]["success"] >= 1


def test_executor_main_queue_success(monkeypatch) -> None:
    class DummyQueue:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    success_result = ExecutionResult(
        task_id="1",
        task_name="sample",
        status="success",
        return_code=0,
        duration=0.1,
        stdout="",
        stderr="",
        cleanup=CleanupReport([], [], []),
        output_json={},
        output_parse_error=None,
        error=None,
    )

    monkeypatch.setattr("clodputer.executor.QueueManager", lambda: DummyQueue())
    monkeypatch.setattr(
        TaskExecutor,
        "process_queue",
        lambda self: [success_result],
    )

    assert main(["--queue"]) == 0


def test_executor_main_queue_failure(monkeypatch) -> None:
    class DummyQueue:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    failure_result = ExecutionResult(
        task_id="1",
        task_name="sample",
        status="failure",
        return_code=1,
        duration=0.1,
        stdout="",
        stderr="err",
        cleanup=CleanupReport([], [], []),
        output_json=None,
        output_parse_error=None,
        error="boom",
    )

    monkeypatch.setattr("clodputer.executor.QueueManager", lambda: DummyQueue())
    monkeypatch.setattr(
        TaskExecutor,
        "process_queue",
        lambda self: [failure_result],
    )

    assert main(["--queue"]) == 1


def test_executor_main_handles_error(monkeypatch) -> None:
    monkeypatch.setattr(
        TaskExecutor,
        "run_task_by_name",
        lambda self, name: (_ for _ in ()).throw(TaskExecutionError("boom")),
    )
    assert main(["--task", "sample"]) == 1
