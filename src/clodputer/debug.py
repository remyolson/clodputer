# Copyright (c) 2025 Rémy Olson
"""
Debug logging infrastructure for Clodputer.

Provides structured debug logging with:
- JSON-formatted logs to ~/.clodputer/debug.log
- Module and function context tracking
- Timing and performance metrics
- Sanitized output (no sensitive data)
- Log rotation (10MB limit)
- Context managers for enter/exit patterns

Usage:
    from clodputer.debug import debug_logger

    debug_logger.info("operation_started", task_name="daily-email")

    with debug_logger.context("execute_task", task_id="abc-123"):
        # Your code here
        debug_logger.subprocess("claude_cli_start", command="claude -p ...", pid=12345)
"""

from __future__ import annotations

import inspect
import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Literal, Optional

DEBUG_DIR = Path.home() / ".clodputer"
DEBUG_LOG_FILE = DEBUG_DIR / "debug.log"


def _ensure_debug_dir() -> None:
    """Ensure debug directory exists."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)


MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_BACKUPS = 3

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

# Global flag to enable/disable debug logging
_debug_enabled = False


def enable_debug_logging() -> None:
    """Enable debug logging globally."""
    global _debug_enabled
    _debug_enabled = True


def disable_debug_logging() -> None:
    """Disable debug logging globally."""
    global _debug_enabled
    _debug_enabled = False


def is_debug_enabled() -> bool:
    """Check if debug logging is enabled."""
    return _debug_enabled


def _sanitize_value(value: Any) -> Any:
    """Sanitize potentially sensitive data from log output.

    Replaces home directory paths with ~ and truncates long strings.
    """
    if isinstance(value, str):
        # Replace home directory with tilde
        home = str(Path.home())
        if home in value:
            value = value.replace(home, "~")

        # Truncate very long strings
        if len(value) > 500:
            value = value[:500] + f"... (truncated, {len(value)} chars total)"

        return value

    elif isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}

    elif isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value]

    elif isinstance(value, Path):
        return _sanitize_value(str(value))

    return value


def _get_caller_info() -> tuple[str, str, int]:
    """Get module, function, and line number of the caller.

    Returns:
        Tuple of (module_name, function_name, line_number)
    """
    frame = inspect.currentframe()
    if frame is None:
        return "unknown", "unknown", 0

    # Walk up the stack to find the first frame outside this module
    try:
        caller_frame = frame.f_back
        if caller_frame is not None:
            caller_frame = caller_frame.f_back  # Skip one more level

        if caller_frame is None:
            return "unknown", "unknown", 0

        module_name = caller_frame.f_globals.get("__name__", "unknown")
        function_name = caller_frame.f_code.co_name
        line_number = caller_frame.f_lineno

        # Strip package prefix for cleaner logs
        if module_name.startswith("clodputer."):
            module_name = module_name[len("clodputer.") :]

        return module_name, function_name, line_number
    finally:
        del frame


def _rotate_if_needed() -> None:
    """Rotate debug log if it exceeds size limit."""
    if not DEBUG_LOG_FILE.exists():
        return

    try:
        size = DEBUG_LOG_FILE.stat().st_size
        if size <= MAX_LOG_SIZE:
            return

        # Rotate existing backups
        for i in range(MAX_BACKUPS - 1, 0, -1):
            old_backup = DEBUG_LOG_FILE.parent / f"{DEBUG_LOG_FILE.name}.{i}"
            new_backup = DEBUG_LOG_FILE.parent / f"{DEBUG_LOG_FILE.name}.{i + 1}"

            if i == MAX_BACKUPS - 1 and new_backup.exists():
                new_backup.unlink()

            if old_backup.exists():
                old_backup.rename(new_backup)

        # Move current log to .1
        backup_path = DEBUG_LOG_FILE.parent / f"{DEBUG_LOG_FILE.name}.1"
        DEBUG_LOG_FILE.rename(backup_path)

    except OSError:
        # Non-fatal if rotation fails
        pass


class DebugLogger:
    """Structured debug logger with context tracking.

    Phase 1 Improvements:
    - Operation IDs for correlating related logs
    - Human-readable descriptions with emoji markers
    - Tags for filtering and searching
    - Summaries for large data objects
    - Elapsed time tracking from operation start
    """

    def __init__(self) -> None:
        self._context_stack: list[dict[str, Any]] = []
        self._operation_start_time: Optional[float] = None

    def _write_log(
        self,
        level: LogLevel,
        event: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[Dict[str, Any]] = None,
        marker: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Write a structured log entry.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            event: Event name/type (technical identifier)
            description: Human-readable description with emoji (Phase 1)
            tags: List of tags for filtering (Phase 1)
            summary: Key metrics summary dict (Phase 1)
            marker: Emoji marker for quick scanning (Phase 1)
            **kwargs: Additional context to log
        """
        if not _debug_enabled:
            return

        _ensure_debug_dir()
        _rotate_if_needed()

        module, function, line = _get_caller_info()

        record = {
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": level,
            "module": module,
            "function": function,
            "line": line,
            "event": event,
        }

        # Add Phase 1 fields
        if description:
            record["description"] = description
        if marker:
            record["marker"] = marker
        if tags:
            record["tags"] = tags
        if summary:
            record["summary"] = summary

        # Add operation_id and elapsed time from context
        if self._context_stack:
            context = self._context_stack[-1].copy()
            record["context"] = context

            # Extract operation_id if present
            if "operation_id" in context:
                record["operation_id"] = context["operation_id"]

            # Calculate elapsed time if operation has started
            if self._operation_start_time is not None:
                record["elapsed"] = round(time.monotonic() - self._operation_start_time, 3)

        # Add additional data
        if kwargs:
            record["data"] = _sanitize_value(kwargs)

        try:
            with DEBUG_LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            # Fail silently - don't break the application if logging fails
            pass

    def debug(
        self,
        event: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[Dict[str, Any]] = None,
        marker: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log a DEBUG level event with Phase 1 enhancements."""
        self._write_log("DEBUG", event, description, tags, summary, marker, **kwargs)

    def info(
        self,
        event: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[Dict[str, Any]] = None,
        marker: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log an INFO level event with Phase 1 enhancements."""
        self._write_log("INFO", event, description, tags, summary, marker, **kwargs)

    def warning(
        self,
        event: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[Dict[str, Any]] = None,
        marker: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log a WARNING level event with Phase 1 enhancements."""
        self._write_log("WARNING", event, description, tags, summary, marker, **kwargs)

    def error(
        self,
        event: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[Dict[str, Any]] = None,
        marker: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log an ERROR level event with Phase 1 enhancements."""
        self._write_log("ERROR", event, description, tags, summary, marker, **kwargs)

    @contextmanager
    def context(
        self,
        operation: str,
        operation_id: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> Iterator[None]:
        """Context manager for tracking operation lifecycle.

        Logs operation start/end with timing and Phase 1 enhancements.

        Usage:
            with debug_logger.context(
                "execute_task",
                operation_id="task-abc123",
                description="🚀 Executing daily email task",
                tags=["task", "execution"],
                task_id="abc-123"
            ):
                # Your code here
                pass

        Args:
            operation: Name of the operation (technical identifier)
            operation_id: Unique ID to correlate logs (auto-generated if not provided)
            description: Human-readable description with emoji
            tags: Tags for filtering
            **kwargs: Context data to track
        """
        # Generate operation_id if not provided
        if operation_id is None:
            operation_id = f"{operation}-{uuid.uuid4().hex[:8]}"

        context_data = {"operation": operation, "operation_id": operation_id, **kwargs}
        self._context_stack.append(context_data)

        # Start elapsed timer on first context
        if self._operation_start_time is None:
            self._operation_start_time = time.monotonic()

        start_time = time.monotonic()

        # Determine marker based on operation type
        marker = "🚀"  # Default for operation start

        self.info(
            f"{operation}_started",
            description=description or f"{marker} {operation.replace('_', ' ').title()} started",
            tags=tags or [operation, "start"],
            **kwargs,
        )

        try:
            yield
        except Exception as exc:
            duration = time.monotonic() - start_time
            self.error(
                f"{operation}_failed",
                description=f"❌ {operation.replace('_', ' ').title()} failed",
                tags=tags or [operation, "error", "failed"],
                summary={"duration": f"{duration:.1f}s", "error": type(exc).__name__},
                duration=duration,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise
        else:
            duration = time.monotonic() - start_time
            self.info(
                f"{operation}_completed",
                description=f"✅ {operation.replace('_', ' ').title()} completed",
                tags=tags or [operation, "completed", "success"],
                summary={"duration": f"{duration:.1f}s"},
                duration=duration,
            )
        finally:
            self._context_stack.pop()

            # Reset operation start time when we exit all contexts
            if not self._context_stack:
                self._operation_start_time = None

    def subprocess(
        self,
        event: str,
        command: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Log subprocess-related events with Phase 1 enhancements.

        Args:
            event: Event name (e.g., "subprocess_started", "subprocess_output")
            command: Command being executed
            description: Human-readable description with emoji
            tags: Tags for filtering (auto-adds "subprocess")
            summary: Key metrics summary
            **kwargs: Additional context (pid, stdout, stderr, etc.)
        """
        # Sanitize command to avoid leaking sensitive args
        sanitized_command = command
        if len(command) > 200:
            sanitized_command = command[:200] + "... (truncated)"

        # Auto-add subprocess tag
        if tags is None:
            tags = ["subprocess"]
        elif "subprocess" not in tags:
            tags = ["subprocess"] + tags

        self.info(
            event,
            description=description,
            tags=tags,
            summary=summary,
            marker="🔌",
            command=sanitized_command,
            **kwargs,
        )

    def state_change(
        self,
        event: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Log state changes (queue, config, etc.) with Phase 1 enhancements.

        Args:
            event: State change event name
            description: Human-readable description with emoji
            tags: Tags for filtering (auto-adds "state")
            summary: Key metrics summary
            **kwargs: State details
        """
        # Auto-add state tag
        if tags is None:
            tags = ["state"]
        elif "state" not in tags:
            tags = ["state"] + tags

        self.info(event, description=description, tags=tags, summary=summary, marker="💾", **kwargs)


# Global singleton instance
debug_logger = DebugLogger()


__all__ = [
    "debug_logger",
    "enable_debug_logging",
    "disable_debug_logging",
    "is_debug_enabled",
    "DEBUG_LOG_FILE",
]
