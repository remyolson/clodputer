from __future__ import annotations

from clodputer.menubar import STATUS_ERROR, STATUS_IDLE, STATUS_RUNNING, determine_status_icon


def test_determine_status_icon_running() -> None:
    queue_status = {"running": {"name": "task", "pid": 123}}
    icon, tooltip = determine_status_icon(queue_status, None)
    assert icon == STATUS_RUNNING
    assert "Running" in tooltip


def test_determine_status_icon_error() -> None:
    queue_status = {"running": None}
    last_event = {"event": "task_failed", "task_name": "oops"}
    icon, tooltip = determine_status_icon(queue_status, last_event)
    assert icon == STATUS_ERROR
    assert "oops" in tooltip


def test_determine_status_icon_idle() -> None:
    queue_status = {"running": None}
    icon, tooltip = determine_status_icon(queue_status, None)
    assert icon == STATUS_IDLE
    assert tooltip == "Idle"
