"""Simple task metrics persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


METRICS_FILE = Path.home() / ".clodputer" / "metrics.json"


def _load_metrics() -> Dict[str, dict]:
    try:
        return json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_metrics(data: Dict[str, dict]) -> None:
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    METRICS_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def record_success(task_name: str, duration: float) -> None:
    data = _load_metrics()
    entry = data.setdefault(task_name, {"success": 0, "failure": 0, "total_duration": 0.0})
    entry["success"] += 1
    entry["total_duration"] += duration
    _save_metrics(data)


def record_failure(task_name: str) -> None:
    data = _load_metrics()
    entry = data.setdefault(task_name, {"success": 0, "failure": 0, "total_duration": 0.0})
    entry["failure"] += 1
    _save_metrics(data)


def metrics_summary() -> Dict[str, dict]:
    data = _load_metrics()
    summary: Dict[str, dict] = {}
    for name, stats in data.items():
        success = stats.get("success", 0)
        failure = stats.get("failure", 0)
        total = success + failure
        avg = stats.get("total_duration", 0.0) / success if success else 0.0
        summary[name] = {
            "success": success,
            "failure": failure,
            "total": total,
            "avg_duration": avg,
        }
    ordered = sorted(summary.items(), key=lambda kv: kv[1]["total"], reverse=True)
    return dict(ordered)


__all__ = ["record_success", "record_failure", "metrics_summary", "METRICS_FILE"]
