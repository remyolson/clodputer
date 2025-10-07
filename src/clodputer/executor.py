"""
Tracer bullet implementation for the task executor.

The goal is intentionally narrow: load a single configuration file, build the
Claude Code command, execute it, capture the output, then perform PID-tracked
cleanup on the spawned process tree. This validates the riskiest integration
point before the full infrastructure is built.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from .cleanup import CleanupReport, cleanup_process_tree

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_NAME = "email-management.yaml"


class TaskConfigError(RuntimeError):
    """Raised when the tracer bullet task configuration cannot be loaded."""


def _default_config_path() -> Path:
    override = os.getenv("CLODPUTER_CONFIG_PATH")
    if override:
        return Path(override).expanduser()
    return REPO_ROOT / DEFAULT_CONFIG_NAME


def load_task_config(path: Path | None = None) -> Dict[str, Any]:
    config_path = path or _default_config_path()
    if not config_path.exists():
        raise TaskConfigError(f"Config file not found: {config_path}")

    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TaskConfigError(f"Failed to read config: {config_path}") from exc

    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise TaskConfigError(f"Invalid YAML in {config_path}") from exc

    if not isinstance(loaded, dict):
        raise TaskConfigError("Task configuration must be a mapping at the top level")
    return loaded


def extract_prompt(config: Dict[str, Any]) -> str:
    task = config.get("task")
    if not isinstance(task, dict):
        raise TaskConfigError("Task configuration requires a 'task' mapping")

    prompt = task.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise TaskConfigError("Task configuration requires a non-empty 'task.prompt'")
    return prompt


def build_command(prompt: str) -> List[str]:
    claude_bin = os.getenv("CLODPUTER_CLAUDE_BIN", "claude")
    extra_args = os.getenv("CLODPUTER_EXTRA_ARGS")

    command = [claude_bin, "-p", prompt]

    if extra_args:
        command.extend(extra_args.split())

    return command


def run_tracer_bullet(config_path: Path | None = None) -> Tuple[int, str, str, CleanupReport]:
    """
    Execute the tracer bullet task and return command results plus cleanup report.

    Returns:
        Tuple of (return_code, stdout, stderr, cleanup_report)
    """
    config = load_task_config(config_path)
    prompt = extract_prompt(config)
    command = build_command(prompt)

    logger.info("Executing tracer bullet task with command: %s", command[0])

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Failed to start Claude CLI: {command[0]!r}. "
            "Set CLODPUTER_CLAUDE_BIN to the correct executable."
        ) from exc

    stdout, stderr = process.communicate()
    return_code = process.returncode

    cleanup_report = cleanup_process_tree(process.pid)

    return return_code, stdout, stderr, cleanup_report


def main() -> int:
    logging.basicConfig(
        level=os.getenv("CLODPUTER_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        return_code, stdout, stderr, cleanup_report = run_tracer_bullet()
    except TaskConfigError as exc:
        logger.error("Configuration error: %s", exc)
        return 1
    except RuntimeError as exc:
        logger.error("Execution error: %s", exc)
        return 1

    if stdout:
        print("=== Claude Output (stdout) ===")
        print(stdout)
    if stderr:
        print("=== Claude Output (stderr) ===", file=sys.stderr)
        print(stderr, file=sys.stderr)

    logger.info(
        "Tracer bullet finished (return_code=%s, cleaned=%s processes)",
        return_code,
        cleanup_report.total,
    )
    return return_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
