"""Environment detection and onboarding state management."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator


STATE_FILE = Path.home() / ".clodputer" / "env.json"
STATE_SCHEMA_VERSION = 1  # Current schema version

# Configuration constants
STATE_BACKUP_SUFFIX = ".backup"
STATE_CORRUPTED_SUFFIX = ".corrupted"


class OnboardingState(BaseModel):
    """Validated onboarding state model.

    Ensures all state values are valid before persisting to disk.
    Uses Pydantic for automatic validation and type coercion.
    """

    schema_version: int = Field(default=STATE_SCHEMA_VERSION, ge=0)
    claude_cli: Optional[str] = Field(default=None, min_length=1)
    onboarding_runs: Optional[int] = Field(default=None, ge=0)
    onboarding_last_run: Optional[str] = Field(default=None, min_length=1)
    onboarding_completed_at: Optional[str] = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="allow")  # Allow additional fields for forward compatibility

    @field_validator("claude_cli")
    @classmethod
    def validate_claude_cli(cls, v: Optional[str]) -> Optional[str]:
        """Ensure claude_cli path is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("claude_cli path cannot be empty")
        return v


# Migration functions registry: (from_version, to_version) -> migration_func
_MIGRATIONS: Dict[Tuple[int, int], Callable[[dict], dict]] = {}


def migration(from_version: int, to_version: int):
    """Decorator to register a state migration function."""

    def decorator(func: Callable[[dict], dict]) -> Callable[[dict], dict]:
        _MIGRATIONS[(from_version, to_version)] = func
        return func

    return decorator


def _migrate_state(data: dict) -> dict:
    """Migrate state to current schema version."""
    current_version = data.get("schema_version", 0)

    if current_version == STATE_SCHEMA_VERSION:
        return data  # Already current

    if current_version > STATE_SCHEMA_VERSION:
        import sys

        print(
            f"Warning: State file schema version {current_version} is newer than "
            f"supported version {STATE_SCHEMA_VERSION}. Some features may not work.",
            file=sys.stderr,
        )
        return data

    # Apply migrations in sequence
    migrated_data = data.copy()
    version = current_version

    while version < STATE_SCHEMA_VERSION:
        next_version = version + 1
        migration_func = _MIGRATIONS.get((version, next_version))

        if migration_func is None:
            raise RuntimeError(f"No migration defined from version {version} to {next_version}")

        migrated_data = migration_func(migrated_data)
        migrated_data["schema_version"] = next_version
        version = next_version

    return migrated_data


@migration(from_version=0, to_version=1)
def _migrate_v0_to_v1(data: dict) -> dict:
    """Add schema_version field to unversioned state.

    This is the initial migration that adds version tracking.
    No data transformation needed, just adds version tracking.
    """
    return data


def claude_cli_path(explicit: Optional[str] = None) -> Optional[str]:
    """Resolve the Claude CLI executable.

    Order of precedence:
        1. Explicit override (from caller).
        2. Stored path in ~/.clodputer/env.json.
        3. Runtime search via shutil.which + common fallbacks.
    """

    if explicit:
        return explicit

    stored = _load_state().get("claude_cli")
    if stored:
        return stored

    found = shutil.which("claude")
    if found:
        return found

    # Common local installations
    candidates = [
        Path.home() / ".claude" / "local" / "claude",
        Path("/opt/homebrew/bin/claude"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def store_claude_cli_path(path: str) -> None:
    """Store the Claude CLI executable path in persistent state.

    Args:
        path: Absolute path to the Claude CLI executable.

    Example:
        >>> store_claude_cli_path("/usr/local/bin/claude")
    """
    update_state({"claude_cli": path})


def update_state(updates: Dict[str, object]) -> None:
    """Update onboarding state with new key-value pairs.

    Merges the provided updates with existing state and persists to disk.
    Creates backups automatically before writing.

    Args:
        updates: Dictionary of state keys and values to update.

    Example:
        >>> update_state({"phase": "complete", "timestamp": "2025-01-15"})
    """
    data = _load_state()
    data.update(updates)
    _persist_state(data)


def onboarding_state() -> Dict[str, object]:
    """Load and return the complete onboarding state.

    Automatically handles corruption recovery and schema migrations.

    Returns:
        Dictionary containing all onboarding state. Empty dict if no state exists.

    Example:
        >>> state = onboarding_state()
        >>> claude_path = state.get("claude_cli")
    """
    return _load_state()


def reset_state() -> None:
    """Delete the onboarding state file.

    Removes ~/.clodputer/env.json if it exists. Used for testing
    and when users want to restart onboarding from scratch.

    Example:
        >>> reset_state()  # Clears all onboarding progress
    """
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def _load_state() -> dict:
    """Load state from file with corruption recovery and migration."""
    if not STATE_FILE.exists():
        return {}

    try:
        content = STATE_FILE.read_text(encoding="utf-8")
        data = json.loads(content)

        # Migrate if needed
        migrated = _migrate_state(data)

        # If migration occurred, persist immediately
        if migrated.get("schema_version") != data.get("schema_version"):
            _persist_state(migrated)

        return migrated
    except json.JSONDecodeError as exc:
        # Attempt recovery from backup
        backup_file = STATE_FILE.parent / f"{STATE_FILE.name}{STATE_BACKUP_SUFFIX}"
        if backup_file.exists():
            try:
                content = backup_file.read_text(encoding="utf-8")
                data = json.loads(content)
                # Restore from backup
                _persist_state(data)
                return data
            except (json.JSONDecodeError, OSError):
                pass  # Backup also corrupted

        # No recovery possible, log and return empty state
        import sys

        print(f"Warning: State file corrupted at {STATE_FILE}", file=sys.stderr)
        print(f"  Error: {exc}", file=sys.stderr)
        print("  Starting with clean state. Run 'clodputer init' to reconfigure.", file=sys.stderr)

        # Archive corrupted file for debugging
        corrupted_file = STATE_FILE.parent / f"{STATE_FILE.name}{STATE_CORRUPTED_SUFFIX}"
        try:
            STATE_FILE.rename(corrupted_file)
            print(f"  Corrupted file saved to: {corrupted_file}", file=sys.stderr)
        except OSError:
            pass  # Non-fatal if archive fails

        return {}
    except OSError as exc:
        import sys

        print(f"Warning: Cannot read state file: {exc}", file=sys.stderr)
        return {}


def _persist_state(data: dict) -> None:
    """Persist state with validation, backup, and version tracking.

    Args:
        data: State dictionary to persist.

    Raises:
        ValueError: If state validation fails (invalid values).

    Example:
        >>> _persist_state({"claude_cli": "/path/to/claude"})  # Valid
        >>> _persist_state({"claude_cli": ""})  # Raises ValueError
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Ensure schema_version is set
    if "schema_version" not in data:
        data = {**data, "schema_version": STATE_SCHEMA_VERSION}

    # Validate state before persisting
    try:
        OnboardingState(**data)
    except Exception as exc:
        raise ValueError(f"Invalid state data: {exc}") from exc

    # Create backup of existing state before overwriting
    if STATE_FILE.exists():
        backup_file = STATE_FILE.parent / f"{STATE_FILE.name}{STATE_BACKUP_SUFFIX}"
        try:
            shutil.copy2(STATE_FILE, backup_file)
        except OSError:
            pass  # Non-fatal if backup fails

    # Write new state atomically
    temp_file = STATE_FILE.parent / f"{STATE_FILE.name}.tmp"
    temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp_file.replace(STATE_FILE)


__all__ = [
    "claude_cli_path",
    "store_claude_cli_path",
    "update_state",
    "onboarding_state",
    "reset_state",
    "STATE_FILE",
]
