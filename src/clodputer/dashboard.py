from __future__ import annotations

import curses
import os
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import psutil

from .config import ConfigError, validate_all_tasks
from .logger import tail_events
from .queue import LockAcquisitionError, QueueCorruptionError, QueueManager
from .watcher import file_watch_tasks, watcher_status


def _safe_addstr(window: "curses._CursesWindow", y: int, x: int, text: str, attr: int = 0) -> None:
    """Write text to a curses window, ignoring overflow errors."""
    try:
        window.addstr(y, x, text[: max(0, window.getmaxyx()[1] - x)], attr)
    except curses.error:
        pass


def _format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "-"
    minutes, remainder = divmod(int(seconds), 60)
    if minutes:
        return f"{minutes}m{remainder:02d}s"
    return f"{remainder}s"


def _format_log_line(event: Dict[str, object]) -> str:
    timestamp = str(event.get("timestamp", "-"))
    name = str(event.get("task_name") or event.get("task_id") or "-")
    event_type = event.get("event")
    if event_type == "task_completed":
        result = event.get("result") or {}
        if isinstance(result, dict):
            duration = _format_duration(result.get("duration"))
            return_code = result.get("return_code")
            extras = []
            if return_code is not None:
                extras.append(f"code={return_code}")
            parse_error = result.get("parse_error")
            if parse_error:
                extras.append(f"parse_error={parse_error}")
            extra = f" ({', '.join(extras)})" if extras else ""
        else:
            duration = "-"
            extra = ""
        return f"{timestamp} ✅ {name} {duration}{extra}"
    if event_type == "task_failed":
        error = event.get("error") or {}
        if isinstance(error, dict):
            message = error.get("error") or error.get("message") or "unknown error"
            return_code = error.get("return_code")
            extra = f" (code={return_code})" if return_code is not None else ""
        else:
            message = str(error)
            extra = ""
        return f"{timestamp} ❌ {name} {message}{extra}"
    if event_type == "task_started":
        return f"{timestamp} ▶️  {name}"
    return f"{timestamp} ℹ️  {name} event={event_type}"


def _load_average() -> Optional[Tuple[float, float, float]]:
    getter = getattr(os, "getloadavg", None)
    if not getter:
        return None
    try:
        return getter()
    except OSError:
        return None


def _parse_iso(timestamp: Optional[str]) -> Optional[datetime]:
    if not timestamp:
        return None
    try:
        value = str(timestamp)
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class DashboardSnapshot:
    queue_status: Dict[str, object] = field(default_factory=dict)
    log_events: List[Dict[str, object]] = field(default_factory=list)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    load_avg: Optional[Tuple[float, float, float]] = None
    last_updated: float = field(default_factory=time.time)


class TerminalDashboard:
    """Interactive curses dashboard for monitoring Clodputer runtime state."""

    def __init__(self, refresh_seconds: float = 1.0, log_lines: int = 8) -> None:
        self.refresh_seconds = refresh_seconds
        self.log_lines = log_lines
        self.snapshot = DashboardSnapshot()
        self.overlay: Optional[str] = None
        self.running = True
        self._last_refresh = 0.0
        psutil.cpu_percent(interval=None)  # Prime CPU sampling

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, stdscr: "curses._CursesWindow") -> None:
        self._setup_curses(stdscr)
        while self.running:
            now = time.time()
            if now - self._last_refresh >= self.refresh_seconds:
                self.snapshot = self._gather_snapshot()
                self._last_refresh = now

            self._draw(stdscr)
            key = stdscr.getch()
            if key == -1:
                continue
            self._handle_key(key)

    # ------------------------------------------------------------------
    # Curses setup + drawing
    # ------------------------------------------------------------------
    @staticmethod
    def _setup_curses(stdscr: "curses._CursesWindow") -> None:
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(500)
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)

    def _draw(self, stdscr: "curses._CursesWindow") -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        self._draw_header(stdscr, width)
        self._draw_main_panels(stdscr, height, width)
        self._draw_footer(stdscr, height, width)

        if self.overlay:
            self._draw_overlay(stdscr, height, width)

        stdscr.refresh()

    def _draw_header(self, stdscr: "curses._CursesWindow", width: int) -> None:
        title = " Clodputer Dashboard "
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        _safe_addstr(stdscr, 0, 0, title, curses.A_BOLD)
        _safe_addstr(stdscr, 0, max(0, width - len(timestamp) - 1), timestamp, curses.A_BOLD)
        stdscr.hline(1, 0, ord("-"), width)

    def _draw_main_panels(self, stdscr: "curses._CursesWindow", height: int, width: int) -> None:
        body_top = 2
        body_height = max(1, height - 4)
        left_width = max(20, width // 2)
        right_width = width - left_width

        queue_win = stdscr.derwin(body_height // 2, left_width, body_top, 0)
        resource_win = stdscr.derwin(body_height // 2, right_width, body_top, left_width)
        logs_win = stdscr.derwin(
            body_height - body_height // 2, width, body_top + body_height // 2, 0
        )

        queue_win.box()
        resource_win.box()
        logs_win.box()

        _safe_addstr(queue_win, 0, 2, " Queue ")
        self._draw_queue_panel(queue_win)

        _safe_addstr(resource_win, 0, 2, " Resources ")
        self._draw_resource_panel(resource_win)

        _safe_addstr(logs_win, 0, 2, " Recent Activity ")
        self._draw_logs_panel(logs_win)

    def _draw_queue_panel(self, window: "curses._CursesWindow") -> None:
        status = self.snapshot.queue_status
        running = status.get("running") if isinstance(status, dict) else None
        queued_counts = status.get("queued_counts", {}) if isinstance(status, dict) else {}
        total = queued_counts.get("total", 0)
        high_priority = queued_counts.get("high_priority", 0)
        if running:
            name = str(running.get("name", "-"))
            pid = running.get("pid", "-")
            started_at = running.get("started_at")
            elapsed = "-"
            started_dt = _parse_iso(started_at) if started_at else None
            if started_dt:
                elapsed_seconds = max(0.0, time.time() - started_dt.timestamp())
                elapsed = _format_duration(elapsed_seconds)
            text = f"🔵 {name} (pid {pid}) {elapsed}"
        else:
            text = "🟢 Idle"
        _safe_addstr(window, 1, 2, text)
        _safe_addstr(window, 2, 2, f"Queued: {total} (high priority: {high_priority})")

        queued_items = status.get("queued") if isinstance(status, dict) else None
        if isinstance(queued_items, Iterable):
            for idx, item in enumerate(list(queued_items)[: window.getmaxyx()[0] - 4]):
                name = str(item.get("name", "-"))
                priority = item.get("priority", "normal")
                attempt = item.get("attempt")
                not_before = item.get("not_before")
                extras: List[str] = []
                if attempt:
                    extras.append(f"attempt={attempt}")
                if not_before:
                    extras.append(f"eta={not_before}")
                extra = f" ({', '.join(extras)})" if extras else ""
                _safe_addstr(window, 3 + idx, 4, f"{name} [{priority}]{extra}")

    def _draw_resource_panel(self, window: "curses._CursesWindow") -> None:
        cpu = f"{self.snapshot.cpu_percent:5.1f}%"
        memory = f"{self.snapshot.memory_percent:5.1f}%"
        _safe_addstr(window, 1, 2, f"CPU usage:    {cpu}")
        _safe_addstr(window, 2, 2, f"Memory usage: {memory}")
        load_avg = self.snapshot.load_avg
        if load_avg:
            load_text = ", ".join(f"{value:.2f}" for value in load_avg)
            _safe_addstr(window, 3, 2, f"Load average: {load_text}")
        metrics = (
            self.snapshot.queue_status.get("metrics")
            if isinstance(self.snapshot.queue_status, dict)
            else {}
        )
        if isinstance(metrics, dict) and metrics:
            _safe_addstr(window, 5, 2, "Top Tasks:")
            for idx, (name, stats) in enumerate(list(metrics.items())[: window.getmaxyx()[0] - 6]):
                line = f"{name}: success={stats.get('success', 0)} failure={stats.get('failure', 0)} avg={stats.get('avg_duration', 0.0):.1f}s"
                _safe_addstr(window, 6 + idx, 4, line)

    def _draw_logs_panel(self, window: "curses._CursesWindow") -> None:
        max_rows = window.getmaxyx()[0] - 2
        events = self.snapshot.log_events[-max_rows:]
        start_row = max_rows - len(events)
        for idx, event in enumerate(events):
            text = _format_log_line(event)
            _safe_addstr(window, 1 + start_row + idx, 2, text)

    def _draw_footer(self, stdscr: "curses._CursesWindow", height: int, width: int) -> None:
        help_text = " q Quit │ t Task details │ l Log tail │ w Watcher status "
        stdscr.hline(height - 2, 0, ord("-"), width)
        _safe_addstr(
            stdscr, height - 1, max(0, (width - len(help_text)) // 2), help_text, curses.A_DIM
        )

    def _draw_overlay(self, stdscr: "curses._CursesWindow", height: int, width: int) -> None:
        title, lines = self._overlay_content()
        if not lines:
            return
        max_line = max(len(line) for line in lines)
        box_height = min(height - 4, len(lines) + 4)
        box_width = min(width - 4, max_line + 4)
        start_y = max(1, (height - box_height) // 2)
        start_x = max(1, (width - box_width) // 2)
        window = curses.newwin(box_height, box_width, start_y, start_x)
        window.box()
        _safe_addstr(window, 0, 2, f" {title} ")
        for idx, line in enumerate(lines[: box_height - 2]):
            _safe_addstr(window, 1 + idx, 2, line)
        window.refresh()

    # ------------------------------------------------------------------
    # Overlay helpers
    # ------------------------------------------------------------------
    def _overlay_content(self) -> Tuple[str, List[str]]:
        if self.overlay == "tasks":
            return ("Task Details", self._task_detail_lines())
        if self.overlay == "logs":
            lines = [_format_log_line(event) for event in self.snapshot.log_events[-40:]]
            return ("Log Tail", lines or ["No log events yet."])
        if self.overlay == "watcher":
            return ("Watcher Status", self._watcher_lines())
        return ("", [])

    def _task_detail_lines(self) -> List[str]:
        status = self.snapshot.queue_status
        lines: List[str] = []
        if not isinstance(status, dict):
            return ["Queue status unavailable."]

        running = status.get("running")
        if running:
            lines.append("Running task:")
            lines.extend(self._describe_task(running, indent="  "))
        else:
            lines.append("No task currently running.")

        if status.get("queued"):
            lines.append("")
            lines.append("Queued tasks:")
            for item in status["queued"]:
                lines.extend(self._describe_task(item, indent="  "))
                lines.append("")
            if lines and lines[-1] == "":
                lines.pop()
        else:
            lines.append("")
            lines.append("Queue is empty.")
        return lines

    def _describe_task(self, item: Dict[str, object], indent: str = "") -> List[str]:
        lines = [
            f"{indent}• {item.get('name', '-')}",
            f"{indent}  id={item.get('id', '-')}, priority={item.get('priority', '-')}",
        ]
        attempt = item.get("attempt")
        if attempt:
            lines.append(f"{indent}  attempt={attempt}")
        not_before = item.get("not_before")
        if not_before:
            lines.append(f"{indent}  not_before={not_before}")
        metadata = item.get("metadata")
        if isinstance(metadata, dict) and metadata:
            lines.append(f"{indent}  metadata:")
            for key, value in metadata.items():
                lines.append(f"{indent}    {key}: {value}")
        return lines

    def _watcher_lines(self) -> List[str]:
        info = watcher_status()
        lines = [
            f"Daemon running: {'yes' if info.get('running') else 'no'}",
            f"PID: {info.get('pid') or '-'}",
            f"Log file: {info.get('log_file') or '-'}",
            "",
        ]
        try:
            configs, errors = validate_all_tasks()
        except ConfigError as exc:
            return [f"Failed to load tasks: {exc}"]
        watcher_tasks = file_watch_tasks(configs)
        if not watcher_tasks:
            lines.append("No file-watch tasks configured.")
        else:
            lines.append(f"{len(watcher_tasks)} file-watch task(s):")
            for task in watcher_tasks:
                trigger = task.trigger
                assert trigger is not None and trigger.type == "file_watch"
                description = (
                    f"• {task.name} → {trigger.path} "
                    f"(pattern={trigger.pattern}, event={trigger.event}, debounce={trigger.debounce}ms)"
                )
                lines.extend(textwrap.wrap(description, width=70))
        if errors:
            lines.append("")
            lines.append("Tasks with validation errors:")
            for path, message in errors:
                lines.append(f"• {path}: {message}")
        return lines

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------
    def _handle_key(self, key: int) -> None:
        if key in (ord("q"), ord("Q")):
            self.running = False
        elif key == curses.KEY_RESIZE:
            # Resize is handled implicitly on next draw pass
            return
        elif key in (ord("t"), ord("T")):
            self._toggle_overlay("tasks")
        elif key in (ord("l"), ord("L")):
            self._toggle_overlay("logs")
        elif key in (ord("w"), ord("W")):
            self._toggle_overlay("watcher")
        elif key in (27,):  # ESC
            self.overlay = None

    def _toggle_overlay(self, name: str) -> None:
        self.overlay = None if self.overlay == name else name

    # ------------------------------------------------------------------
    # Snapshot gathering
    # ------------------------------------------------------------------
    def _gather_snapshot(self) -> DashboardSnapshot:
        queue_status: Dict[str, object] = {"error": "Queue unavailable"}
        try:
            manager = QueueManager(auto_lock=False)
            queue_status = manager.get_status()
        except (QueueCorruptionError, LockAcquisitionError) as exc:
            queue_status = {"error": f"Queue error: {exc}"}
        except Exception as exc:  # pragma: no cover - defensive guard
            queue_status = {"error": f"Queue status unavailable: {exc}"}

        log_events = tail_events(limit=100)
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_percent = psutil.virtual_memory().percent
        load_avg = _load_average()

        return DashboardSnapshot(
            queue_status=queue_status,
            log_events=log_events,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            load_avg=load_avg,
            last_updated=time.time(),
        )


def _dashboard(stdscr: "curses._CursesWindow") -> None:
    dashboard = TerminalDashboard()
    dashboard.run(stdscr)


def run_dashboard() -> None:
    curses.wrapper(_dashboard)


__all__ = ["run_dashboard", "TerminalDashboard"]
