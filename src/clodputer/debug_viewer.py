# Copyright (c) 2025 Rémy Olson
"""
Simple viewer for debug logs with Phase 1 enhancements.

Shows human-readable format with:
- Emoji markers for quick scanning
- Human descriptions
- Summaries for large data
- Hierarchical view by operation
"""

from __future__ import annotations

import json
from typing import Any, Optional

import click

from .debug import DEBUG_LOG_FILE


def format_elapsed(elapsed: Optional[float]) -> str:
    """Format elapsed seconds as human-readable string."""
    if elapsed is None:
        return ""
    if elapsed < 0.001:
        return "0.0s"
    if elapsed < 1:
        return f"{elapsed * 1000:.0f}ms"
    if elapsed < 60:
        return f"{elapsed:.1f}s"
    minutes = int(elapsed // 60)
    seconds = elapsed % 60
    return f"{minutes}m{seconds:.0f}s"


def format_log_entry(entry: dict[str, Any], show_full_data: bool = False) -> str:
    """Format a single log entry in human-readable format."""
    lines = []

    # Build the main line with elapsed time, marker, and description
    prefix_parts = []

    if "elapsed" in entry:
        prefix_parts.append(f"[+{format_elapsed(entry['elapsed'])}]")

    if "marker" in entry:
        prefix_parts.append(entry["marker"])

    if "description" in entry:
        # Use description (human-readable)
        message = entry["description"]
    else:
        # Fall back to event name (technical)
        message = entry["event"].replace("_", " ").title()

    prefix = " ".join(prefix_parts)
    lines.append(f"{prefix} {message}")

    # Show summary if present
    if "summary" in entry:
        summary = entry["summary"]
        if isinstance(summary, dict):
            summary_parts = [f"{k}={v}" for k, v in summary.items()]
            lines.append(f"        Summary: {', '.join(summary_parts)}")

    # Show operation_id if present
    if "operation_id" in entry:
        lines.append(f"        Operation ID: {entry['operation_id']}")

    # Show tags if present
    if "tags" in entry:
        tags_str = ", ".join(entry["tags"])
        lines.append(f"        Tags: {tags_str}")

    # Show level if ERROR or WARNING
    if entry.get("level") in ("ERROR", "WARNING"):
        lines.append(f"        Level: {entry['level']}")

    # Show technical details in compact format
    location = f"{entry.get('module', '?')}.{entry.get('function', '?')}:{entry.get('line', '?')}"
    lines.append(f"        Location: {location}")

    # Show data if requested or if it's small
    if show_full_data and "data" in entry:
        data_str = json.dumps(entry["data"], indent=2)
        lines.append("        Data:")
        for line in data_str.split("\n"):
            lines.append(f"          {line}")

    return "\n".join(lines)


@click.command(name="view")
@click.option(
    "--operation-id",
    help="Filter to specific operation ID",
)
@click.option(
    "--level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Filter by log level",
)
@click.option(
    "--tags",
    help="Filter by tags (comma-separated)",
)
@click.option(
    "--event",
    help="Filter by event name",
)
@click.option(
    "--full",
    is_flag=True,
    help="Show full data objects",
)
@click.option(
    "--tail",
    type=int,
    default=None,
    help="Show only last N entries",
)
def debug_view_command(
    operation_id: Optional[str],
    level: Optional[str],
    tags: Optional[str],
    event: Optional[str],
    full: bool,
    tail: Optional[int],
) -> None:
    """View debug logs in human-readable format.

    Examples:
        clodputer debug view
        clodputer debug view --operation-id onboard-a1b2c3d4
        clodputer debug view --level ERROR
        clodputer debug view --tags claude,api
        clodputer debug view --tail 20
    """
    if not DEBUG_LOG_FILE.exists():
        click.echo("No debug log found. Run with --debug flag to enable logging.")
        return

    # Read all log entries
    entries = []
    try:
        with DEBUG_LOG_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        click.echo(f"Error reading log file: {exc}", err=True)
        return

    # Apply filters
    filtered_entries = entries

    if operation_id:
        filtered_entries = [e for e in filtered_entries if e.get("operation_id") == operation_id]

    if level:
        filtered_entries = [e for e in filtered_entries if e.get("level") == level]

    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        filtered_entries = [
            e for e in filtered_entries if "tags" in e and any(tag in e["tags"] for tag in tag_list)
        ]

    if event:
        filtered_entries = [e for e in filtered_entries if e.get("event") == event]

    # Apply tail limit
    if tail:
        filtered_entries = filtered_entries[-tail:]

    # Show results
    if not filtered_entries:
        click.echo("No log entries match the filters.")
        return

    click.echo(f"\n{'='*80}")
    click.echo(f"Debug Logs ({len(filtered_entries)} entries)")
    click.echo(f"{'='*80}\n")

    for i, entry in enumerate(filtered_entries):
        click.echo(format_log_entry(entry, show_full_data=full))
        if i < len(filtered_entries) - 1:
            click.echo()  # Blank line between entries

    click.echo()


__all__ = ["debug_view_command"]
