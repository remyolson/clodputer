"""Catch-up logic for missed scheduled tasks."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Optional

from croniter import croniter

from .config import ScheduleConfig, TaskConfig
from .task_state import TaskState, get_task_state


class MissedTask:
    """Represents a task that missed its scheduled run time."""

    def __init__(
        self,
        task_name: str,
        missed_at: str,
        catch_up_mode: str,
    ):
        """Initialize missed task.

        Args:
            task_name: Name of the task.
            missed_at: ISO 8601 timestamp of when the task should have run.
            catch_up_mode: How to handle the miss ("run_once" or "run_all").
        """
        self.task_name = task_name
        self.missed_at = missed_at
        self.catch_up_mode = catch_up_mode


def detect_missed_tasks(tasks: List[TaskConfig]) -> List[MissedTask]:
    """Detect tasks that missed their scheduled run times.

    Args:
        tasks: List of task configurations to check.

    Returns:
        List of MissedTask objects for tasks that should be caught up.

    Example:
        >>> tasks = load_all_tasks()
        >>> missed = detect_missed_tasks(tasks)
        >>> for miss in missed:
        ...     print(f"[CATCH-UP] {miss.task_name}: missed run at {miss.missed_at}")
    """
    missed: List[MissedTask] = []
    now = datetime.now(timezone.utc)

    for task in tasks:
        if not task.enabled:
            continue

        # Only cron schedules support catch-up
        if not task.schedule or task.schedule.type != "cron":
            continue

        # Skip if catch_up is "skip" (default)
        if task.schedule.catch_up == "skip":
            continue

        # Get task state
        state = get_task_state(task.name)
        if not state or not state.last_success:
            # Task never ran successfully - don't catch up
            continue

        # Parse last successful run
        try:
            last_success_dt = datetime.fromisoformat(state.last_success.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            # Invalid timestamp - skip
            continue

        # Calculate missed runs
        missed_runs = _calculate_missed_runs(
            task.schedule,
            last_success_dt,
            now,
            task.schedule.catch_up,
        )

        # Create MissedTask entries
        for missed_time in missed_runs:
            missed_iso = missed_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            missed.append(
                MissedTask(
                    task_name=task.name,
                    missed_at=missed_iso,
                    catch_up_mode=task.schedule.catch_up,
                )
            )

    return missed


def _calculate_missed_runs(
    schedule: ScheduleConfig,
    last_success: datetime,
    now: datetime,
    catch_up_mode: str,
) -> List[datetime]:
    """Calculate which scheduled runs were missed.

    Args:
        schedule: Schedule configuration.
        last_success: Timestamp of last successful run.
        now: Current time.
        catch_up_mode: "run_once" or "run_all".

    Returns:
        List of datetime objects for missed runs that should be caught up.
    """
    try:
        # Create croniter starting from last successful run
        cron = croniter(schedule.expression, last_success)

        # Get all missed occurrences
        missed = []
        next_run = cron.get_next(datetime)

        while next_run < now:
            missed.append(next_run)
            next_run = cron.get_next(datetime)

        # Apply catch-up mode
        if catch_up_mode == "run_once":
            # Only catch up the most recent miss
            return [missed[-1]] if missed else []
        elif catch_up_mode == "run_all":
            # Catch up all missed runs
            return missed
        else:
            # "skip" or unknown - no catch-up
            return []

    except (ValueError, KeyError):
        # Invalid cron expression - no missed runs
        return []


def calculate_next_expected_run(
    schedule: ScheduleConfig, after: Optional[datetime] = None
) -> Optional[str]:
    """Calculate the next expected run time for a schedule.

    Args:
        schedule: Schedule configuration.
        after: Calculate next run after this time (defaults to now).

    Returns:
        ISO 8601 timestamp of next expected run, or None if calculation fails.

    Example:
        >>> schedule = ScheduleConfig(type="cron", expression="0 9 * * *")
        >>> next_run = calculate_next_expected_run(schedule)
        >>> print(f"Next run: {next_run}")
    """
    if schedule.type != "cron":
        return None

    if after is None:
        after = datetime.now(timezone.utc)

    try:
        cron = croniter(schedule.expression, after)
        next_run = cron.get_next(datetime)
        return next_run.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, KeyError):
        return None


def should_catch_up(task: TaskConfig) -> bool:
    """Check if a task should use catch-up behavior.

    Args:
        task: Task configuration.

    Returns:
        True if task has catch-up enabled and conditions are met.
    """
    if not task.enabled:
        return False

    if not task.schedule or task.schedule.type != "cron":
        return False

    return task.schedule.catch_up in ("run_once", "run_all")


__all__ = [
    "MissedTask",
    "detect_missed_tasks",
    "calculate_next_expected_run",
    "should_catch_up",
]
