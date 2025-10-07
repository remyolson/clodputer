from __future__ import annotations

from pathlib import Path

from clodputer.logger import LOG_FILE, StructuredLogger, iter_events, tail_events


def test_structured_logger_writes_events(tmp_path: Path, monkeypatch) -> None:
    log_dir = tmp_path / ".clodputer"
    monkeypatch.setattr("clodputer.logger.LOG_DIR", log_dir)
    monkeypatch.setattr("clodputer.logger.LOG_FILE", log_dir / "execution.log")
    monkeypatch.setattr("clodputer.logger.ARCHIVE_DIR", log_dir / "archive")

    logger = StructuredLogger(hostname="test-host")
    logger.task_started("task-1", "sample", {"priority": "high"})
    logger.task_completed("task-1", "sample", {"duration": 1.2}, {"priority": "high"})

    events = list(iter_events())
    assert len(events) == 2
    assert events[0]["event"] == "task_started"
    assert events[1]["event"] == "task_completed"

    recent = tail_events(limit=1)
    assert recent and recent[0]["event"] == "task_completed"
