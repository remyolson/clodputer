# Copyright (c) 2025 Rémy Olson
"""
macOS menu bar application for Clodputer.

Uses the `rumps` library to provide a simple status indicator and quick-access
actions for viewing status, opening logs, and launching a terminal dashboard.
"""

from __future__ import annotations

import subprocess
from typing import Optional, Tuple

import rumps

from .logger import LOG_FILE, tail_events
from .queue import QueueManager

STATUS_IDLE = "🟢"
STATUS_RUNNING = "🔵"
STATUS_ERROR = "🔴"


def determine_status_icon(queue_status: dict, last_event: Optional[dict]) -> Tuple[str, str]:
    if queue_status.get("running"):
        running = queue_status["running"]
        name = running.get("name", "Unknown")
        return STATUS_RUNNING, f"Running {name}"

    if last_event and last_event.get("event") == "task_failed":
        task_name = last_event.get("task_name", "Unknown")
        return STATUS_ERROR, f"Last task failed: {task_name}"

    return STATUS_IDLE, "Idle"


def _osascript(script: str) -> None:
    try:
        subprocess.run(["osascript", "-e", script], check=True)
    except Exception:
        rumps.alert("Unable to launch Terminal dashboard.")


class ClodputerMenuBar(rumps.App):
    def __init__(self, refresh_interval: int = 30) -> None:
        super().__init__("Clodputer", title=STATUS_IDLE)
        self.menu = [
            "View Status",
            "Open Logs",
            "Launch Dashboard",
            None,
            "Quit",
        ]
        self.timer = rumps.Timer(self.update_status, refresh_interval)
        self.timer.start()
        self.update_status(None)

    def update_status(self, _sender) -> None:
        with QueueManager(auto_lock=False) as queue_manager:
            status = queue_manager.get_status()
        recent = tail_events(limit=1)
        last_event = recent[0] if recent else None
        icon, tooltip = determine_status_icon(status, last_event)
        self.title = icon
        self.icon = None
        self.template = False
        self.menu["View Status"].title = f"View Status ({tooltip})"

    @rumps.clicked("View Status")
    def view_status(self, _sender) -> None:
        with QueueManager(auto_lock=False) as queue_manager:
            status = queue_manager.get_status()

        running = status.get("running")
        queued = status.get("queued_counts", {}).get("total", 0)
        lines = []
        if running:
            lines.append(f"🔵 Running: {running.get('name')} (pid {running.get('pid')})")
        else:
            lines.append("🟢 Idle: no active task.")
        lines.append(f"📦 Queue: {queued} queued task(s)")
        rumps.alert("\n".join(lines))

    @rumps.clicked("Open Logs")
    def open_logs(self, _sender) -> None:
        if not LOG_FILE.exists():
            rumps.alert("No log file found yet.")
            return
        try:
            subprocess.run(["open", str(LOG_FILE)], check=True)
        except Exception:
            rumps.alert(f"Log file located at {LOG_FILE}")

    @rumps.clicked("Launch Dashboard")
    def launch_dashboard(self, _sender) -> None:
        script = (
            'tell application "Terminal"\n'
            "  activate\n"
            '  do script "clodputer dashboard"\n'
            "end tell"
        )
        _osascript(script)

    @rumps.clicked("Quit")
    def quit_app(self, _sender) -> None:
        rumps.quit_application()


def run_menu_bar() -> None:
    ClodputerMenuBar().run()


__all__ = ["ClodputerMenuBar", "determine_status_icon", "run_menu_bar"]
