from __future__ import annotations

from pathlib import Path
import os

from clodputer import logger as logger_module
from clodputer.logger import StructuredLogger, iter_events, tail_events, _prune_archives


def _configure_logger_paths(tmp_path: Path, monkeypatch) -> Path:
    log_dir = tmp_path / ".clodputer"
    archive_dir = log_dir / "archive"
    log_file = log_dir / "execution.log"
    monkeypatch.setattr(logger_module, "LOG_DIR", log_dir)
    monkeypatch.setattr(logger_module, "LOG_FILE", log_file)
    monkeypatch.setattr(logger_module, "ARCHIVE_DIR", archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def test_structured_logger_writes_events(tmp_path: Path, monkeypatch) -> None:
    _configure_logger_paths(tmp_path, monkeypatch)

    logger = StructuredLogger(hostname="test-host")
    logger.task_started("task-1", "sample", {"priority": "high"})
    logger.task_completed(
        "task-1",
        "sample",
        {"duration": 1.2, "return_code": 0, "result": {"ok": True}, "parse_error": None},
        {"priority": "high"},
    )
    logger.task_failed(
        "task-2",
        "sample",
        {"error": "boom", "return_code": 1, "stderr": "oops"},
        {"stage": "execute"},
    )

    events = list(iter_events())
    assert len(events) == 3
    assert events[1]["event"] == "task_completed"
    assert events[1]["result"]["return_code"] == 0
    assert "parse_error" not in events[1]["result"]
    assert events[2]["error"]["return_code"] == 1

    recent = tail_events(limit=1)
    assert recent and recent[0]["event"] == "task_failed"


def test_prune_archives_retains_recent(tmp_path: Path, monkeypatch) -> None:
    _configure_logger_paths(tmp_path, monkeypatch)
    archive_dir = logger_module.ARCHIVE_DIR
    for idx in range(5):
        f = archive_dir / f"2025-0{idx+1}.log"
        f.write_text("dummy")
        os.utime(f, (idx, idx))

    _prune_archives(retain=3)
    remaining = sorted(archive_dir.glob("*.log"))
    assert len(remaining) == 3


def test_read_all_events(tmp_path: Path, monkeypatch) -> None:
    _configure_logger_paths(tmp_path, monkeypatch)
    logger_instance = StructuredLogger()
    logger_instance.task_started("task-1", "sample", {})
    logger_instance.task_failed(
        "task-1",
        "sample",
        {"error": "boom", "return_code": 2, "stdout": "raw"},
        {},
    )

    events = logger_module.read_all_events()
    assert len(events) == 2
    assert events[-1]["error"]["stdout"] == "raw"
