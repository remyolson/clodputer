# Copyright (c) 2025 Rémy Olson
"""
Structured logging for Clodputer executions.

Writes JSON lines to ~/.clodputer/execution.log and rotates logs when they grow
larger than 10 MB, archiving them under ~/.clodputer/archive/YYYY-MM.log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .queue import ensure_queue_dir

LOG_DIR = Path.home() / ".clodputer"
LOG_FILE = LOG_DIR / "execution.log"
ARCHIVE_DIR = LOG_DIR / "archive"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
ARCHIVE_RETAIN_COUNT = 6


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _ensure_paths() -> None:
    ensure_queue_dir(LOG_DIR)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def _rotate_logs_if_needed() -> None:
    if not LOG_FILE.exists():
        return
    if LOG_FILE.stat().st_size < MAX_LOG_SIZE:
        return
    _ensure_paths()
    archive_name = datetime.now(timezone.utc).strftime("%Y-%m") + ".log"
    destination = ARCHIVE_DIR / archive_name
    if destination.exists():
        destination = ARCHIVE_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%S')}.log"
    LOG_FILE.replace(destination)
    _prune_archives()


def _prune_archives(retain: int = ARCHIVE_RETAIN_COUNT) -> None:
    if not ARCHIVE_DIR.exists():
        return
    archives = sorted(ARCHIVE_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in archives[retain:]:
        try:
            stale.unlink()
        except OSError:
            continue


def _write_json_line(record: Dict[str, Any]) -> None:
    _ensure_paths()
    _rotate_logs_if_needed()
    record.setdefault("timestamp", _timestamp())
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


@dataclass
class StructuredLogger:
    hostname: Optional[str] = None
    log_version: str = "1.0"

    def _base_record(self, event: str) -> Dict[str, Any]:
        record: Dict[str, Any] = {"event": event, "log_version": self.log_version}
        if self.hostname:
            record["host"] = self.hostname
        return record

    @staticmethod
    def _clean_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in payload.items() if v is not None}

    def task_started(self, task_id: str, task_name: str, metadata: Dict[str, Any]) -> None:
        record = self._base_record("task_started")
        record.update(
            {
                "task_id": task_id,
                "task_name": task_name,
                "metadata": metadata,
            }
        )
        _write_json_line(record)

    def task_completed(
        self,
        task_id: str,
        task_name: str,
        result: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> None:
        record = self._base_record("task_completed")
        record.update(
            {
                "task_id": task_id,
                "task_name": task_name,
                "result": self._clean_payload(result),
                "metadata": metadata,
            }
        )
        _write_json_line(record)

    def task_failed(
        self,
        task_id: str,
        task_name: str,
        error: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> None:
        record = self._base_record("task_failed")
        record.update(
            {
                "task_id": task_id,
                "task_name": task_name,
                "error": self._clean_payload(error),
                "metadata": metadata,
            }
        )
        _write_json_line(record)


def iter_events(limit: Optional[int] = None, reverse: bool = False) -> Iterator[Dict[str, Any]]:
    if not LOG_FILE.exists():
        return
    with LOG_FILE.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    if reverse:
        lines = list(reversed(lines))
    count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        yield record
        count += 1
        if limit is not None and count >= limit:
            break


def tail_events(limit: int = 10) -> List[Dict[str, Any]]:
    return list(iter_events(limit=limit, reverse=True))[::-1]


def read_all_events() -> List[Dict[str, Any]]:
    return list(iter_events())


__all__ = [
    "StructuredLogger",
    "iter_events",
    "tail_events",
    "read_all_events",
    "LOG_FILE",
    "ARCHIVE_DIR",
]
