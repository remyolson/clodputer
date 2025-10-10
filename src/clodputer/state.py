# Copyright (c) 2025 Rémy Olson
"""
Task state persistence and management.

Enables tasks to store and retrieve state between executions, allowing for
stateful automation workflows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

STATE_DIR = Path.home() / ".clodputer" / "state"
MAX_STATE_SIZE = 1024 * 1024  # 1MB max per task state


class StateError(RuntimeError):
    """Raised when state operations fail."""


def ensure_state_dir(path: Path = STATE_DIR) -> None:
    """Ensure state directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def get_state_path(task_name: str, state_dir: Path = STATE_DIR) -> Path:
    """Get the state file path for a task."""
    return state_dir / f"{task_name}.json"


def load_state(task_name: str, state_dir: Path = STATE_DIR) -> Dict[str, Any]:
    """Load state for a task.

    Args:
        task_name: Name of the task
        state_dir: Directory where state files are stored

    Returns:
        Dictionary containing task state, or empty dict if no state exists

    Raises:
        StateError: If state file is corrupted or too large
    """
    ensure_state_dir(state_dir)
    state_path = get_state_path(task_name, state_dir)

    if not state_path.exists():
        return {}

    try:
        # Check file size
        file_size = state_path.stat().st_size
        if file_size > MAX_STATE_SIZE:
            raise StateError(
                f"State file for '{task_name}' is too large ({file_size} bytes, max {MAX_STATE_SIZE})"
            )

        # Load and parse JSON
        content = state_path.read_text(encoding="utf-8")
        state = json.loads(content)

        if not isinstance(state, dict):
            raise StateError(
                f"State for '{task_name}' must be a JSON object, got {type(state).__name__}"
            )

        return state

    except json.JSONDecodeError as exc:
        raise StateError(f"Corrupted state file for '{task_name}': {exc}") from exc
    except OSError as exc:
        raise StateError(f"Failed to read state for '{task_name}': {exc}") from exc


def save_state(task_name: str, state: Dict[str, Any], state_dir: Path = STATE_DIR) -> Path:
    """Save state for a task.

    Args:
        task_name: Name of the task
        state: Dictionary containing state to save
        state_dir: Directory where state files are stored

    Returns:
        Path to the saved state file

    Raises:
        StateError: If state is invalid or save fails
    """
    if not isinstance(state, dict):
        raise StateError(f"State must be a dictionary, got {type(state).__name__}")

    ensure_state_dir(state_dir)
    state_path = get_state_path(task_name, state_dir)

    try:
        # Serialize to JSON
        content = json.dumps(state, indent=2, ensure_ascii=False)

        # Check size
        if len(content.encode("utf-8")) > MAX_STATE_SIZE:
            raise StateError(
                f"State for '{task_name}' exceeds maximum size of {MAX_STATE_SIZE} bytes"
            )

        # Write atomically
        temp_path = state_path.with_suffix(".tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(state_path)

        return state_path

    except OSError as exc:
        raise StateError(f"Failed to save state for '{task_name}': {exc}") from exc


def update_state(
    task_name: str,
    updates: Dict[str, Any],
    state_dir: Path = STATE_DIR,
) -> Dict[str, Any]:
    """Update specific fields in task state.

    Args:
        task_name: Name of the task
        updates: Dictionary of fields to update
        state_dir: Directory where state files are stored

    Returns:
        The updated complete state

    Raises:
        StateError: If update fails
    """
    current_state = load_state(task_name, state_dir)
    current_state.update(updates)
    save_state(task_name, current_state, state_dir)
    return current_state


def delete_state(task_name: str, state_dir: Path = STATE_DIR) -> bool:
    """Delete state for a task.

    Args:
        task_name: Name of the task
        state_dir: Directory where state files are stored

    Returns:
        True if state was deleted, False if no state existed

    Raises:
        StateError: If deletion fails
    """
    ensure_state_dir(state_dir)
    state_path = get_state_path(task_name, state_dir)

    if not state_path.exists():
        return False

    try:
        state_path.unlink()
        return True
    except OSError as exc:
        raise StateError(f"Failed to delete state for '{task_name}': {exc}") from exc


def list_states(state_dir: Path = STATE_DIR) -> Dict[str, Dict[str, Any]]:
    """List all task states.

    Args:
        state_dir: Directory where state files are stored

    Returns:
        Dictionary mapping task names to their states
    """
    ensure_state_dir(state_dir)
    states = {}

    for state_file in sorted(state_dir.glob("*.json")):
        task_name = state_file.stem
        try:
            states[task_name] = load_state(task_name, state_dir)
        except StateError:
            # Skip corrupted state files
            continue

    return states


__all__ = [
    "StateError",
    "STATE_DIR",
    "ensure_state_dir",
    "load_state",
    "save_state",
    "update_state",
    "delete_state",
    "list_states",
    "get_state_path",
]
