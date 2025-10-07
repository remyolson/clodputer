# Copyright (c) 2025 Rémy Olson
"""
File watcher daemon for Clodputer.

Uses watchdog to monitor directories defined in task configurations and enqueue
tasks when matching file events occur. Supports foreground execution as well as
a lightweight daemon controlled via PID file.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import signal
import threading
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import psutil
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from .config import TaskConfig, validate_all_tasks
from .queue import QueueManager, ensure_queue_dir

WATCHER_LOG_FILE = Path.home() / ".clodputer" / "watcher.log"
WATCHER_PID_FILE = Path.home() / ".clodputer" / "watcher.pid"


class WatcherError(RuntimeError):
    """Raised when watcher setup or management fails."""


def file_watch_tasks(configs: Iterable[TaskConfig]) -> List[TaskConfig]:
    return [
        task
        for task in configs
        if task.enabled and task.trigger and task.trigger.type == "file_watch"
    ]


def _get_logger() -> logging.Logger:
    ensure_queue_dir(WATCHER_LOG_FILE.parent)
    logger = logging.getLogger("clodputer.watcher")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(WATCHER_LOG_FILE, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class TaskEventHandler(PatternMatchingEventHandler):
    def __init__(self, task: TaskConfig, logger: logging.Logger) -> None:
        trigger = task.trigger
        assert trigger is not None and trigger.type == "file_watch"
        patterns = [trigger.pattern or "*"]
        super().__init__(patterns=patterns, ignore_directories=True)
        self.task = task
        self.logger = logger
        self.debounce_seconds = (trigger.debounce or 1000) / 1000.0
        self.expected_event = trigger.event
        self._last_emitted: Dict[str, float] = {}

    def _should_emit(self, path: str) -> bool:
        now = time.monotonic()
        last = self._last_emitted.get(path, 0.0)
        if now - last < self.debounce_seconds:
            return False
        self._last_emitted[path] = now
        return True

    def _enqueue(self, event_type: str, path: str) -> None:
        if not self._should_emit(path):
            return
        metadata = {
            "trigger": "file_watch",
            "event": event_type,
            "path": path,
        }
        with QueueManager() as queue:
            queue.enqueue(self.task.name, priority=self.task.priority, metadata=metadata)
        self.logger.info("Enqueued task %s for %s (%s)", self.task.name, event_type, path)

    def on_created(self, event) -> None:  # type: ignore[override]
        if self.expected_event == "created":
            self._enqueue("created", event.src_path)

    def on_modified(self, event) -> None:  # type: ignore[override]
        if self.expected_event == "modified":
            self._enqueue("modified", event.src_path)

    def on_deleted(self, event) -> None:  # type: ignore[override]
        if self.expected_event == "deleted":
            self._enqueue("deleted", event.src_path)


def run_watch_service(
    tasks: Sequence[TaskConfig], stop_event: Optional[threading.Event] = None
) -> None:
    logger = _get_logger()
    if not tasks:
        raise WatcherError("No file watcher tasks configured")

    observer = Observer()
    scheduled = 0

    for task in tasks:
        trigger = task.trigger
        assert trigger is not None and trigger.type == "file_watch"
        path = Path(trigger.path).expanduser()
        if not path.exists():
            logger.warning("Watch path does not exist for task %s: %s", task.name, path)
            continue

        handler = TaskEventHandler(task, logger)
        observer.schedule(handler, str(path), recursive=False)
        logger.info(
            "Watching %s for task %s (pattern=%s, event=%s, debounce=%sms)",
            path,
            task.name,
            trigger.pattern,
            trigger.event,
            trigger.debounce,
        )
        scheduled += 1

    if scheduled == 0:
        raise WatcherError("No valid watch directories were scheduled")

    observer.start()
    logger.info("File watcher service started")

    try:
        while not (stop_event and stop_event.is_set()):
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("File watcher interrupted by user")
    finally:
        observer.stop()
        observer.join()
        logger.info("File watcher service stopped")


def _daemon_loop() -> None:
    logger = _get_logger()
    stop_event = threading.Event()

    def _handle_signal(signum, frame):
        logger.info("Received signal %s; stopping watcher daemon", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    while not stop_event.is_set():
        configs, errors = validate_all_tasks()
        if errors:
            for path, error in errors:
                logger.error("Invalid task config %s: %s", path, error)
        tasks = file_watch_tasks(configs)
        if not tasks:
            logger.info("No file watcher tasks configured; sleeping 60 seconds")
            for _ in range(60):
                if stop_event.is_set():
                    break
                time.sleep(1)
            continue

        try:
            run_watch_service(tasks, stop_event=stop_event)
        except WatcherError as exc:
            logger.warning("%s; retrying in 30 seconds", exc)
            for _ in range(30):
                if stop_event.is_set():
                    break
                time.sleep(1)
        else:
            break  # run_watch_service exited normally (stop_event triggered)


def start_daemon() -> int:
    if is_daemon_running():
        raise WatcherError("Watcher daemon already running")

    ensure_queue_dir(WATCHER_PID_FILE.parent)

    process = multiprocessing.Process(target=_daemon_loop, daemon=False)
    process.start()
    WATCHER_PID_FILE.write_text(str(process.pid), encoding="utf-8")
    return process.pid


def stop_daemon(timeout: float = 5.0) -> bool:
    if not WATCHER_PID_FILE.exists():
        return False
    pid = int(WATCHER_PID_FILE.read_text())
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass

    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_daemon_running():
            break
        time.sleep(0.1)

    WATCHER_PID_FILE.unlink(missing_ok=True)
    return True


def is_daemon_running() -> bool:
    if not WATCHER_PID_FILE.exists():
        return False
    try:
        pid = int(WATCHER_PID_FILE.read_text())
    except ValueError:
        return False
    return psutil.pid_exists(pid)


def watcher_status() -> dict:
    return {
        "running": is_daemon_running(),
        "pid": int(WATCHER_PID_FILE.read_text()) if WATCHER_PID_FILE.exists() else None,
        "log_file": str(WATCHER_LOG_FILE),
    }


__all__ = [
    "WatcherError",
    "file_watch_tasks",
    "run_watch_service",
    "start_daemon",
    "stop_daemon",
    "is_daemon_running",
    "watcher_status",
    "WATCHER_LOG_FILE",
    "WATCHER_PID_FILE",
]
