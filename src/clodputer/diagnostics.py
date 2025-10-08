"""Shared diagnostics helpers for Clodputer doctor checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .config import TASKS_DIR, ensure_tasks_dir, validate_all_tasks
from .cron import (
    CronError,
    cron_section_present,
    generate_cron_section,
    is_cron_daemon_running,
    preview_schedule,
    scheduled_tasks,
)
from .environment import claude_cli_path, onboarding_state
from .logger import LOG_FILE
from .queue import QueueCorruptionError, QueueManager, lockfile_status
from .watcher import (
    WATCHER_LOG_FILE,
    file_watch_tasks,
    is_daemon_running as watcher_is_running,
)


@dataclass
class CheckResult:
    """A single diagnostic check result."""

    name: str
    passed: bool
    details: List[str] = field(default_factory=list)


def gather_diagnostics() -> List[CheckResult]:
    """Collect diagnostics data for doctor command and onboarding summary."""

    ensure_tasks_dir()
    results: List[CheckResult] = []

    # Base directory / tasks folder
    tasks_dir_exists = TASKS_DIR.exists()
    task_details = [] if tasks_dir_exists else [f"Expected tasks directory at {TASKS_DIR}"]
    results.append(CheckResult("Tasks directory exists", tasks_dir_exists, task_details))

    # Queue lock
    lock_status = lockfile_status()
    lock_ok = (not lock_status["locked"]) or (lock_status["locked"] and not lock_status["stale"])
    lock_details: List[str] = []
    if lock_status["locked"]:
        state = "stale" if lock_status["stale"] else "held"
        lock_details.append(f"Lockfile {lock_status['path']} is {state}.")
    results.append(CheckResult("Queue lockfile", lock_ok, lock_details))

    # Queue integrity
    queue_ok, queue_errors = True, []
    try:
        queue_manager = QueueManager(auto_lock=False)
        queue_ok, queue_errors = queue_manager.validate_state()
    except QueueCorruptionError as exc:
        queue_ok = False
        queue_errors = [str(exc)]
    results.append(CheckResult("Queue integrity", queue_ok, queue_errors))

    # Task configs and scheduling/watcher data
    configs, config_errors = validate_all_tasks()
    config_details = [f"{path}: {err}" for path, err in config_errors]
    results.append(CheckResult("Task configs valid", not config_errors, config_details))

    scheduled = scheduled_tasks(configs)
    watch_tasks = file_watch_tasks(configs)

    # Cron-related checks
    cron_running = is_cron_daemon_running()
    cron_details = [] if cron_running else ["Cron service not detected (cron/crond)."]
    results.append(CheckResult("Cron daemon running", cron_running, cron_details))

    cron_installed = (not scheduled) or cron_section_present()
    cron_installed_details = (
        []
        if cron_installed or not scheduled
        else ["No Clodputer-managed cron section detected; run `clodputer install`."]
    )
    results.append(
        CheckResult("Clodputer cron jobs installed", cron_installed, cron_installed_details)
    )

    cron_definition_errors: List[str] = []
    cron_definitions_ok = True
    if scheduled:
        try:
            generate_cron_section(scheduled)
        except CronError as exc:
            cron_definitions_ok = False
            cron_definition_errors.append(str(exc))
    results.append(
        CheckResult("Cron job definitions valid", cron_definitions_ok, cron_definition_errors)
    )

    schedule_preview_errors: List[str] = []
    schedule_preview_ok = True
    if scheduled:
        try:
            for entry in scheduled:
                preview_schedule(entry, count=1)
        except CronError as exc:
            schedule_preview_ok = False
            schedule_preview_errors.append(str(exc))
    results.append(
        CheckResult("Cron schedule preview", schedule_preview_ok, schedule_preview_errors)
    )

    # Watcher-related checks
    watcher_running = (not watch_tasks) or watcher_is_running()
    watcher_details = [] if watcher_running or not watch_tasks else ["Watcher daemon not running."]
    results.append(CheckResult("Watcher daemon running", watcher_running, watcher_details))

    watch_path_details: List[str] = []
    watch_paths_exist = True
    for task in watch_tasks:
        trigger = task.trigger
        assert trigger is not None and trigger.type == "file_watch"
        path = Path(trigger.path).expanduser()
        if not path.exists():
            watch_paths_exist = False
            watch_path_details.append(f"{task.name}: missing {path}")
    results.append(CheckResult("Watch paths exist", watch_paths_exist, watch_path_details))

    watcher_log_dir_ok = WATCHER_LOG_FILE.parent.exists()
    watcher_log_details = (
        [] if watcher_log_dir_ok else [f"Watcher log directory missing: {WATCHER_LOG_FILE.parent}"]
    )
    results.append(
        CheckResult("Watcher log directory available", watcher_log_dir_ok, watcher_log_details)
    )

    if LOG_FILE.exists():
        results.append(CheckResult("Execution log readable", LOG_FILE.exists(), []))

    # Environment / onboarding state
    cli_path = claude_cli_path(None)
    cli_details: List[str] = []
    cli_pass = False
    if cli_path:
        cli_details.append(f"Configured path: {cli_path}")
        cli_pass = Path(cli_path).exists()
        if not cli_pass:
            cli_details.append("Configured Claude CLI path does not exist on disk.")
    else:
        cli_details.append("No stored Claude CLI path found. Run `clodputer init`.")
    results.append(CheckResult("Claude CLI path configured", cli_pass, cli_details))

    state = onboarding_state()
    last_run = state.get("onboarding_last_run")
    run_count = state.get("onboarding_runs")
    onboarding_details: List[str] = []
    onboarding_pass = bool(last_run)
    if last_run:
        onboarding_details.append(f"Last onboarding run: {last_run}")
    else:
        onboarding_details.append("Onboarding has not been completed yet.")
    if run_count is not None:
        onboarding_details.append(f"Recorded onboarding runs: {run_count}")
    results.append(
        CheckResult("Onboarding completion recorded", onboarding_pass, onboarding_details)
    )

    return results


__all__ = ["CheckResult", "gather_diagnostics"]
