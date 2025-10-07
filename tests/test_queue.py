from __future__ import annotations

from pathlib import Path

from clodputer.queue import QueueManager


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
