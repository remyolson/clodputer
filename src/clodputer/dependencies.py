# Copyright (c) 2025 Rémy Olson
"""
Task dependency validation and resolution.

Provides:
- Dependency cycle detection
- Task existence validation
- Dependency resolution order
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .config import ConfigError, TaskConfig, load_task_by_name, TASKS_DIR


class DependencyError(Exception):
    """Raised when dependency validation fails."""
    pass


def validate_dependencies(
    task: TaskConfig,
    tasks_dir: Path = TASKS_DIR,
    all_tasks: Optional[List[TaskConfig]] = None
) -> List[str]:
    """Validate task dependencies.

    Args:
        task: Task configuration to validate
        tasks_dir: Directory containing task configs
        all_tasks: Optional list of all tasks (for efficiency in batch validation)

    Returns:
        List of validation errors (empty if valid)

    Raises:
        DependencyError: If validation fails critically
    """
    errors = []

    if not task.depends_on:
        return errors

    # Build map of task names for quick lookup
    if all_tasks is not None:
        task_map = {t.name: t for t in all_tasks}
    else:
        task_map = {}

    # Check each dependency
    for dep in task.depends_on:
        # Validate referenced task exists
        if dep.task not in task_map:
            try:
                # Try to load the task
                load_task_by_name(dep.task, tasks_dir)
                task_map[dep.task] = load_task_by_name(dep.task, tasks_dir)
            except ConfigError:
                errors.append(f"Dependency task '{dep.task}' does not exist")
                continue

        # Validate max_age if specified
        if dep.max_age is not None and dep.max_age <= 0:
            errors.append(f"Dependency '{dep.task}': max_age must be positive, got {dep.max_age}")

        # Check for self-dependency
        if dep.task == task.name:
            errors.append(f"Task cannot depend on itself: {task.name}")

    # Check for circular dependencies
    if all_tasks is None:
        # Load all tasks for cycle detection
        from .config import load_all_tasks
        try:
            all_tasks = load_all_tasks(tasks_dir)
        except ConfigError as exc:
            errors.append(f"Could not load all tasks for cycle detection: {exc}")
            return errors

    cycles = detect_dependency_cycles(task, all_tasks)
    if cycles:
        errors.append(f"Circular dependency detected: {' -> '.join(cycles)}")

    return errors


def detect_dependency_cycles(
    task: TaskConfig,
    all_tasks: List[TaskConfig]
) -> List[str]:
    """Detect circular dependencies starting from a task.

    Args:
        task: Task to check
        all_tasks: All available tasks

    Returns:
        List forming a cycle path if found, empty list if no cycle
    """
    task_map = {t.name: t for t in all_tasks}

    # DFS to detect cycles
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    path: List[str] = []

    def dfs(task_name: str) -> bool:
        """Returns True if cycle detected."""
        if task_name in rec_stack:
            # Found a cycle - build the cycle path
            cycle_start = path.index(task_name)
            path.append(task_name)  # Complete the cycle
            return True

        if task_name in visited:
            return False

        visited.add(task_name)
        rec_stack.add(task_name)
        path.append(task_name)

        # Check dependencies
        if task_name in task_map:
            current_task = task_map[task_name]
            for dep in current_task.depends_on:
                if dfs(dep.task):
                    return True

        path.pop()
        rec_stack.remove(task_name)
        return False

    if dfs(task.name):
        # Extract just the cycle portion
        cycle_start_idx = 0
        for i, name in enumerate(path):
            if name == path[-1] and i < len(path) - 1:
                cycle_start_idx = i
                break
        return path[cycle_start_idx:]

    return []


def get_dependency_order(tasks: List[TaskConfig]) -> List[TaskConfig]:
    """Get tasks in dependency order (topological sort).

    Args:
        tasks: List of tasks to order

    Returns:
        Tasks in dependency order (dependencies first)

    Raises:
        DependencyError: If circular dependency detected
    """
    task_map = {t.name: t for t in tasks}

    # Build adjacency list (task -> tasks that depend on it)
    in_degree: Dict[str, int] = defaultdict(int)
    adj_list: Dict[str, List[str]] = defaultdict(list)

    # Initialize all tasks with in_degree 0
    for task in tasks:
        if task.name not in in_degree:
            in_degree[task.name] = 0

    # Build graph
    for task in tasks:
        for dep in task.depends_on:
            if dep.task not in task_map:
                raise DependencyError(
                    f"Task '{task.name}' depends on non-existent task '{dep.task}'"
                )
            adj_list[dep.task].append(task.name)
            in_degree[task.name] += 1

    # Kahn's algorithm for topological sort
    queue: List[str] = []
    for task_name, degree in in_degree.items():
        if degree == 0:
            queue.append(task_name)

    sorted_order: List[str] = []
    while queue:
        current = queue.pop(0)
        sorted_order.append(current)

        for dependent in adj_list[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # Check if all tasks were processed (no cycles)
    if len(sorted_order) != len(tasks):
        # There's a cycle
        remaining = [t.name for t in tasks if t.name not in sorted_order]
        raise DependencyError(
            f"Circular dependency detected among tasks: {', '.join(remaining)}"
        )

    # Return tasks in sorted order
    return [task_map[name] for name in sorted_order]


def check_dependency_satisfied(
    dependency_task_name: str,
    condition: str,
    max_age: Optional[int],
    outputs_dir: Path
) -> Tuple[bool, Optional[str]]:
    """Check if a dependency condition is satisfied.

    Args:
        dependency_task_name: Name of the dependency task
        condition: Condition type ("success", "complete", "always")
        max_age: Maximum age in seconds (None for no limit)
        outputs_dir: Directory containing task outputs

    Returns:
        Tuple of (satisfied: bool, reason: Optional[str])
    """
    from .reports import load_latest_report

    # Load latest execution report
    latest_report = load_latest_report(dependency_task_name, outputs_dir)

    if latest_report is None:
        return False, f"Dependency '{dependency_task_name}' has never run"

    # Check condition
    status = latest_report.get("status", "unknown")

    if condition == "success":
        if status != "success":
            return False, f"Dependency '{dependency_task_name}' did not succeed (status: {status})"
    elif condition == "complete":
        if status not in ("success", "failure", "timeout"):
            return False, f"Dependency '{dependency_task_name}' has not completed (status: {status})"
    # condition == "always" - no status check needed

    # Check max_age if specified
    if max_age is not None:
        # Get timestamp from report
        timestamp_str = latest_report.get("timestamp")
        if timestamp_str is None:
            return False, f"Dependency '{dependency_task_name}' report has no timestamp"

        try:
            # Parse ISO format timestamp
            report_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            if report_time.tzinfo is None:
                report_time = report_time.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            age_seconds = (now - report_time).total_seconds()

            if age_seconds > max_age:
                return False, f"Dependency '{dependency_task_name}' is too old ({age_seconds:.0f}s > {max_age}s)"
        except (ValueError, AttributeError) as exc:
            return False, f"Dependency '{dependency_task_name}' has invalid timestamp: {exc}"

    return True, None


__all__ = [
    "DependencyError",
    "validate_dependencies",
    "detect_dependency_cycles",
    "get_dependency_order",
    "check_dependency_satisfied",
]
