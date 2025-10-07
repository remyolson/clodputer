# Copyright (c) 2025 Rémy Olson
"""
Cron integration utilities for Clodputer.

Responsibilities:
- Validate cron expressions defined in task configurations
- Generate cron entries that enqueue Clodputer tasks on schedule
- Install/uninstall the Clodputer-managed section in the user's crontab
- Provide diagnostics helpers for the CLI `doctor` command
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import psutil

from .config import TaskConfig
from .queue import ensure_queue_dir

CRON_SECTION_BEGIN = "# >>> BEGIN CLODPUTER JOBS >>>"
CRON_SECTION_END = "# <<< END CLODPUTER JOBS <<<"
CRON_SECTION_HEADER = "# Managed by Clodputer. Do not edit manually."

CRON_BACKUP_DIR = Path.home() / ".clodputer" / "backups"
CRON_LOG_FILE = Path.home() / ".clodputer" / "cron.log"

CRON_MACROS = {
    "@yearly",
    "@annually",
    "@monthly",
    "@weekly",
    "@daily",
    "@midnight",
    "@hourly",
}

CRON_FIELD_PATTERN = re.compile(r"^(\*|\d+|\d+-\d+|\*/\d+|\d+(,\d+)*)(/(\d+))?$")


class CronError(RuntimeError):
    """Raised when cron installation or validation fails."""


def _timestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_cron_expression(expression: str) -> bool:
    expression = expression.strip()
    if not expression:
        return False
    if expression in CRON_MACROS:
        return True
    fields = expression.split()
    if len(fields) not in (5, 6):
        return False
    for field in fields:
        if field == "@reboot":
            continue
        if not CRON_FIELD_PATTERN.match(field):
            return False
    return True


def _clodputer_binary() -> str:
    binary = shutil.which("clodputer")
    if binary:
        return binary
    return f"{sys.executable} -m clodputer.cli"


def _format_command(task: TaskConfig) -> str:
    binary = _clodputer_binary()
    priority_flag = f"--priority {task.priority}" if task.priority == "high" else ""
    parts = [
        binary,
        "run",
        task.name,
        priority_flag,
    ]
    command = " ".join(part for part in parts if part)

    env_prefix = []
    claude_bin_env = os.getenv("CLODPUTER_CLAUDE_BIN")
    if claude_bin_env:
        env_prefix.append(f"CLODPUTER_CLAUDE_BIN={shlex.quote(claude_bin_env)}")
    extra_args = os.getenv("CLODPUTER_EXTRA_ARGS")
    if extra_args:
        env_prefix.append(f"CLODPUTER_EXTRA_ARGS={shlex.quote(extra_args)}")

    if env_prefix:
        command = " ".join(env_prefix) + " " + command

    command += f" >> {CRON_LOG_FILE} 2>&1"
    return command


def _timezone_line(timezone: Optional[str]) -> Optional[str]:
    if timezone:
        return f"CRON_TZ={timezone}"
    return None


def generate_cron_section(tasks: Sequence[TaskConfig]) -> str:
    jobs = [task for task in tasks if task.enabled and task.schedule]
    if not jobs:
        return ""

    lines: List[str] = [
        CRON_SECTION_BEGIN,
        CRON_SECTION_HEADER,
        f"# Generated: {_timestamp()}",
    ]

    for task in jobs:
        schedule = task.schedule
        assert schedule is not None
        if not validate_cron_expression(schedule.expression):
            raise CronError(f"Invalid cron expression '{schedule.expression}' for task {task.name}")

        lines.append(f"# Task: {task.name}")
        tz_line = _timezone_line(schedule.timezone)
        if tz_line:
            lines.append(tz_line)
        lines.append(f"{schedule.expression} {_format_command(task)}")
        lines.append("")  # blank line between jobs

    lines.append(CRON_SECTION_END)
    return "\n".join(lines).strip() + "\n"


def _call_crontab(
    args: List[str], input_text: Optional[str] = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["crontab", *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def read_crontab() -> str:
    result = _call_crontab(["-l"])
    if result.returncode != 0:
        if "no crontab for" in (result.stderr or "").lower():
            return ""
        raise CronError(f"Failed to read crontab: {result.stderr.strip()}")
    return result.stdout


def _write_crontab(content: str) -> None:
    result = _call_crontab(["-"], input_text=content)
    if result.returncode != 0:
        raise CronError(f"Failed to install crontab: {result.stderr.strip()}")


def _remove_existing_section(crontab: str) -> str:
    if CRON_SECTION_BEGIN not in crontab:
        return crontab
    pattern = re.compile(
        rf"{re.escape(CRON_SECTION_BEGIN)}.*?{re.escape(CRON_SECTION_END)}\n?",
        re.DOTALL,
    )
    return pattern.sub("", crontab).strip() + ("\n" if crontab.strip() else "")


def backup_crontab(current_content: str) -> Path:
    ensure_queue_dir(CRON_BACKUP_DIR.parent)
    CRON_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    path = CRON_BACKUP_DIR / f"crontab-{timestamp}.bak"
    path.write_text(current_content, encoding="utf-8")
    return path


def install_cron_jobs(tasks: Sequence[TaskConfig]) -> dict:
    section = generate_cron_section(tasks)
    current = read_crontab()
    cleaned = _remove_existing_section(current)
    backup_path = backup_crontab(current)

    if section:
        new_content = (
            cleaned + "\n" if cleaned and not cleaned.endswith("\n") else cleaned
        ) + section
    else:
        new_content = cleaned

    _write_crontab(new_content)
    return {
        "installed": len([t for t in tasks if t.enabled and t.schedule]),
        "backup": str(backup_path),
        "section_written": bool(section),
    }


def uninstall_cron_jobs() -> dict:
    current = read_crontab()
    if CRON_SECTION_BEGIN not in current:
        return {"removed": False, "backup": None}
    cleaned = _remove_existing_section(current)
    backup_path = backup_crontab(current)
    _write_crontab(cleaned)
    return {"removed": True, "backup": str(backup_path)}


def cron_section_present() -> bool:
    try:
        current = read_crontab()
    except CronError:
        return False
    return CRON_SECTION_BEGIN in current and CRON_SECTION_END in current


def is_cron_daemon_running() -> bool:
    for proc in psutil.process_iter(["name"]):
        name = (proc.info.get("name") or "").lower()
        if name in {"cron", "crond"}:
            return True
    return False


def scheduled_tasks(tasks: Iterable[TaskConfig]) -> List[TaskConfig]:
    return [task for task in tasks if task.enabled and task.schedule]


__all__ = [
    "CronError",
    "validate_cron_expression",
    "generate_cron_section",
    "install_cron_jobs",
    "uninstall_cron_jobs",
    "cron_section_present",
    "is_cron_daemon_running",
    "scheduled_tasks",
]
