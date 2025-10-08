from __future__ import annotations

from pathlib import Path

from clodputer import metrics as metrics_module
from clodputer import settings as settings_module
from clodputer.queue import QueueItem, QueueManager
from types import SimpleNamespace


def _configure_environment(tmp_path: Path, monkeypatch=None) -> None:
    metrics_path = tmp_path / "metrics.json"
    if monkeypatch:
        monkeypatch.setattr(metrics_module, "METRICS_FILE", metrics_path)
    settings_path = tmp_path / "config.yaml"
    if monkeypatch:
        monkeypatch.setattr(settings_module, "SETTINGS_FILE", settings_path)
        monkeypatch.setattr(settings_module, "_CACHE", None)


def test_queue_enqueue_and_record_failure(tmp_path: Path, monkeypatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"

    with QueueManager(queue_file=queue_file, lock_file=lock_file) as queue:
        item = queue.enqueue("sample-task", priority="high")
        status = queue.get_status()
        assert status["queued_counts"]["total"] == 1
        assert queue.cancel(item.id)
        queue.record_failure(item, {"error": "config"})

    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    ok, errors = queue.validate_state()
    assert ok
    assert not errors
    assert queue.get_status()["queued_counts"]["total"] == 0
    assert len(queue.get_status()["failed_recent"]) == 1


def test_queue_mark_failed_includes_payload(tmp_path: Path, monkeypatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"

    with QueueManager(queue_file=queue_file, lock_file=lock_file) as queue:
        item = queue.enqueue("sample-task")
        running = queue.mark_running(item.id, pid=123)
        queue.mark_failed(running.id, {"error": "boom", "return_code": 1})

    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    status = queue.get_status()
    failure = status["failed_recent"][0]["error"]
    assert failure["return_code"] == 1


def test_queue_cancel_nonexistent(tmp_path: Path, monkeypatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    assert not queue.cancel("missing")


def test_queue_priority_ordering(tmp_path: Path, monkeypatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    # Create permissive config to avoid resource check failures in CI
    settings_path = tmp_path / "config.yaml"
    settings_path.write_text("queue:\n  cpu_percent: 99.0\n  memory_percent: 99.0\n")
    monkeypatch.setattr(settings_module, "_CACHE", None)

    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    with QueueManager(queue_file=queue_file, lock_file=lock_file) as queue:
        queue.enqueue("normal")
        queue.enqueue("urgent", priority="high")

    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    next_task = queue.get_next_task()
    assert next_task.priority == "high"
    assert next_task.name == "urgent"


def test_queue_clear_and_validate(tmp_path: Path, monkeypatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    queue.enqueue("one")
    queue.clear_queue()
    status = queue.get_status()
    assert status["queued_counts"]["total"] == 0

    duplicate = QueueItem(
        id="dup",
        name="dup-task",
        priority="normal",  # type: ignore[arg-type]
        enqueued_at="now",
    )
    queue._state.queued.append(duplicate)
    queue._state.queued.append(duplicate)
    ok, errors = queue.validate_state()
    assert not ok
    assert any("Duplicate" in error for error in errors)


def test_queue_requeue_with_delay(tmp_path: Path, monkeypatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    item = queue.enqueue("retry-me")
    queue.mark_running(item.id, pid=123)
    queue.requeue_with_delay(item, delay_seconds=30)
    status = queue.get_status()
    queued_item = status["queued"][0]
    assert queued_item["attempt"] == 1
    assert queued_item["not_before"] is not None


def test_resources_available_blocks(tmp_path: Path, monkeypatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    queue.enqueue("cpu-heavy")

    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 95.0)
    monkeypatch.setattr("psutil.virtual_memory", lambda: SimpleNamespace(percent=50.0))
    assert queue.get_next_task() is None

    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 10.0)
    assert queue.get_next_task().name == "cpu-heavy"


def test_corrupt_queue_file_recovers(tmp_path: Path) -> None:
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    queue_file.write_text("{not json}", encoding="utf-8")

    manager = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    status = manager.get_status()
    assert status["queued_counts"]["total"] == 0
    corrupt_files = list(tmp_path.glob("queue.corrupt-*"))
    if corrupt_files:
        assert corrupt_files[0].is_file()
