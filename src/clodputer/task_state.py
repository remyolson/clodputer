"""Task state tracking for catch-up behavior and execution history."""

from __future__ import annotations

import json
import time
from typing import Optional

from .queue import QUEUE_DIR

TASK_STATE_FILE = QUEUE_DIR / "task_state.json"
TASK_STATE_BACKUP_SUFFIX = ".backup"


class TaskState:
    """Track execution state for a single task."""

    def __init__(
        self,
        last_run: Optional[str] = None,
        last_success: Optional[str] = None,
        next_expected: Optional[str] = None,
    ):
        """Initialize task state.

        Args:
            last_run: ISO 8601 timestamp of last execution attempt
            last_success: ISO 8601 timestamp of last successful execution
            next_expected: ISO 8601 timestamp of next expected run
        """
        self.last_run = last_run
        self.last_success = last_success
        self.next_expected = next_expected

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "last_run": self.last_run,
            "last_success": self.last_success,
            "next_expected": self.next_expected,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TaskState:
        """Create TaskState from dictionary."""
        return cls(
            last_run=data.get("last_run"),
            last_success=data.get("last_success"),
            next_expected=data.get("next_expected"),
        )


def load_task_states() -> dict[str, TaskState]:
    """Load task states from disk.

    Returns:
        Dictionary mapping task name to TaskState.
        Returns empty dict if file doesn't exist or is corrupted.
    """
    if not TASK_STATE_FILE.exists():
        return {}

    try:
        with TASK_STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        states = {}
        for task_name, state_dict in data.items():
            states[task_name] = TaskState.from_dict(state_dict)
        return states

    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        # Corrupted file - move to backup and return empty
        _backup_corrupted_state()
        return {}


def save_task_states(states: dict[str, TaskState]) -> None:
    """Save task states to disk.

    Args:
        states: Dictionary mapping task name to TaskState.
    """
    TASK_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Convert to serializable format
    data = {name: state.to_dict() for name, state in states.items()}

    try:
        # Write atomically using temp file
        temp_path = TASK_STATE_FILE.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.flush()

        # Atomic rename
        temp_path.replace(TASK_STATE_FILE)

    except OSError:
        # Clean up temp file on error
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def get_task_state(task_name: str) -> Optional[TaskState]:
    """Get state for a specific task.

    Args:
        task_name: Name of the task.

    Returns:
        TaskState if found, None otherwise.
    """
    states = load_task_states()
    return states.get(task_name)


def update_task_state(task_name: str, **updates) -> None:
    """Update state for a specific task.

    Args:
        task_name: Name of the task.
        **updates: Fields to update (last_run, last_success, next_expected).

    Example:
        >>> update_task_state("daily-email", last_run="2025-10-09T08:00:01Z")
    """
    states = load_task_states()

    if task_name not in states:
        states[task_name] = TaskState()

    state = states[task_name]

    # Update fields
    if "last_run" in updates:
        state.last_run = updates["last_run"]
    if "last_success" in updates:
        state.last_success = updates["last_success"]
    if "next_expected" in updates:
        state.next_expected = updates["next_expected"]

    save_task_states(states)


def record_task_execution(
    task_name: str, success: bool, next_expected: Optional[str] = None
) -> None:
    """Record a task execution.

    Args:
        task_name: Name of the task.
        success: Whether the execution succeeded.
        next_expected: ISO 8601 timestamp of next expected run (optional).
    """
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    updates = {"last_run": timestamp}
    if success:
        updates["last_success"] = timestamp
    if next_expected:
        updates["next_expected"] = next_expected

    update_task_state(task_name, **updates)


def _backup_corrupted_state() -> None:
    """Move corrupted state file to backup."""
    if not TASK_STATE_FILE.exists():
        return

    try:
        backup_path = TASK_STATE_FILE.with_suffix(f"{TASK_STATE_BACKUP_SUFFIX}.corrupted")
        TASK_STATE_FILE.rename(backup_path)
    except OSError:
        # If backup fails, just delete the corrupted file
        try:
            TASK_STATE_FILE.unlink()
        except OSError:
            pass


__all__ = [
    "TaskState",
    "load_task_states",
    "save_task_states",
    "get_task_state",
    "update_task_state",
    "record_task_execution",
    "TASK_STATE_FILE",
]
