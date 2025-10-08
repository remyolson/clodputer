# Copyright (c) 2025 Rémy Olson
"""
Click-based CLI entry point for Clodputer.

Commands included:
- clodputer run <task>
- clodputer dashboard
- clodputer status
- clodputer logs
- clodputer list
- clodputer queue
- clodputer install
- clodputer uninstall
- clodputer watch
- clodputer doctor
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Iterable, Optional

import click
import json

from .config import ConfigError, TASKS_DIR, ensure_tasks_dir, load_task_by_name, validate_all_tasks
from .cron import (
    CRON_LOG_FILE,
    CRON_SECTION_BEGIN,
    CRON_SECTION_END,
    CronError,
    generate_cron_section,
    install_cron_jobs,
    preview_schedule,
    read_crontab,
    scheduled_tasks,
    uninstall_cron_jobs,
)
from .dashboard import run_dashboard
from .diagnostics import gather_diagnostics
from .executor import ExecutionResult, TaskExecutor
from .logger import LOG_FILE, iter_events, tail_events
from .onboarding import run_onboarding
from .queue import QueueManager
from .templates import available as available_templates, export as export_template
from .watcher import (
    WATCHER_LOG_FILE,
    WatcherError,
    file_watch_tasks,
    run_watch_service,
    start_daemon as start_watch_daemon,
    stop_daemon as stop_watch_daemon,
    watcher_status,
)
from .menubar import run_menu_bar

try:
    __version__ = metadata.version("clodputer")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.0-dev"


def _parse_iso(timestamp: str) -> Optional[datetime]:
    if not timestamp:
        return None
    try:
        if timestamp.endswith("Z"):
            timestamp = timestamp.replace("Z", "+00:00")
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None


def _format_duration(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def _print_execution_result(result: ExecutionResult) -> None:
    status_symbol = {"success": "✅", "failure": "❌", "timeout": "⏱️", "error": "⚠️"}.get(
        result.status, "ℹ️"
    )
    click.echo(
        f"{status_symbol} {result.task_name} ({result.task_id}) "
        f"- {result.status} in {_format_duration(result.duration)}"
    )
    if result.error:
        click.echo(f"   Error: {result.error}")
    if result.output_json:
        click.echo(f"   Output: {result.output_json}")


def _compute_queue_position(queue_status: dict, task_id: str) -> Optional[int]:
    for index, item in enumerate(queue_status.get("queued", []), start=1):
        if item["id"] == task_id:
            return index
    return None


def _today_stats() -> tuple[int, int]:
    today = datetime.now(timezone.utc).date()
    success = failure = 0
    for event in iter_events(reverse=True):
        if event is None:
            continue
        timestamp = event.get("timestamp")
        dt = _parse_iso(timestamp) if timestamp else None
        if not dt:
            continue
        if dt.date() != today:
            break
        if event.get("event") == "task_completed":
            success += 1
        elif event.get("event") == "task_failed":
            failure += 1
    return success, failure


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__)
def cli() -> None:
    """Clodputer CLI."""


@cli.command()
@click.option(
    "--reset",
    is_flag=True,
    help="Reset stored onboarding state before running the guided flow.",
)
def init(reset: bool) -> None:
    """Run the guided onboarding workflow."""

    try:
        run_onboarding(reset=reset)
    except click.ClickException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        raise click.ClickException(f"Onboarding failed: {exc}") from exc


@cli.command()
@click.argument("task_name")
@click.option("--priority", type=click.Choice(["normal", "high"]), default="normal")
@click.option("--enqueue-only", is_flag=True, help="Only enqueue the task, do not execute it now.")
def run(task_name: str, priority: str, enqueue_only: bool) -> None:
    """Enqueue and optionally execute a task."""
    try:
        load_task_by_name(task_name)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    with QueueManager() as queue:
        item = queue.enqueue(task_name, priority=priority, metadata={"manual": True})
        status = queue.get_status()
        position = _compute_queue_position(status, item.id)
        click.echo(
            f"Enqueued {task_name} ({item.id}) at position {position or 1} "
            f"with priority {priority}."
        )
        if enqueue_only:
            return
        executor = TaskExecutor(queue_manager=queue)
        results = executor.process_queue()
        outcome = next((r for r in results if r.task_id == item.id), None)
        if outcome:
            _print_execution_result(outcome)
        else:
            click.echo("Task did not execute in this session (another task may still be running).")


@cli.command()
@click.option(
    "--tail", type=int, default=10, show_default=True, help="Number of entries to display."
)
@click.option("--task", "task_filter", help="Filter logs to a specific task name.")
@click.option("--follow", is_flag=True, help="Follow log output (like tail -f).")
@click.option("--json", "json_output", is_flag=True, help="Output raw JSON events.")
def logs(tail: int, task_filter: Optional[str], follow: bool, json_output: bool) -> None:
    """Display structured execution logs."""
    if not LOG_FILE.exists():
        click.echo("No log entries yet.")
        return

    def display(entries: Iterable[dict]) -> None:
        for event in entries:
            task_name = event.get("task_name")
            if task_filter and task_name != task_filter:
                continue
            if json_output:
                click.echo(json.dumps(event))
                continue
            ts = event.get("timestamp", "unknown")
            if event.get("event") == "task_completed":
                duration = event.get("result", {}).get("duration")
                duration_str = _format_duration(duration) if duration else "-"
                return_code = event.get("result", {}).get("return_code")
                parse_error = event.get("result", {}).get("parse_error")
                extras = []
                if return_code is not None:
                    extras.append(f"code={return_code}")
                if parse_error:
                    extras.append(f"parse_error={parse_error}")
                extra_text = f" {' '.join(extras)}" if extras else ""
                click.echo(f"{ts} ✅ {task_name} duration={duration_str}{extra_text}")
            elif event.get("event") == "task_failed":
                error_payload = event.get("error", {})
                if isinstance(error_payload, dict):
                    err = error_payload.get("error") or "unknown"
                    return_code = error_payload.get("return_code")
                    parse_error = error_payload.get("parse_error")
                else:
                    err = error_payload or "unknown"
                    return_code = None
                    parse_error = None
                extras = []
                if return_code is not None:
                    extras.append(f"code={return_code}")
                if parse_error:
                    extras.append(f"parse_error={parse_error}")
                extra_text = f" {' '.join(extras)}" if extras else ""
                click.echo(f"{ts} ❌ {task_name} error={err}{extra_text}")
            elif event.get("event") == "task_started":
                click.echo(f"{ts} ▶️  {task_name}")
            else:
                click.echo(f"{ts} ℹ️  {task_name} event={event.get('event')}")

    display(tail_events(limit=tail))
    if not follow:
        return

    with LOG_FILE.open("r", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)
        try:
            while True:
                where = handle.tell()
                line = handle.readline()
                if not line:
                    time.sleep(1)
                    handle.seek(where)
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                display([event])
        except KeyboardInterrupt:  # pragma: no cover
            pass


@cli.command()
def list() -> None:  # type: ignore[override]
    """List configured tasks."""
    ensure_tasks_dir()
    configs, errors = validate_all_tasks()
    if configs:
        click.echo("Configured tasks:")
        for cfg in configs:
            status = "enabled" if cfg.enabled else "disabled"
            schedule = cfg.schedule.expression if cfg.schedule else "-"
            if cfg.trigger:
                if cfg.trigger.type == "file_watch":
                    trigger_desc = (
                        f"file_watch path={cfg.trigger.path} pattern={cfg.trigger.pattern} "
                        f"event={cfg.trigger.event}"
                    )
                elif cfg.trigger.type == "interval":
                    trigger_desc = f"interval every {cfg.trigger.seconds}s"
                else:
                    trigger_desc = cfg.trigger.type
            else:
                trigger_desc = "manual"
            click.echo(f" • {cfg.name} [{status}] trigger={trigger_desc} schedule={schedule}")
    else:
        click.echo("No task configs found.")

    if errors:
        click.echo("\nTasks with validation errors:")
        for path, error in errors:
            click.echo(f" • {path}: {error}")


@cli.group()
def template() -> None:
    """Manage bundled task templates."""


@template.command("list")
def template_list() -> None:
    templates = available_templates()
    if not templates:
        click.echo("No bundled templates available.")
        return
    click.echo("Available templates:")
    for name in templates:
        click.echo(f" • {name}")


@template.command("export")
@click.argument("name")
@click.option(
    "--directory",
    "directory",
    default=str(TASKS_DIR),
    type=click.Path(path_type=Path),
    help="Directory to copy the template into (default: ~/.clodputer/tasks).",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    help="Optional explicit file path to write the template to.",
)
@click.option("--overwrite", is_flag=True, help="Overwrite the destination file if it exists.")
def template_export(
    name: str, directory: Path, output_path: Optional[Path], overwrite: bool
) -> None:
    """Copy a bundled template into your workspace."""

    directory_path = directory.expanduser()

    target: Path
    if output_path:
        target = output_path.expanduser()
    else:
        target = directory_path / name
        directory_path.mkdir(parents=True, exist_ok=True)

    if target.exists() and not overwrite:
        raise click.ClickException(
            f"Destination {target} already exists. Re-run with --overwrite to replace it."
        )

    try:
        destination = target if output_path else directory_path
        written = export_template(name, destination)
    except FileNotFoundError as exc:
        available = ", ".join(available_templates()) or "<none>"
        raise click.ClickException(
            f"Unknown template {name!r}. Available templates: {available}."
        ) from exc

    click.echo(f"Template {name} copied to {written}")


@cli.command()
@click.option("--clear", is_flag=True, help="Clear all queued tasks (does not stop running task).")
def queue(clear: bool) -> None:
    """Inspect or clear the task queue."""
    with QueueManager() as queue_manager:
        if clear:
            queue_manager.clear_queue()
            click.echo("Queue cleared.")
            return
        status = queue_manager.get_status()
        running = status.get("running")
        if running:
            started = _parse_iso(running.get("started_at", "")) or datetime.now(timezone.utc)
            elapsed = datetime.now(timezone.utc) - started
            click.echo(
                f"Running: {running['name']} (pid {running['pid']}) for {_format_duration(elapsed.total_seconds())}"
            )
        else:
            click.echo("No task currently running.")

        if status.get("queued"):
            click.echo("\nQueued tasks:")
            for item in status["queued"]:
                extras = []
                if item.get("attempt"):
                    extras.append(f"attempt={item['attempt']}")
                if item.get("not_before"):
                    extras.append(f"not_before={item['not_before']}")
                extra_text = f" ({', '.join(extras)})" if extras else ""
                click.echo(
                    f" • {item['name']} [{item['priority']}] enqueued_at={item['enqueued_at']}{extra_text}"
                )
        else:
            click.echo("\nQueue is empty.")

        if status.get("metrics"):
            click.echo("\nTask metrics:")
            for name, stats in status["metrics"].items():
                click.echo(
                    f" • {name}: success={stats['success']} failure={stats['failure']} avg_duration={stats['avg_duration']:.2f}s"
                )


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview cron entries without modifying crontab.")
def install(dry_run: bool) -> None:
    """Install scheduled tasks into the user's crontab."""
    configs, errors = validate_all_tasks()
    if errors:
        click.echo("⚠️  Some task configs are invalid; fix them before installing cron jobs:")
        for path, err in errors:
            click.echo(f" • {path}: {err}")
        raise click.ClickException("Task config validation failed")

    entries = scheduled_tasks(configs)
    if not entries:
        click.echo("No enabled cron or interval tasks found.")
        return

    section = generate_cron_section(entries)
    if dry_run:
        click.echo(section.rstrip())
        return

    try:
        result = install_cron_jobs(entries)
    except CronError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"Installed {result['installed']} cron job(s). Backup written to {result['backup']}."
    )
    click.echo(f"Cron log: {CRON_LOG_FILE}")


@cli.command()
@click.option(
    "--dry-run", is_flag=True, help="Show current Clodputer cron section without removing it."
)
def uninstall(dry_run: bool) -> None:
    """Remove Clodputer-managed cron jobs."""
    try:
        current = read_crontab()
    except CronError as exc:
        raise click.ClickException(str(exc)) from exc

    if CRON_SECTION_BEGIN not in current:
        click.echo("No Clodputer cron section found.")
        return

    if dry_run:
        click.echo(
            current[
                current.index(CRON_SECTION_BEGIN) : current.index(CRON_SECTION_END)
                + len(CRON_SECTION_END)
            ]
        )
        return

    try:
        result = uninstall_cron_jobs()
    except CronError as exc:
        raise click.ClickException(str(exc)) from exc

    if result["removed"]:
        click.echo(f"Removed Clodputer cron section. Backup written to {result['backup']}.")
    else:
        click.echo("No Clodputer cron section found.")


@cli.command("schedule-preview")
@click.argument("task_name")
@click.option("--count", default=5, show_default=True, help="Number of upcoming runs to display.")
def schedule_preview_command(task_name: str, count: int) -> None:
    """Preview upcoming run times for a scheduled or interval task."""

    configs, errors = validate_all_tasks()
    if errors:
        click.echo("⚠️  Cannot preview schedule until configuration errors are resolved:")
        for path, err in errors:
            click.echo(f" • {path}: {err}")
        raise click.ClickException("Task config validation failed")

    entries = scheduled_tasks(configs)
    for entry in entries:
        if entry.task.name == task_name:
            try:
                runs = preview_schedule(entry, count=count)
            except CronError as exc:
                raise click.ClickException(str(exc)) from exc

            click.echo(f"Upcoming runs for {task_name}:")
            for dt in runs:
                click.echo(f" • {dt.isoformat()}")
            return

    raise click.ClickException(
        f"Task '{task_name}' is not enabled with a cron schedule or interval trigger."
    )


@cli.command()
@click.option("--daemon", is_flag=True, help="Run watcher service in the background")
@click.option("--stop", is_flag=True, help="Stop the watcher daemon")
@click.option("--status", is_flag=True, help="Show watcher daemon status")
def watch(daemon: bool, stop: bool, status: bool) -> None:
    """Manage the file watcher service."""

    chosen = sum(1 for flag in (daemon, stop, status) if flag)
    if chosen > 1:
        raise click.ClickException("Choose only one of --daemon, --stop, or --status")

    if status:
        info = watcher_status()
        if info["running"]:
            click.echo(f"Watcher daemon running (PID {info['pid']}). Log: {info['log_file']}")
        else:
            click.echo("Watcher daemon not running.")
        return

    if stop:
        if stop_watch_daemon():
            click.echo("Watcher daemon stopped.")
        else:
            click.echo("Watcher daemon is not running.")
        return

    configs, errors = validate_all_tasks()
    if errors:
        click.echo("⚠️  Some task configs are invalid; fix them before starting the watcher:")
        for path, err in errors:
            click.echo(f" • {path}: {err}")
        raise click.ClickException("Task config validation failed")

    tasks = file_watch_tasks(configs)
    if not tasks:
        click.echo("No tasks configured with file_watch triggers.")
        return

    if daemon:
        try:
            pid = start_watch_daemon()
        except WatcherError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Watcher daemon started (PID {pid}). Log: {WATCHER_LOG_FILE}")
        return

    click.echo("Starting watcher in foreground. Press Ctrl+C to stop.")
    try:
        run_watch_service(tasks)
    except WatcherError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
def menu() -> None:
    """Start the Clodputer menu bar application."""

    try:
        run_menu_bar()
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(f"Failed to start menu bar: {exc}") from exc


@cli.command()
def dashboard() -> None:
    """Launch the interactive terminal dashboard."""

    try:
        run_dashboard()
    except KeyboardInterrupt:  # pragma: no cover - user exit
        pass
    except Exception as exc:  # pragma: no cover - curses failures
        raise click.ClickException(f"Failed to start dashboard: {exc}") from exc


@cli.command()
def status() -> None:
    """Show queue state and recent activity."""
    queue_manager = QueueManager(auto_lock=False)
    status = queue_manager.get_status()
    running = status.get("running")
    if running:
        started = _parse_iso(running.get("started_at", "")) or datetime.now(timezone.utc)
        elapsed = datetime.now(timezone.utc) - started
        click.echo(
            f"🔵 Running: {running['name']} (pid {running['pid']}) "
            f"{_format_duration(elapsed.total_seconds())} elapsed"
        )
    else:
        click.echo("🟢 Idle: no active task.")

    total = status["queued_counts"]["total"]
    high = status["queued_counts"]["high_priority"]
    click.echo(f"📦 Queue: {total} queued ({high} high priority)")

    click.echo("\nRecent executions:")
    recent = tail_events(limit=10)
    if not recent:
        click.echo("  (no executions logged yet)")
    else:
        for event in recent:
            ts = event.get("timestamp", "unknown")
            task = event.get("task_name", "unknown")
            if event.get("event") == "task_completed":
                duration = event.get("result", {}).get("duration")
                duration_str = _format_duration(duration) if duration else "-"
                click.echo(f" • {ts} ✅ {task} ({duration_str})")
            elif event.get("event") == "task_failed":
                err = event.get("error", {}).get("error") or "unknown"
                click.echo(f" • {ts} ❌ {task} ({err})")
            else:
                click.echo(f" • {ts} ▶️  {task}")

    success, failure = _today_stats()
    click.echo(f"\n📊 Today: {success} success / {failure} failed")

    metrics = status.get("metrics") or {}
    if metrics:
        click.echo("\n📈 Task Metrics:")
        for name, stats in list(metrics.items())[:5]:
            click.echo(
                f" • {name}: success={stats['success']} failure={stats['failure']} avg={stats['avg_duration']:.2f}s"
            )


@cli.command()
def doctor() -> None:
    """Run diagnostics and output pass/fail checks."""
    results = gather_diagnostics()
    all_passed = True

    for result in results:
        symbol = "✅" if result.passed else "❌"
        click.echo(f"{symbol} {result.name}")
        if result.details:
            for detail in result.details:
                click.echo(f"   • {detail}")
        all_passed = all_passed and result.passed

    sys.exit(0 if all_passed else 1)


def main() -> None:  # pragma: no cover
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
