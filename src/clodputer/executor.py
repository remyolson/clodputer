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

from .catch_up import calculate_next_expected_run
from .cleanup import CleanupReport, cleanup_process_tree
from .config import ConfigError, TaskConfig, load_task_by_name, load_task_config
from .debug import debug_logger
from .environment import claude_cli_path, store_claude_cli_path
from .logger import StructuredLogger
from .metrics import record_failure, record_success
from .queue import LockAcquisitionError, QueueCorruptionError, QueueItem, QueueManager
from .reports import save_execution_report
from .task_state import record_task_execution

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
    def _check_dependencies(self, config: TaskConfig) -> Tuple[bool, Optional[str]]:
        """Check if all task dependencies are satisfied.

        Returns:
            Tuple of (satisfied: bool, reason: Optional[str])
        """
        if not config.depends_on:
            return True, None

        from pathlib import Path
        from .dependencies import check_dependency_satisfied

        # Use default outputs directory
        outputs_dir = Path.home() / ".clodputer" / "outputs"

        for dep in config.depends_on:
            satisfied, reason = check_dependency_satisfied(
                dep.task, dep.condition, dep.max_age, outputs_dir
            )
            if not satisfied:
                return False, reason

        return True, None

    def _execute(
        self,
        config: TaskConfig,
        queue_item: QueueItem,
        update_queue: bool,
    ) -> ExecutionResult:
        debug_logger.info(
            "task_execution_started",
            description=f"🚀 Starting task execution: {config.name}",
            tags=["task", "execution", "start"],
            task_id=queue_item.id,
            task_name=config.name,
            priority=config.priority,
        )

        # Check dependencies before executing
        if config.depends_on:
            debug_logger.info(
                "checking_dependencies",
                description=f"🔗 Checking {len(config.depends_on)} dependencies for {config.name}",
                tags=["dependencies", "check"],
                task_name=config.name,
                dependency_count=len(config.depends_on),
            )

            satisfied, reason = self._check_dependencies(config)
            if not satisfied:
                debug_logger.error(
                    "dependency_not_satisfied",
                    description=f"❌ Dependency check failed: {reason}",
                    tags=["dependencies", "failure"],
                    marker="❌",
                    task_name=config.name,
                    reason=reason,
                )

                # Create a failure result for unsatisfied dependency
                result = ExecutionResult(
                    task_id=queue_item.id,
                    task_name=config.name,
                    status="failure",
                    return_code=None,
                    duration=0.0,
                    stdout="",
                    stderr=f"Dependency check failed: {reason}",
                    cleanup=CleanupReport(terminated=[], killed=[], orphaned_mcps=[]),
                    output_json=None,
                    error=f"dependency_failed: {reason}",
                )

                if update_queue and self.queue_manager:
                    failure_payload = {
                        "error": "dependency_failed",
                        "details": reason,
                    }
                    self.queue_manager.mark_failed(queue_item.id, failure_payload)
                    record_failure(config.name)

                self.execution_logger.task_failed(
                    queue_item.id,
                    config.name,
                    {"error": "dependency_failed", "details": reason},
                    {"stage": "dependency_check"},
                )

                # Save execution report
                try:
                    save_execution_report(result)
                except Exception as exc:
                    logger.warning("Failed to save execution report: %s", exc)

                return result

            debug_logger.info(
                "dependencies_satisfied",
                description=f"✅ All dependencies satisfied for {config.name}",
                tags=["dependencies", "success"],
                marker="✅",
                task_name=config.name,
            )

        command = build_command(config)

        # Log FULL command for debugging (shows exactly what we're sending to Claude)
        debug_logger.info(
            "claude_command_built",
            description=f"📝 Built Claude CLI command ({len(command)} arguments)",
            tags=["claude", "command", "build"],
            summary={
                "arg_count": len(command),
                "has_tools": bool(config.task.allowed_tools or config.task.disallowed_tools),
                "output_format": "json",
            },
            full_command=command,
            command_string=" ".join(command),
        )

        # Log the FULL prompt being sent to Claude
        prompt_size_kb = len(config.task.prompt) / 1024

        # Warn if prompt is dangerously large (could hit token limits)
        if prompt_size_kb > 50:  # ~12k tokens
            debug_logger.warning(
                "large_prompt_warning",
                description=f"⚠️  Large prompt may hit token limits ({prompt_size_kb:.1f} KB)",
                tags=["claude", "prompt", "warning", "size"],
                marker="⚠️",
                summary={
                    "size_kb": f"{prompt_size_kb:.1f}",
                    "threshold_kb": "50",
                    "risk": "token_limit",
                },
                prompt_size_kb=prompt_size_kb,
                task_name=config.name,
            )

        debug_logger.info(
            "claude_prompt_sent",
            description=f"📤 Sending prompt to Claude ({prompt_size_kb:.1f} KB)",
            tags=["claude", "prompt", "api"],
            marker="📤",
            summary={
                "size_kb": f"{prompt_size_kb:.1f}",
                "size_chars": len(config.task.prompt),
                "task": config.name,
            },
            prompt=config.task.prompt,
            prompt_length=len(config.task.prompt),
            task_name=config.name,
        )

        metadata = {"priority": config.priority}

        process = None
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            debug_logger.subprocess(
                "claude_process_started",
                " ".join(command),
                pid=process.pid,
                task_name=config.name,
            )
        except FileNotFoundError as exc:
            debug_logger.error("task_cli_not_found", command_path=command[0], error=str(exc))
            raise TaskExecutionError(
                f"Claude CLI not found at {command[0]!r}. "
                "Set CLODPUTER_CLAUDE_BIN to the correct executable."
            ) from exc
        except OSError as exc:
            debug_logger.error("task_subprocess_failed", error=str(exc))
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

            # Log FULL response from Claude (critical for debugging)
            duration = time.monotonic() - start_time
            stdout_size_kb = (len(stdout) if stdout else 0) / 1024
            stderr_size_kb = (len(stderr) if stderr else 0) / 1024

            debug_logger.info(
                "claude_response_received",
                description=f"📥 Received response from Claude ({duration:.1f}s, {stdout_size_kb:.1f} KB)",
                tags=["claude", "response", "api"],
                marker="📥",
                summary={
                    "duration": f"{duration:.1f}s",
                    "stdout_kb": f"{stdout_size_kb:.1f}",
                    "stderr_kb": f"{stderr_size_kb:.1f}",
                    "return_code": return_code,
                    "has_output": bool(stdout),
                },
                pid=process.pid,
                task_name=config.name,
                return_code=return_code,
                duration=duration,
                stdout=stdout,
                stderr=stderr,
                stdout_length=len(stdout) if stdout else 0,
                stderr_length=len(stderr) if stderr else 0,
            )
        except subprocess.TimeoutExpired:
            debug_logger.warning(
                "task_subprocess_timeout",
                pid=process.pid,
                timeout_seconds=timeout_seconds,
            )
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
                    # Calculate exponential backoff with cap
                    delay = config.task.retry_backoff_seconds * (2**queue_item.attempt)
                    delay = min(delay, config.task.max_retry_delay)
                    debug_logger.info(
                        "task_retry_scheduled",
                        description=f"🔄 Retry scheduled for {config.name} (attempt {queue_item.attempt + 1}/{config.task.max_retries})",
                        tags=["retry", "backoff"],
                        marker="🔄",
                        summary={
                            "task": config.name,
                            "attempt": queue_item.attempt + 1,
                            "max_retries": config.task.max_retries,
                            "delay_seconds": delay,
                            "backoff_strategy": "exponential",
                        },
                        delay=delay,
                        next_attempt=queue_item.attempt + 1,
                    )
                    self.queue_manager.requeue_with_delay(queue_item, delay)
            self.execution_logger.task_failed(queue_item.id, config.name, timeout_payload, metadata)

            # Save execution report
            try:
                save_execution_report(result)
            except Exception as exc:
                logger.warning("Failed to save execution report: %s", exc)

            return result
        finally:
            cleanup_report = cleanup_report or cleanup_process_tree(process.pid)

        duration = time.monotonic() - start_time
        parsed_json, parse_error = _extract_json(stdout)

        # Log JSON parsing result with schema validation (helps identify format issues)
        if parse_error:
            # Analyze what we got to provide better diagnostics
            stdout_preview = stdout[:200] if stdout else ""
            actual_type = "empty" if not stdout else "text"

            # Detect common failure patterns
            troubleshooting_hint = "Check if Claude returned an error message instead of JSON"
            if stdout and stdout.strip().startswith("{"):
                troubleshooting_hint = (
                    "JSON syntax error - check for unescaped quotes or invalid characters"
                )
            elif stdout and "error" in stdout.lower()[:100]:
                troubleshooting_hint = "Claude CLI returned an error message, not JSON"
            elif stdout and stdout.strip().startswith("```"):
                troubleshooting_hint = (
                    "Response contains markdown code blocks - extraction may have failed"
                )
            elif not stdout:
                troubleshooting_hint = "Claude produced no output - check if CLI is working (run: clodputer debug test-claude)"

            debug_logger.error(
                "claude_json_parse_failed",
                description="❌ Failed to parse Claude's response as JSON",
                tags=["claude", "json", "parse", "error", "schema"],
                marker="❌",
                summary={
                    "error": parse_error[:100],
                    "expected": "Valid JSON object or array",
                    "actual_type": actual_type,
                    "stdout_length": len(stdout) if stdout else 0,
                },
                task_name=config.name,
                parse_error=parse_error,
                expected_schema="JSON object (dict) or array - Claude should return --output-format json",
                actual_preview=stdout_preview,
                troubleshooting=troubleshooting_hint,
                stdout_preview=stdout[:500] if stdout else None,
            )
        else:
            debug_logger.info(
                "claude_json_parsed_successfully",
                description="✅ Successfully parsed JSON response",
                tags=["claude", "json", "parse", "success"],
                marker="✅",
                summary={
                    "type": type(parsed_json).__name__,
                    "is_dict": isinstance(parsed_json, dict),
                },
                task_name=config.name,
                parsed_structure=type(parsed_json).__name__,
            )

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
                    # Calculate exponential backoff with cap
                    delay = config.task.retry_backoff_seconds * (2**queue_item.attempt)
                    delay = min(delay, config.task.max_retry_delay)
                    debug_logger.info(
                        "task_retry_scheduled",
                        description=f"🔄 Retry scheduled for {config.name} (attempt {queue_item.attempt + 1}/{config.task.max_retries})",
                        tags=["retry", "backoff"],
                        marker="🔄",
                        summary={
                            "task": config.name,
                            "attempt": queue_item.attempt + 1,
                            "max_retries": config.task.max_retries,
                            "delay_seconds": delay,
                            "backoff_strategy": "exponential",
                        },
                        delay=delay,
                        next_attempt=queue_item.attempt + 1,
                    )
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
            # Record task state for catch-up logic
            next_expected = None
            if config.schedule:
                next_expected = calculate_next_expected_run(config.schedule)
            record_task_execution(config.name, success=True, next_expected=next_expected)
        else:
            record_failure(config.name)
            # Record failed execution (but don't update next_expected)
            record_task_execution(config.name, success=False)

        # Determine appropriate marker based on status
        status_markers = {
            "success": "✅",
            "failure": "❌",
            "timeout": "⏱️",
            "error": "⚠️",
        }
        status_marker = status_markers.get(status, "ℹ️")

        debug_logger.info(
            "task_execution_completed",
            description=f"{status_marker} Task {status}: {config.name} ({duration:.1f}s)",
            tags=["task", "execution", "completed", status],
            marker=status_marker,
            summary={
                "status": status,
                "duration": f"{duration:.1f}s",
                "return_code": return_code,
                "json_valid": parse_error is None,
                "task": config.name,
            },
            task_id=queue_item.id,
            task_name=config.name,
            status=status,
            duration=duration,
            return_code=return_code,
            has_parse_error=parse_error is not None,
        )

        # Save execution report
        try:
            json_path, md_path = save_execution_report(result)
            debug_logger.info(
                "execution_report_saved",
                description=f"📄 Saved execution report for {config.name}",
                tags=["report", "save"],
                marker="📄",
                summary={
                    "json": str(json_path.name),
                    "markdown": str(md_path.name),
                    "task": config.name,
                },
                json_path=str(json_path),
                markdown_path=str(md_path),
            )
        except Exception as exc:
            logger.warning("Failed to save execution report: %s", exc)

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
