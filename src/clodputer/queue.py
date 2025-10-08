# Copyright (c) 2025 Rémy Olson
"""
Queue management for sequential task execution.

This module implements the Phase 1 requirements from the planning docs:
* Queue state persisted at ~/.clodputer/queue.json with atomic writes
* Sequential execution with optional high/normal priority
* Lock-file protection to prevent concurrent queue managers
* Basic diagnostics helpers for future `doctor` integration
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import psutil

from .metrics import metrics_summary
from .settings import load_settings

logger = logging.getLogger(__name__)

Priority = Literal["normal", "high"]

QUEUE_DIR = Path.home() / ".clodputer"
QUEUE_FILE = QUEUE_DIR / "queue.json"
LOCK_FILE = QUEUE_DIR / "clodputer.lock"


def ensure_queue_dir(path: Path = QUEUE_DIR) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _future_timestamp(seconds: int) -> str:
    future = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return future.isoformat().replace("+00:00", "Z")


@dataclass
class QueueItem:
    id: str
    name: str
    priority: Priority
    enqueued_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    not_before: Optional[str] = None
    attempt: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "priority": self.priority,
            "enqueued_at": self.enqueued_at,
            "metadata": self.metadata,
            "not_before": self.not_before,
            "attempt": self.attempt,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "QueueItem":
        return QueueItem(
            id=str(data["id"]),
            name=str(data["name"]),
            priority=data.get("priority", "normal"),  # type: ignore[return-value]
            enqueued_at=str(data.get("enqueued_at", _timestamp())),
            metadata=dict(data.get("metadata") or {}),
            not_before=data.get("not_before"),
            attempt=int(data.get("attempt", 0)),
        )


@dataclass
class RunningTask:
    id: str
    name: str
    pid: int
    started_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pid": self.pid,
            "started_at": self.started_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RunningTask":
        return RunningTask(
            id=str(data["id"]),
            name=str(data["name"]),
            pid=int(data["pid"]),
            started_at=str(data.get("started_at", _timestamp())),
        )


@dataclass
class QueueState:
    running: Optional[RunningTask] = None
    queued: List[QueueItem] = field(default_factory=list)
    completed: List[Dict[str, Any]] = field(default_factory=list)
    failed: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "running": self.running.to_dict() if self.running else None,
            "queued": [item.to_dict() for item in self.queued],
            "completed": self.completed,
            "failed": self.failed,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "QueueState":
        running = data.get("running")
        queued = data.get("queued") or []
        completed = data.get("completed") or []
        failed = data.get("failed") or []
        return QueueState(
            running=RunningTask.from_dict(running) if running else None,
            queued=[QueueItem.from_dict(item) for item in queued],
            completed=list(completed),
            failed=list(failed),
        )


class QueueCorruptionError(RuntimeError):
    """Raised when queue.json cannot be parsed or validated."""


class LockAcquisitionError(RuntimeError):
    """Raised when the lock file cannot be acquired."""


class QueueManager:
    """
    Manage sequential task execution with persistent state.

    This class is intentionally conservative: every state mutation is written to disk
    immediately using atomic rename semantics. For now there is no in-memory caching
    across instances; callers should create a single QueueManager instance when
    managing the queue within a process.
    """

    def __init__(
        self,
        queue_file: Path = QUEUE_FILE,
        lock_file: Path = LOCK_FILE,
        auto_lock: bool = True,
    ) -> None:
        ensure_queue_dir(queue_file.parent)
        self.queue_file = queue_file
        self.lock_file = lock_file
        self._state = self._load_state()
        self._lock_acquired = False
        self.settings = load_settings()
        self._last_resource_log: Optional[float] = None
        if self.settings.queue.max_parallel > 1:
            logger.info(
                "Queue max_parallel=%s requested but current executor operates sequentially.",
                self.settings.queue.max_parallel,
            )
        if auto_lock:
            self.acquire_lock()

    # ------------------------------------------------------------------
    # Lockfile management
    # ------------------------------------------------------------------
    def acquire_lock(self) -> None:
        if self._lock_acquired:
            return

        if self.lock_file.exists():
            try:
                existing_pid = int(self.lock_file.read_text().strip())
            except ValueError:
                existing_pid = -1

            if existing_pid > 0 and psutil.pid_exists(existing_pid):
                raise LockAcquisitionError(f"Clodputer queue already locked by PID {existing_pid}")

            logger.warning("Removing stale lock file at %s", self.lock_file)
            self.lock_file.unlink(missing_ok=True)

        self.lock_file.write_text(str(os.getpid()))
        self._lock_acquired = True

    def release_lock(self) -> None:
        if self._lock_acquired and self.lock_file.exists():
            self.lock_file.unlink(missing_ok=True)
        self._lock_acquired = False

    def __del__(self) -> None:  # pragma: no cover
        try:
            self.release_lock()
        except Exception:
            pass

    def __enter__(self) -> "QueueManager":
        self.acquire_lock()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release_lock()

    # ------------------------------------------------------------------
    # Queue operations
    # ------------------------------------------------------------------
    def enqueue(
        self,
        task_name: str,
        priority: Priority = "normal",
        metadata: Optional[Dict[str, Any]] = None,
        not_before: Optional[str] = None,
        attempt: int = 0,
    ) -> QueueItem:
        metadata = metadata or {}
        attempt = int(metadata.get("attempt", attempt))
        task_id = str(uuid.uuid4())
        item = QueueItem(
            id=task_id,
            name=task_name,
            priority=priority,
            enqueued_at=_timestamp(),
            metadata=metadata,
            not_before=not_before,
            attempt=attempt,
        )
        self._state.queued.append(item)
        self._state.queued = self._sorted_queue(self._state.queued)
        self._persist_state()
        logger.info("Enqueued task %s (%s)", item.name, item.id)
        return item

    def get_next_task(self) -> Optional[QueueItem]:
        if not self._state.queued:
            return None

        now = datetime.now(timezone.utc)
        for item in self._sorted_queue(self._state.queued):
            not_before = _parse_timestamp(item.not_before)
            if not_before and not_before > now:
                continue
            if not self._resources_available():
                return None
            return item
        return None

    def mark_running(self, task_id: str, pid: int) -> RunningTask:
        item, index = self._find_queue_item(task_id)
        if item is None:
            raise KeyError(f"Task {task_id} not found in queue")

        running = RunningTask(
            id=item.id,
            name=item.name,
            pid=pid,
            started_at=_timestamp(),
        )
        del self._state.queued[index]
        self._state.running = running
        self._persist_state()
        logger.info("Task %s (%s) marked running with pid %s", item.name, item.id, pid)
        return running

    def mark_completed(self, task_id: str, result: Dict[str, Any]) -> None:
        running = self._state.running
        if not running or running.id != task_id:
            raise KeyError(f"Task {task_id} is not the currently running task")

        entry = {
            "id": running.id,
            "name": running.name,
            "completed_at": _timestamp(),
            "result": result,
        }
        self._state.completed.append(entry)
        self._state.running = None
        self._persist_state()
        logger.info("Task %s (%s) marked completed", running.name, running.id)

    def mark_failed(self, task_id: str, error: Dict[str, Any]) -> None:
        running = self._state.running
        if not running or running.id != task_id:
            raise KeyError(f"Task {task_id} is not the currently running task")

        entry = {
            "id": running.id,
            "name": running.name,
            "failed_at": _timestamp(),
            "error": error,
        }
        self._state.failed.append(entry)
        self._state.running = None
        self._persist_state()
        logger.info("Task %s (%s) marked failed", running.name, running.id)

    def cancel(self, task_id: str) -> bool:
        item, index = self._find_queue_item(task_id)
        if item is None:
            return False
        del self._state.queued[index]
        self._persist_state()
        logger.info("Cancelled queued task %s (%s)", item.name, item.id)
        return True

    def record_failure(self, item: QueueItem, error: Dict[str, Any]) -> None:
        entry = {
            "id": item.id,
            "name": item.name,
            "failed_at": _timestamp(),
            "error": error,
            "attempt": item.attempt,
        }
        self._state.failed.append(entry)
        self._persist_state()

    def clear_queue(self) -> None:
        self._state.queued.clear()
        self._persist_state()
        logger.info("Cleared queued tasks")

    def requeue_with_delay(self, item: QueueItem, delay_seconds: int) -> None:
        item.attempt += 1
        item.not_before = _future_timestamp(delay_seconds)
        item.metadata = dict(item.metadata or {})
        item.metadata["attempt"] = item.attempt
        self._state.running = None
        self._state.queued.append(item)
        self._state.queued = self._sorted_queue(self._state.queued)
        self._persist_state()
        logger.info(
            "Scheduled retry for %s (%s) attempt %s in %ss",
            item.name,
            item.id,
            item.attempt,
            delay_seconds,
        )

    # ------------------------------------------------------------------
    # Diagnostics and status
    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._state.running.to_dict() if self._state.running else None,
            "queued": [item.to_dict() for item in self._sorted_queue(self._state.queued)],
            "queued_counts": {
                "total": len(self._state.queued),
                "high_priority": sum(1 for item in self._state.queued if item.priority == "high"),
            },
            "completed_recent": self._state.completed[-10:],
            "failed_recent": self._state.failed[-10:],
            "metrics": metrics_summary(),
        }

    def validate_state(self) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        seen_ids = set()
        for item in self._state.queued:
            if item.id in seen_ids:
                errors.append(f"Duplicate queued task id {item.id}")
            seen_ids.add(item.id)
            if item.priority not in ("high", "normal"):
                errors.append(f"Invalid priority for {item.id}: {item.priority}")
        running = self._state.running
        if running and running.id in seen_ids:
            errors.append(f"Task {running.id} appears queued and running")
        return (len(errors) == 0, errors)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _find_queue_item(self, task_id: str) -> Tuple[Optional[QueueItem], Optional[int]]:
        for index, item in enumerate(self._state.queued):
            if item.id == task_id:
                return item, index
        return None, None

    @staticmethod
    def _sorted_queue(items: List[QueueItem]) -> List[QueueItem]:
        return sorted(
            items,
            key=lambda i: (
                0 if i.priority == "high" else 1,
                _parse_timestamp(i.not_before) or datetime.min.replace(tzinfo=timezone.utc),
                i.enqueued_at,
            ),
        )

    def _resources_available(self) -> bool:
        thresholds = self.settings.queue
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory().percent
        if cpu > thresholds.cpu_percent or memory > thresholds.memory_percent:
            now = time.monotonic()
            if not self._last_resource_log or now - self._last_resource_log > 30:
                logger.info(
                    "Resource thresholds exceeded (cpu %.1f%%, mem %.1f%%); deferring execution",
                    cpu,
                    memory,
                )
                self._last_resource_log = now
            return False
        return True

    def _load_state(self) -> QueueState:
        if not self.queue_file.exists():
            return QueueState()

        try:
            data = json.loads(self.queue_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load queue state (%s). Attempting recovery.", exc)
            self._archive_corrupt_state(exc)
            return QueueState()

        if not isinstance(data, dict):
            raise QueueCorruptionError("Queue file malformed: expected object at top level")
        return QueueState.from_dict(data)

    def _persist_state(self) -> None:
        serialized = json.dumps(self._state.to_dict(), indent=2, sort_keys=True)
        tmp_dir = self.queue_file.parent if self.queue_file.parent.exists() else QUEUE_DIR

        with tempfile.NamedTemporaryFile("w", dir=tmp_dir, delete=False) as tmp:
            tmp.write(serialized)
            tmp_path = Path(tmp.name)

        # Verify file readability before atomic replace
        json.loads(tmp_path.read_text(encoding="utf-8"))
        tmp_path.replace(self.queue_file)
        logger.debug("Persisted queue state to %s", self.queue_file)

    def _archive_corrupt_state(self, exc: Exception) -> None:
        timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
        corrupt_path = self.queue_file.with_suffix(f".corrupt-{timestamp}")
        try:
            self.queue_file.rename(corrupt_path)
            logger.warning(
                "Corrupted queue.json moved to %s; a new queue will be created.",
                corrupt_path,
            )
        except OSError:
            logger.error("Unable to archive corrupt queue file; continuing with empty queue.")
            raise QueueCorruptionError(f"Failed to load queue state: {exc}") from exc


def lockfile_status(lock_file: Path = LOCK_FILE) -> Dict[str, Any]:
    """
    Report on the current lock file status for diagnostics.
    """
    if not lock_file.exists():
        return {"locked": False, "pid": None, "stale": False}
    try:
        pid = int(lock_file.read_text().strip())
    except ValueError:
        return {"locked": True, "pid": None, "stale": True}
    is_running = psutil.pid_exists(pid)
    return {
        "locked": True,
        "pid": pid,
        "stale": not is_running,
    }


__all__ = [
    "QueueManager",
    "QueueCorruptionError",
    "LockAcquisitionError",
    "QueueItem",
    "RunningTask",
    "QueueState",
    "lockfile_status",
]
