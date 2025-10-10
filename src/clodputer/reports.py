# Copyright (c) 2025 Rémy Olson
"""
Task execution report generation and storage.

Provides detailed execution reports with JSON storage and markdown summaries.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import asdict

if TYPE_CHECKING:
    from .executor import ExecutionResult

OUTPUTS_DIR = Path.home() / ".clodputer" / "outputs"


class ReportError(RuntimeError):
    """Raised when report operations fail."""


def ensure_outputs_dir(task_name: str, outputs_dir: Path = OUTPUTS_DIR) -> Path:
    """Ensure output directory exists for a task.

    Args:
        task_name: Name of the task
        outputs_dir: Base outputs directory

    Returns:
        Path to the task's output directory
    """
    task_dir = outputs_dir / task_name
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def get_timestamp() -> str:
    """Get current timestamp in filename-safe format."""
    return time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())


def save_execution_report(
    result: ExecutionResult,
    outputs_dir: Path = OUTPUTS_DIR,
) -> tuple[Path, Path]:
    """Save execution result as JSON and markdown.

    Args:
        result: Execution result to save
        outputs_dir: Base outputs directory

    Returns:
        Tuple of (json_path, markdown_path)

    Raises:
        ReportError: If save fails
    """
    task_dir = ensure_outputs_dir(result.task_name, outputs_dir)
    timestamp = get_timestamp()

    # Save JSON report
    json_path = task_dir / f"{timestamp}.json"
    try:
        # Convert ExecutionResult to dict for JSON serialization
        result_dict = asdict(result)
        # Convert CleanupReport to dict if present
        if result_dict.get("cleanup"):
            cleanup = result_dict["cleanup"]
            if hasattr(cleanup, "__dict__"):
                result_dict["cleanup"] = cleanup.__dict__

        json_content = json.dumps(result_dict, indent=2, ensure_ascii=False)
        json_path.write_text(json_content, encoding="utf-8")
    except (OSError, TypeError) as exc:
        raise ReportError(f"Failed to save JSON report: {exc}") from exc

    # Generate and save markdown report
    markdown_path = task_dir / f"{timestamp}.md"
    try:
        markdown_content = generate_markdown_report(result, timestamp)
        markdown_path.write_text(markdown_content, encoding="utf-8")
    except OSError as exc:
        raise ReportError(f"Failed to save markdown report: {exc}") from exc

    return json_path, markdown_path


def generate_markdown_report(result: ExecutionResult, timestamp: str) -> str:
    """Generate markdown summary for an execution result.

    Args:
        result: Execution result
        timestamp: Formatted timestamp string

    Returns:
        Markdown report content
    """
    # Status emoji mapping
    status_emoji = {
        "success": "✅",
        "failure": "❌",
        "timeout": "⏱️",
        "error": "⚠️",
    }

    emoji = status_emoji.get(result.status, "❓")

    lines = [
        f"# {emoji} Task Execution Report",
        "",
        f"**Task:** {result.task_name}",
        f"**Task ID:** {result.task_id}",
        f"**Status:** {result.status.upper()}",
        f"**Timestamp:** {timestamp}",
        f"**Duration:** {result.duration:.2f}s",
        "",
        "---",
        "",
    ]

    # Add execution details
    lines.extend(
        [
            "## Execution Details",
            "",
            f"- **Return Code:** {result.return_code}",
            f"- **JSON Parse:** {'✅ Success' if result.output_parse_error is None else '❌ Failed'}",
        ]
    )

    if result.error:
        lines.extend(
            [
                f"- **Error:** {result.error}",
            ]
        )

    lines.extend(["", "---", ""])

    # Add output section
    if result.output_json is not None:
        lines.extend(
            [
                "## Output (Parsed JSON)",
                "",
                "```json",
                json.dumps(result.output_json, indent=2, ensure_ascii=False),
                "```",
                "",
            ]
        )

    if result.stdout:
        lines.extend(
            [
                "## Standard Output",
                "",
                "```",
                result.stdout.strip(),
                "```",
                "",
            ]
        )

    if result.stderr:
        lines.extend(
            [
                "## Standard Error",
                "",
                "```",
                result.stderr.strip(),
                "```",
                "",
            ]
        )

    # Add parse error if present
    if result.output_parse_error:
        lines.extend(
            [
                "## JSON Parse Error",
                "",
                "```",
                result.output_parse_error,
                "```",
                "",
            ]
        )

    # Add cleanup information
    if result.cleanup:
        cleanup = result.cleanup
        terminated = getattr(cleanup, "terminated_processes", [])
        zombie_count = getattr(cleanup, "zombie_count", 0)

        if terminated or zombie_count > 0:
            lines.extend(
                [
                    "## Cleanup Report",
                    "",
                ]
            )

            if terminated:
                lines.extend(
                    [
                        f"**Terminated Processes:** {len(terminated)}",
                        "",
                        "| PID | Status |",
                        "|-----|--------|",
                    ]
                )
                for proc in terminated:
                    pid = proc.get("pid", "?")
                    status = proc.get("status", "unknown")
                    lines.append(f"| {pid} | {status} |")
                lines.append("")

            if zombie_count > 0:
                lines.extend(
                    [
                        f"**Zombie Processes Found:** {zombie_count}",
                        "",
                    ]
                )

    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Clodputer at {timestamp}*")

    return "\n".join(lines)


def load_latest_report(task_name: str, outputs_dir: Path = OUTPUTS_DIR) -> Optional[Dict[str, Any]]:
    """Load the most recent execution report for a task.

    Args:
        task_name: Name of the task
        outputs_dir: Base outputs directory

    Returns:
        Report data as dictionary, or None if no reports exist
    """
    task_dir = outputs_dir / task_name
    if not task_dir.exists():
        return None

    # Find most recent JSON file
    json_files = sorted(task_dir.glob("*.json"), reverse=True)
    if not json_files:
        return None

    try:
        content = json_files[0].read_text(encoding="utf-8")
        return json.loads(content)
    except (OSError, json.JSONDecodeError):
        return None


def list_reports(
    task_name: str, outputs_dir: Path = OUTPUTS_DIR, limit: int = 10
) -> List[Dict[str, Any]]:
    """List recent execution reports for a task.

    Args:
        task_name: Name of the task
        outputs_dir: Base outputs directory
        limit: Maximum number of reports to return

    Returns:
        List of report data dictionaries, newest first
    """
    task_dir = outputs_dir / task_name
    if not task_dir.exists():
        return []

    reports = []
    json_files = sorted(task_dir.glob("*.json"), reverse=True)[:limit]

    for json_file in json_files:
        try:
            content = json_file.read_text(encoding="utf-8")
            report = json.loads(content)
            # Add file metadata
            report["report_file"] = str(json_file)
            report["report_timestamp"] = json_file.stem
            reports.append(report)
        except (OSError, json.JSONDecodeError):
            continue

    return reports


def compare_reports(
    report1: Dict[str, Any],
    report2: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare two execution reports.

    Args:
        report1: First report (usually newer)
        report2: Second report (usually older)

    Returns:
        Dictionary containing comparison results
    """
    comparison = {
        "status_changed": report1.get("status") != report2.get("status"),
        "status_from": report2.get("status"),
        "status_to": report1.get("status"),
        "duration_delta": (report1.get("duration", 0) - report2.get("duration", 0)),
        "return_code_changed": report1.get("return_code") != report2.get("return_code"),
        "return_code_from": report2.get("return_code"),
        "return_code_to": report1.get("return_code"),
    }

    # Check if error changed
    error1 = report1.get("error")
    error2 = report2.get("error")
    comparison["error_changed"] = error1 != error2
    if comparison["error_changed"]:
        comparison["error_from"] = error2
        comparison["error_to"] = error1

    # Output comparison
    output1 = report1.get("output_json")
    output2 = report2.get("output_json")
    comparison["output_changed"] = output1 != output2

    return comparison


__all__ = [
    "ReportError",
    "OUTPUTS_DIR",
    "ensure_outputs_dir",
    "save_execution_report",
    "generate_markdown_report",
    "load_latest_report",
    "list_reports",
    "compare_reports",
]
