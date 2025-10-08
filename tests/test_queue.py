from __future__ import annotations

from pathlib import Path

from clodputer.queue import QueueItem, QueueManager


def test_queue_enqueue_and_record_failure(tmp_path: Path) -> None:
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


def test_queue_mark_failed_includes_payload(tmp_path: Path) -> None:
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


def test_queue_cancel_nonexistent(tmp_path: Path) -> None:
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    assert not queue.cancel("missing")


def test_queue_priority_ordering(tmp_path: Path) -> None:
    queue_file = tmp_path / "queue.json"
    lock_file = tmp_path / "queue.lock"
    with QueueManager(queue_file=queue_file, lock_file=lock_file) as queue:
        queue.enqueue("normal")
        queue.enqueue("urgent", priority="high")

    queue = QueueManager(queue_file=queue_file, lock_file=lock_file, auto_lock=False)
    next_task = queue.get_next_task()
    assert next_task.priority == "high"
    assert next_task.name == "urgent"


def test_queue_clear_and_validate(tmp_path: Path) -> None:
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
