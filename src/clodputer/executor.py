# Copyright (c) 2025 Rémy Olson
"""
Task execution engine integrating configuration, queue management, and cleanup.

Phase 1 expands the tracer bullet into a reusable executor that can:
- Load task definitions by name using the Pydantic-backed config loader
- Build the Claude CLI command with the appropriate flags
- Execute the task with timeout handling and output parsing
- Update the persistent queue state on success/failure
- Optionally process all pending items in the queue
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Protocol, Tuple
import uuid

from .cleanup import CleanupReport, cleanup_process_tree
from .config import ConfigError, TaskConfig, load_task_by_name, load_task_config
from .environment import claude_cli_path, store_claude_cli_path
from .logger import StructuredLogger
from .metrics import record_failure, record_success
from .queue import LockAcquisitionError, QueueCorruptionError, QueueItem, QueueManager

logger = logging.getLogger(__name__)


class ExecutionLogger(Protocol):
    def task_started(self, task_id: str, task_name: str, metadata: Dict[str, Any]) -> None: ...

    def task_completed(
        self,
        task_id: str,
        task_name: str,
        result: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> None: ...

    def task_failed(
        self,
        task_id: str,
        task_name: str,
        error: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> None: ...


class NullExecutionLogger:
    def task_started(
        self, task_id: str, task_name: str, metadata: Dict[str, Any]
    ) -> None:  # pragma: no cover
        logger.debug("task_started: %s (%s) metadata=%s", task_name, task_id, metadata)

    def task_completed(
        self, task_id: str, task_name: str, result: Dict[str, Any], metadata: Dict[str, Any]
    ) -> None:  # pragma: no cover
        logger.debug(
            "task_completed: %s (%s) result=%s metadata=%s", task_name, task_id, result, metadata
        )

    def task_failed(
        self, task_id: str, task_name: str, error: Dict[str, Any], metadata: Dict[str, Any]
    ) -> None:  # pragma: no cover
        logger.debug(
            "task_failed: %s (%s) error=%s metadata=%s", task_name, task_id, error, metadata
        )


class TaskExecutionError(RuntimeError):
    """Raised when a task fails during execution."""


ExecutionStatus = Literal["success", "failure", "timeout", "error"]


@dataclass
class ExecutionResult:
    task_id: str
    task_name: str
    status: ExecutionStatus
    return_code: Optional[int]
    duration: float
    stdout: str
    stderr: str
    cleanup: CleanupReport
    output_json: Optional[Any]
    output_parse_error: Optional[str] = None
    error: Optional[str] = None


def _resolve_claude_bin() -> str:
    env_override = os.getenv("CLODPUTER_CLAUDE_BIN")
    path = claude_cli_path(env_override)
    if path:
        store_claude_cli_path(path)
        return path
    return "claude"


def _extra_args() -> List[str]:
    extra = os.getenv("CLODPUTER_EXTRA_ARGS")
    if not extra:
        return []
    return shlex.split(extra)


def _extract_json(stdout: str) -> Tuple[Optional[Any], Optional[str]]:
    text = stdout.strip()
    if not text:
        return None, "Claude produced no stdout"

    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        while lines and lines[-1].strip() == "```":
            lines.pop()
        text = "\n".join(lines).strip()

    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def build_command(config: TaskConfig) -> List[str]:
    command: List[str] = [
        _resolve_claude_bin(),
        "-p",
        config.task.prompt,
        "--output-format",
        "json",
    ]

    if config.task.allowed_tools:
        command.extend(["--allowed-tools", ",".join(config.task.allowed_tools)])
    if config.task.disallowed_tools:
        command.extend(["--blocked-tools", ",".join(config.task.disallowed_tools)])

    if config.task.permission_mode:
        command.extend(["--permission-mode", config.task.permission_mode])

    if config.task.mcp_config:
        command.extend(["--mcp-config", str(Path(config.task.mcp_config).expanduser())])

    command.extend(_extra_args())
    return command


class TaskExecutor:
    def __init__(
        self,
        queue_manager: Optional[QueueManager] = None,
        execution_logger: Optional[ExecutionLogger] = None,
    ) -> None:
        self.queue_manager = queue_manager
        self.execution_logger = execution_logger or StructuredLogger()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run_task_by_name(self, task_name: str) -> ExecutionResult:
        config = load_task_by_name(task_name)
        queue_item = QueueItem(
            id=f"manual-{uuid.uuid4()}",
            name=task_name,
            priority=config.priority,
            enqueued_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        return self._execute(config, queue_item=queue_item, update_queue=False)

    def run_config_path(self, path: Path) -> ExecutionResult:
        config = load_task_config(path)
        queue_item = QueueItem(
            id=f"path-{uuid.uuid4()}",
            name=config.name,
            priority=config.priority,
            enqueued_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        return self._execute(config, queue_item=queue_item, update_queue=False)

    def process_queue_once(self) -> Optional[ExecutionResult]:
        if not self.queue_manager:
            raise RuntimeError("Queue processing requires a QueueManager")

        next_item = self.queue_manager.get_next_task()
        if not next_item:
            logger.info("No queued tasks to process")
            return None

        try:
            config = load_task_by_name(next_item.name)
        except ConfigError as exc:
            logger.error("Failed to load config for %s: %s", next_item.name, exc)
            if self.queue_manager.cancel(next_item.id):
                failure = {
                    "error": "config_error",
                    "details": str(exc),
                }
                self.queue_manager.record_failure(next_item, failure)
                self.execution_logger.task_failed(
                    next_item.id, next_item.name, failure, {"stage": "load"}
                )
            return None

        if not config.enabled:
            logger.warning("Task %s disabled; skipping", config.name)
            if self.queue_manager.cancel(next_item.id):
                disabled_error = {"error": "task_disabled"}
                self.queue_manager.record_failure(next_item, disabled_error)
                self.execution_logger.task_failed(
                    next_item.id, next_item.name, disabled_error, {"stage": "disabled"}
                )
            return None

        return self._execute(config, queue_item=next_item, update_queue=True)

    def process_queue(self) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        while True:
            outcome = self.process_queue_once()
            if outcome is None:
                break
            results.append(outcome)
        return results

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------
    def _execute(
        self,
        config: TaskConfig,
        queue_item: QueueItem,
        update_queue: bool,
    ) -> ExecutionResult:
        command = build_command(config)
        metadata = {"priority": config.priority}

        process = None
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as exc:
            raise TaskExecutionError(
                f"Claude CLI not found at {command[0]!r}. "
                "Set CLODPUTER_CLAUDE_BIN to the correct executable."
            ) from exc
        except OSError as exc:
            raise TaskExecutionError(f"Failed to start Claude CLI: {exc}") from exc

        if update_queue and self.queue_manager:
            self.queue_manager.mark_running(queue_item.id, process.pid)

        self.execution_logger.task_started(queue_item.id, queue_item.name, metadata)

        start_time = time.monotonic()
        timeout_seconds = config.task.timeout
        stdout = ""
        stderr = ""
        return_code: Optional[int] = None
        cleanup_report: Optional[CleanupReport] = None
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return_code = process.returncode
            cleanup_report = cleanup_process_tree(process.pid)
            timeout_payload = {
                "error": "timeout",
                "return_code": return_code,
                "stdout": stdout or None,
                "stderr": stderr or None,
            }
            result = ExecutionResult(
                task_id=queue_item.id,
                task_name=config.name,
                status="timeout",
                return_code=return_code,
                duration=time.monotonic() - start_time,
                stdout=stdout,
                stderr=stderr,
                cleanup=cleanup_report,
                output_json=None,
                output_parse_error=None,
                error="timeout",
            )
            if update_queue and self.queue_manager:
                self.queue_manager.mark_failed(queue_item.id, timeout_payload)
                record_failure(config.name)
                if config.task.max_retries > queue_item.attempt:
                    delay = config.task.retry_backoff_seconds * (2**queue_item.attempt)
                    self.queue_manager.requeue_with_delay(queue_item, delay)
            self.execution_logger.task_failed(queue_item.id, config.name, timeout_payload, metadata)
            return result
        finally:
            cleanup_report = cleanup_report or cleanup_process_tree(process.pid)

        duration = time.monotonic() - start_time
        parsed_json, parse_error = _extract_json(stdout)

        status: ExecutionStatus
        error_info: Optional[str] = None
        if return_code == 0 and parse_error is None:
            status = "success"
        elif return_code == 0 and parse_error:
            status = "failure"
            error_info = f"JSON parse failure: {parse_error}"
        else:
            status = "failure"
            error_info = f"Claude exited with code {return_code}"

        result = ExecutionResult(
            task_id=queue_item.id,
            task_name=config.name,
            status=status,
            return_code=return_code,
            duration=duration,
            stdout=stdout,
            stderr=stderr,
            cleanup=cleanup_report,
            output_json=parsed_json,
            output_parse_error=parse_error,
            error=error_info,
        )

        if update_queue and self.queue_manager:
            if status == "success":
                success_payload = {
                    "duration": duration,
                    "result": parsed_json,
                    "return_code": return_code,
                    "stdout": stdout if parse_error else None,
                    "parse_error": parse_error,
                }
                self.queue_manager.mark_completed(
                    queue_item.id,
                    success_payload,
                )
            else:
                failure_payload = {
                    "error": error_info or "unknown",
                    "stderr": stderr or None,
                    "stdout": stdout or None,
                    "return_code": return_code,
                    "parse_error": parse_error,
                }
                self.queue_manager.mark_failed(
                    queue_item.id,
                    failure_payload,
                )
                if config.task.max_retries > queue_item.attempt:
                    delay = config.task.retry_backoff_seconds * (2**queue_item.attempt)
                    self.queue_manager.requeue_with_delay(queue_item, delay)

        if status == "success":
            success_payload = {
                "duration": duration,
                "result": parsed_json,
                "return_code": return_code,
                "parse_error": parse_error,
            }
            if parse_error:
                success_payload["stdout"] = stdout
            self.execution_logger.task_completed(
                queue_item.id,
                config.name,
                success_payload,
                metadata,
            )
        else:
            failure_payload = {
                "error": error_info or "unknown",
                "stderr": stderr or None,
                "stdout": stdout or None,
                "return_code": return_code,
                "parse_error": parse_error,
            }
            self.execution_logger.task_failed(
                queue_item.id,
                config.name,
                failure_payload,
                metadata,
            )

        if status == "success":
            record_success(config.name, duration)
        else:
            record_failure(config.name)

        return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clodputer task executor")
    parser.add_argument("--task", help="Run a specific task by name")
    parser.add_argument("--config", help="Run a task from an explicit YAML path")
    parser.add_argument("--queue", action="store_true", help="Process the task queue until empty")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    logging.basicConfig(
        level=os.getenv("CLODPUTER_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    config_path_env = os.getenv("CLODPUTER_CONFIG_PATH")

    executor = TaskExecutor()

    try:
        if args.config or config_path_env:
            config_path = Path(args.config or config_path_env).expanduser()
            result = executor.run_config_path(config_path)
            return 0 if result.status == "success" else 1
        if args.task:
            result = executor.run_task_by_name(args.task)
            return 0 if result.status == "success" else 1
        if args.queue or (not args.task and not args.config and not config_path_env):
            with QueueManager() as queue_manager:
                executor = TaskExecutor(queue_manager=queue_manager)
                results = executor.process_queue()
                if not results:
                    return 0
                last = results[-1]
                return 0 if last.status == "success" else 1
    except (ConfigError, TaskExecutionError, QueueCorruptionError, LockAcquisitionError) as exc:
        logger.error("Executor error: %s", exc)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
