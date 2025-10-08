"""Application settings loader for Clodputer.

Settings are read from ``~/.clodputer/config.yaml`` when available.
Only a small subset of values is supported for now, focusing on queue
resource heuristics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

SETTINGS_FILE = Path.home() / ".clodputer" / "config.yaml"


@dataclass(frozen=True)
class QueueSettings:
    max_parallel: int = 1
    cpu_percent: float = 85.0
    memory_percent: float = 85.0


@dataclass(frozen=True)
class Settings:
    queue: QueueSettings = QueueSettings()


_CACHE: Optional[Settings] = None


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}


def load_settings() -> Settings:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    data = _load_yaml(SETTINGS_FILE)
    queue_section = data.get("queue", {}) if isinstance(data, dict) else {}

    queue_settings = QueueSettings(
        max_parallel=int(queue_section.get("max_parallel", 1) or 1),
        cpu_percent=float(queue_section.get("cpu_percent", 85.0) or 85.0),
        memory_percent=float(queue_section.get("memory_percent", 85.0) or 85.0),
    )

    _CACHE = Settings(queue=queue_settings)
    return _CACHE


__all__ = ["Settings", "QueueSettings", "load_settings", "SETTINGS_FILE"]
