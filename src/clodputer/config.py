# Copyright (c) 2025 Rémy Olson
"""
Task configuration loading and validation.

Phase 1 requirements call for Pydantic-backed validation, environment variable
substitution, and helper utilities to discover task definitions stored in
``~/.clodputer/tasks``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

TASKS_DIR = Path.home() / ".clodputer" / "tasks"

ENV_PATTERN = re.compile(r"\{\{\s*env\.([A-Z0-9_]+)\s*\}\}")


def ensure_tasks_dir(path: Path = TASKS_DIR) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _substitute_env(value: Any) -> Any:
    if isinstance(value, str):

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in os.environ:
                raise KeyError(f"Environment variable {key} not set")
            return os.environ[key]

        return ENV_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: _substitute_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_env(item) for item in value]
    return value


class ScheduleConfig(BaseModel):
    type: Literal["cron"]
    expression: str
    timezone: Optional[str] = None


class ManualTrigger(BaseModel):
    type: Literal["manual"] = "manual"


class FileWatchTrigger(BaseModel):
    type: Literal["file_watch"] = "file_watch"
    path: str
    pattern: str = "*"
    event: Literal["created", "modified", "deleted"] = "created"
    debounce: int = 1000


class IntervalTrigger(BaseModel):
    type: Literal["interval"] = "interval"
    seconds: int = Field(gt=0)


TriggerConfig = Union[ManualTrigger, FileWatchTrigger, IntervalTrigger]


KNOWN_CORE_TOOLS = {
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Search",
    "Terminal",
    "List",
    "Delete",
    "Code",
    "FileSystem",
}


def _is_valid_tool(name: str) -> bool:
    return name in KNOWN_CORE_TOOLS or name.startswith("mcp__")


class TaskActions(BaseModel):
    log: Optional[str] = None
    notify: Optional[bool] = None
    retry: Optional[bool] = None


class TaskSpec(BaseModel):
    prompt: str
    allowed_tools: List[str] = Field(default_factory=list)
    disallowed_tools: List[str] = Field(default_factory=list)
    permission_mode: Literal["acceptEdits", "rejectEdits", "prompt"] = "acceptEdits"
    timeout: int = Field(default=3600, gt=0)
    context: Dict[str, Any] = Field(default_factory=dict)
    mcp_config: Optional[str] = None
    max_retries: int = Field(default=0, ge=0)
    retry_backoff_seconds: int = Field(default=60, ge=1)

    @model_validator(mode="after")
    def validate_tools(self) -> "TaskSpec":
        overlap = set(self.allowed_tools) & set(self.disallowed_tools)
        if overlap:
            raise ValueError(
                f"Tools cannot be both allowed and disallowed: {', '.join(sorted(overlap))}"
            )

        invalid_allowed = [tool for tool in self.allowed_tools if not _is_valid_tool(tool)]
        invalid_disallowed = [tool for tool in self.disallowed_tools if not _is_valid_tool(tool)]
        if invalid_allowed or invalid_disallowed:
            problems = []
            if invalid_allowed:
                problems.append(f"Unknown allowed_tools: {', '.join(invalid_allowed)}")
            if invalid_disallowed:
                problems.append(f"Unknown disallowed_tools: {', '.join(invalid_disallowed)}")
            hint = (
                "Built-in tools are limited to "
                f"{', '.join(sorted(KNOWN_CORE_TOOLS))}. "
                "Custom MCP tools must be prefixed with 'mcp__'. "
                "See docs/user/configuration.md for guidance."
            )
            raise ValueError("; ".join(problems) + ". " + hint)
        return self


class TaskConfig(BaseModel):
    name: str
    description: Optional[str] = None
    enabled: bool = True
    schedule: Optional[ScheduleConfig] = None
    trigger: Optional[TriggerConfig] = None
    priority: Literal["normal", "high"] = "normal"
    task: TaskSpec
    on_success: List[TaskActions] = Field(default_factory=list)
    on_failure: List[TaskActions] = Field(default_factory=list)
    created: Optional[str] = None
    created_by: Optional[str] = None
    last_run: Optional[str] = None
    run_count: Optional[int] = None
    success_rate: Optional[float] = None
    total_cost: Optional[float] = None

    model_config = {"extra": "ignore"}


class ConfigError(RuntimeError):
    """Raised when configuration files cannot be loaded or parsed."""


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Failed to read config {path}") from exc

    try:
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Config {path} must be a mapping at the top level")
    return data


def load_task_config(path: Path) -> TaskConfig:
    raw = _load_yaml(path)
    try:
        substituted = _substitute_env(raw)
    except KeyError as exc:
        raise ConfigError(f"Missing environment variable for placeholder: {exc}") from exc
    try:
        return TaskConfig.model_validate(substituted)
    except ValidationError as exc:
        raise ConfigError(_format_validation_errors(path, exc)) from exc


def load_task_by_name(name: str, tasks_dir: Path = TASKS_DIR) -> TaskConfig:
    ensure_tasks_dir(tasks_dir)
    candidate = tasks_dir / f"{name}.yaml"
    if not candidate.exists():
        raise ConfigError(f"Task config not found for {name!r} at {candidate}")
    return load_task_config(candidate)


def list_task_names(tasks_dir: Path = TASKS_DIR) -> List[str]:
    ensure_tasks_dir(tasks_dir)
    names: List[str] = []
    for path in sorted(tasks_dir.glob("*.yaml")):
        names.append(path.stem)
    return names


def load_all_tasks(tasks_dir: Path = TASKS_DIR) -> List[TaskConfig]:
    configs: List[TaskConfig] = []
    errors: List[str] = []
    for name in list_task_names(tasks_dir):
        try:
            configs.append(load_task_by_name(name, tasks_dir=tasks_dir))
        except ConfigError as exc:
            errors.append(str(exc))
    if errors:
        error_text = "\n".join(errors)
        raise ConfigError(f"One or more task configs failed to load:\n{error_text}")
    return configs


def validate_all_tasks(
    tasks_dir: Path = TASKS_DIR,
) -> tuple[List[TaskConfig], List[tuple[Path, str]]]:
    ensure_tasks_dir(tasks_dir)
    configs: List[TaskConfig] = []
    errors: List[tuple[Path, str]] = []
    for path in sorted(tasks_dir.glob("*.yaml")):
        try:
            configs.append(load_task_config(path))
        except ConfigError as exc:
            errors.append((path, str(exc)))
    return configs, errors


def _format_validation_errors(path: Path, exc: ValidationError) -> str:
    lines = [f"Validation error in {path}:"]
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", ())) or "root"
        message = error.get("msg", "Invalid value")
        lines.append(f"  - {location}: {message}")
    return "\n".join(lines)


__all__ = [
    "ConfigError",
    "TaskConfig",
    "TaskSpec",
    "TaskActions",
    "ScheduleConfig",
    "TriggerConfig",
    "load_task_by_name",
    "load_all_tasks",
    "validate_all_tasks",
    "list_task_names",
    "ensure_tasks_dir",
]
