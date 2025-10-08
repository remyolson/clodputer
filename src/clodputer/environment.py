"""Environment detection and onboarding state management."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional


STATE_FILE = Path.home() / ".clodputer" / "env.json"


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
    data = _load_state()
    data["claude_cli"] = path
    _persist_state(data)


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _persist_state(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


__all__ = ["claude_cli_path", "store_claude_cli_path", "STATE_FILE"]
