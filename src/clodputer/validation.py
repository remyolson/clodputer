# Copyright (c) 2025 Rémy Olson
"""
Task validation and dry-run checking.

Provides comprehensive validation beyond Pydantic schema checks:
- Schedule syntax validation
- MCP tool availability
- Resource usage warnings
- Best practice recommendations
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Literal, Optional

from croniter import croniter

from .config import ConfigError, TaskConfig, load_task_by_name, TASKS_DIR


class ValidationIssue:
    """A validation issue found during dry-run."""

    def __init__(
        self,
        level: Literal["error", "warning", "info"],
        message: str,
        field: Optional[str] = None,
    ):
        self.level = level
        self.message = message
        self.field = field

    def __repr__(self) -> str:
        if self.field:
            return f"{self.level.upper()}: {self.field}: {self.message}"
        return f"{self.level.upper()}: {self.message}"


class ValidationResult:
    """Result of task validation."""

    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.config: Optional[TaskConfig] = None

    def add_error(self, message: str, field: Optional[str] = None) -> None:
        self.issues.append(ValidationIssue("error", message, field))

    def add_warning(self, message: str, field: Optional[str] = None) -> None:
        self.issues.append(ValidationIssue("warning", message, field))

    def add_info(self, message: str, field: Optional[str] = None) -> None:
        self.issues.append(ValidationIssue("info", message, field))

    @property
    def is_valid(self) -> bool:
        """True if no errors found."""
        return not any(issue.level == "error" for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        """True if warnings found."""
        return any(issue.level == "warning" for issue in self.issues)

    def get_errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    def get_warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]

    def get_infos(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == "info"]


def _check_schedule(config: TaskConfig, result: ValidationResult) -> None:
    """Validate schedule configuration."""
    if not config.schedule:
        result.add_info("No schedule configured (task will only run manually)", "schedule")
        return

    # Validate cron expression
    try:
        croniter(config.schedule.expression)
    except (ValueError, KeyError) as exc:
        result.add_error(f"Invalid cron expression: {exc}", "schedule.expression")
        return

    # Warn about very frequent schedules
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    cron = croniter(config.schedule.expression, now)
    next_run = cron.get_next(datetime)
    interval_seconds = (next_run - now).total_seconds()

    if interval_seconds < 60:
        result.add_warning(
            f"Schedule runs very frequently (every {interval_seconds:.0f}s). "
            "Consider if this is intentional.",
            "schedule.expression",
        )


def _check_mcp_tools(config: TaskConfig, result: ValidationResult) -> None:
    """Check if MCP tools are available."""
    mcp_tools = [t for t in config.task.allowed_tools if t.startswith("mcp__")]

    if not mcp_tools:
        return

    # Try to get list of available MCP tools
    try:
        # Run: claude mcp list --format json
        proc = subprocess.run(
            ["claude", "mcp", "list", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if proc.returncode != 0:
            result.add_warning(
                "Could not verify MCP tools (claude mcp list failed). "
                "Ensure MCP servers are configured.",
                "task.allowed_tools",
            )
            return

        # Parse available MCPs
        import json

        try:
            mcp_list = json.loads(proc.stdout)
            available_mcps = set()

            # MCP tool names are like: mcp__server-name__tool-name
            # Extract server names from available MCPs
            for mcp in mcp_list:
                server_name = mcp.get("name", "")
                if server_name:
                    available_mcps.add(f"mcp__{server_name}")

            # Check each MCP tool
            for tool in mcp_tools:
                # Extract server name from tool (mcp__gmail__send_email -> mcp__gmail)
                parts = tool.split("__")
                if len(parts) >= 2:
                    server_prefix = f"mcp__{parts[1]}"
                    if server_prefix not in available_mcps and tool not in available_mcps:
                        result.add_warning(
                            f"MCP tool '{tool}' may not be available. "
                            f"Available MCP servers: {', '.join(sorted(available_mcps)) or 'none'}",
                            "task.allowed_tools",
                        )

        except json.JSONDecodeError:
            result.add_warning(
                "Could not parse MCP list. Ensure claude mcp is configured correctly.",
                "task.allowed_tools",
            )

    except (subprocess.TimeoutExpired, FileNotFoundError):
        result.add_info(
            "Could not verify MCP tools (claude command not available)", "task.allowed_tools"
        )


def _check_resources(config: TaskConfig, result: ValidationResult) -> None:
    """Check resource configuration and warn about potential issues."""

    # Check timeout
    if config.task.timeout > 3600:  # 1 hour
        hours = config.task.timeout / 3600
        result.add_warning(
            f"Very long timeout configured ({hours:.1f} hours). "
            "Consider if this is intentional.",
            "task.timeout",
        )

    if config.task.timeout < 60:  # 1 minute
        result.add_warning(
            f"Very short timeout ({config.task.timeout}s). "
            "Task may not have enough time to complete.",
            "task.timeout",
        )

    # Check retry configuration
    if config.task.max_retries > 5:
        result.add_warning(
            f"Many retries configured ({config.task.max_retries}). "
            "Consider if this is intentional.",
            "task.max_retries",
        )

    # Check if using state but not enabled
    if "state" in config.task.prompt.lower() and not config.schedule:
        result.add_info(
            "Prompt mentions 'state' but task has no schedule. "
            "State is most useful for scheduled tasks.",
            "task.prompt",
        )


def _check_best_practices(config: TaskConfig, result: ValidationResult) -> None:
    """Check best practices and provide recommendations."""

    # Check prompt length
    if len(config.task.prompt) < 20:
        result.add_warning(
            "Very short prompt. Consider adding more context for better results.", "task.prompt"
        )

    if len(config.task.prompt) > 2000:
        result.add_info(
            f"Long prompt ({len(config.task.prompt)} chars). "
            "Consider breaking into multiple tasks if possible.",
            "task.prompt",
        )

    # Check if no tools specified
    if not config.task.allowed_tools:
        result.add_warning(
            "No tools specified. Task will have very limited capabilities.", "task.allowed_tools"
        )

    # Check for disabled task with schedule
    if not config.enabled and config.schedule:
        result.add_info("Task is disabled but has a schedule configured", "enabled")


def _check_dependencies(config: TaskConfig, result: ValidationResult, tasks_dir: Path) -> None:
    """Validate task dependencies."""
    if not config.depends_on:
        return

    from .dependencies import validate_dependencies

    # Validate dependencies
    dep_errors = validate_dependencies(config, tasks_dir)

    for error in dep_errors:
        result.add_error(error, "depends_on")


def validate_task(
    task_name: str,
    tasks_dir: Path = TASKS_DIR,
    check_mcp: bool = True,
) -> ValidationResult:
    """Perform comprehensive validation on a task.

    Args:
        task_name: Name of task to validate
        tasks_dir: Directory containing task configs
        check_mcp: Whether to check MCP tool availability (requires claude CLI)

    Returns:
        ValidationResult with all issues found
    """
    result = ValidationResult()

    # Load and validate schema
    try:
        config = load_task_by_name(task_name, tasks_dir)
        result.config = config
    except ConfigError as exc:
        result.add_error(str(exc))
        return result

    # Perform additional checks
    _check_schedule(config, result)
    _check_dependencies(config, result, tasks_dir)
    _check_resources(config, result)
    _check_best_practices(config, result)

    if check_mcp:
        _check_mcp_tools(config, result)

    return result


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "validate_task",
]
