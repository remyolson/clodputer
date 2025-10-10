# Copyright (c) 2025 Rémy Olson
"""
Click-based CLI entry point for Clodputer.

Commands included:
- clodputer init
- clodputer create-task
- clodputer modify <task>
- clodputer validate <task>
- clodputer deps <task>
- clodputer run <task>
- clodputer list
- clodputer inspect <task>
- clodputer search <keyword>
- clodputer results <task>
- clodputer health-check
- clodputer state get/set/delete/list
- clodputer dashboard
- clodputer status
- clodputer logs
- clodputer queue
- clodputer catch-up
- clodputer install
- clodputer uninstall
- clodputer watch
- clodputer manage
- clodputer doctor
- clodputer debug view
- clodputer debug test-claude
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Iterable, Optional

import click
import json

from .catch_up import detect_missed_tasks
from .config import (
    ConfigError,
    TASKS_DIR,
    create_task_from_json,
    ensure_tasks_dir,
    load_task_by_name,
    task_to_json,
    validate_all_tasks,
)
from .cron import (
    CRON_LOG_FILE,
    CRON_SECTION_BEGIN,
    CRON_SECTION_END,
    CronError,
    generate_cron_section,
    install_cron_jobs,
    preview_schedule,
    read_crontab,
    scheduled_tasks,
    uninstall_cron_jobs,
)
from .dashboard import run_dashboard
from .debug import debug_logger, enable_debug_logging, DEBUG_LOG_FILE
from .debug_viewer import debug_view_command
from .diagnostics import gather_diagnostics
from .executor import ExecutionResult, TaskExecutor
from .logger import LOG_FILE, iter_events, tail_events
from .onboarding import run_onboarding
from .queue import QueueManager
from .templates import available as available_templates, export as export_template
from .watcher import (
    WATCHER_LOG_FILE,
    WatcherError,
    file_watch_tasks,
    run_watch_service,
    start_daemon as start_watch_daemon,
    stop_daemon as stop_watch_daemon,
    watcher_status,
)
from .menubar import run_menu_bar
from .manager import run_manager
from .state import StateError, delete_state, list_states, load_state, save_state, update_state

try:
    __version__ = metadata.version("clodputer")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.0-dev"


def _parse_iso(timestamp: str) -> Optional[datetime]:
    if not timestamp:
        return None
    try:
        if timestamp.endswith("Z"):
            timestamp = timestamp.replace("Z", "+00:00")
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None


def _format_duration(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def _open_debug_log_window() -> None:
    """Open a new Terminal window showing live debug logs.

    Uses AppleScript to open a new Terminal window with a tail -f command
    that follows the debug log file with color-coded output.
    """
    if sys.platform != "darwin":
        click.echo("⚠️  Log window only supported on macOS. Monitor logs with:")
        click.echo(f"    tail -f {DEBUG_LOG_FILE}")
        return

    # Create a tail command with color highlighting for log levels
    tail_cmd = f"tail -f {DEBUG_LOG_FILE} | grep --color=always -E 'ERROR|WARNING|INFO|DEBUG|$'"

    # AppleScript to open new Terminal window
    script = f"""
tell application "Terminal"
    activate
    do script "{tail_cmd}"
end tell
"""

    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        click.echo(f"🪟  Debug log window opened (viewing {DEBUG_LOG_FILE})")
    except subprocess.CalledProcessError:
        click.echo("⚠️  Failed to open log window. Monitor logs with:")
        click.echo(f"    tail -f {DEBUG_LOG_FILE}")
    except FileNotFoundError:
        click.echo("⚠️  AppleScript not available. Monitor logs with:")
        click.echo(f"    tail -f {DEBUG_LOG_FILE}")


def _print_execution_result(result: ExecutionResult) -> None:
    status_symbol = {"success": "✅", "failure": "❌", "timeout": "⏱️", "error": "⚠️"}.get(
        result.status, "ℹ️"
    )
    click.echo(
        f"{status_symbol} {result.task_name} ({result.task_id}) "
        f"- {result.status} in {_format_duration(result.duration)}"
    )
    if result.error:
        click.echo(f"   Error: {result.error}")
    if result.output_json:
        click.echo(f"   Output: {result.output_json}")


def _compute_queue_position(queue_status: dict, task_id: str) -> Optional[int]:
    for index, item in enumerate(queue_status.get("queued", []), start=1):
        if item["id"] == task_id:
            return index
    return None


def _today_stats() -> tuple[int, int]:
    today = datetime.now(timezone.utc).date()
    success = failure = 0
    for event in iter_events(reverse=True):
        if event is None:
            continue
        timestamp = event.get("timestamp")
        dt = _parse_iso(timestamp) if timestamp else None
        if not dt:
            continue
        if dt.date() != today:
            break
        if event.get("event") == "task_completed":
            success += 1
        elif event.get("event") == "task_failed":
            failure += 1
    return success, failure


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging and open log window",
)
@click.version_option(__version__)
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Clodputer CLI."""
    if debug:
        enable_debug_logging()
        click.echo("🐛 Debug mode enabled")
        click.echo(f"   Logs writing to {DEBUG_LOG_FILE}")

        # Open log window automatically
        _open_debug_log_window()
        click.echo()

        # Log the command being executed
        debug_logger.info("cli_invoked", command=ctx.invoked_subcommand, args=sys.argv[1:])


@cli.command()
@click.option(
    "--reset",
    is_flag=True,
    help="Reset stored onboarding state before running the guided flow.",
)
@click.option(
    "--claude-cli",
    help="Path to Claude CLI executable (skips auto-detection and interactive prompt).",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip all confirmation prompts (non-interactive mode).",
)
@click.option(
    "--no-templates",
    is_flag=True,
    help="Skip template/task installation prompts.",
)
@click.option(
    "--no-automation",
    is_flag=True,
    help="Skip automation setup (cron/watcher).",
)
def init(
    reset: bool,
    claude_cli: Optional[str],
    yes: bool,
    no_templates: bool,
    no_automation: bool,
) -> None:
    """Run the guided onboarding workflow.

    Non-interactive mode example:
        clodputer init --claude-cli /path/to/claude --yes --no-templates --no-automation

    This mode is useful for automated testing, CI/CD, and scripted installations.
    """

    try:
        run_onboarding(
            reset=reset,
            claude_cli_path=claude_cli,
            non_interactive=yes,
            skip_templates=no_templates,
            skip_automation=no_automation,
        )
    except click.ClickException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        raise click.ClickException(f"Onboarding failed: {exc}") from exc


@cli.command(name="create-task")
@click.option("--json", "json_input", help="JSON task configuration string")
@click.option("--stdin", is_flag=True, help="Read JSON from stdin")
@click.option("--test", is_flag=True, help="Test task immediately after creation")
@click.option("--name", help="Quick-create: task name (requires --prompt)")
@click.option("--prompt", help="Quick-create: task prompt (requires --name)")
@click.option("--schedule", help="Quick-create: cron schedule expression (optional)")
@click.option("--priority", type=click.Choice(["normal", "high"]), default="normal", help="Task priority")
@click.option("--tools", help="Comma-separated list of allowed tools (optional)")
@click.option("--format", "output_format", type=click.Choice(["json", "text"]), default="text", help="Output format")
def create_task(
    json_input: Optional[str],
    stdin: bool,
    test: bool,
    name: Optional[str],
    prompt: Optional[str],
    schedule: Optional[str],
    priority: str,
    tools: Optional[str],
    output_format: str,
) -> None:
    """Create a new task from JSON configuration or quick-create options.

    Examples:
        # Create from JSON string
        clodputer create-task --json '{"name": "daily-email", "task": {"prompt": "Check email"}}'

        # Create from stdin
        echo '{"name": "task1", "task": {"prompt": "Do something"}}' | clodputer create-task --stdin

        # Quick-create with name and prompt
        clodputer create-task --name daily-backup --prompt "Backup my files" --schedule "0 2 * * *"

        # Test immediately after creation
        clodputer create-task --json '{...}' --test
    """

    # Validate input sources
    input_sources = sum(1 for x in [json_input, stdin, (name and prompt)] if x)
    if input_sources == 0:
        raise click.ClickException(
            "Must provide one of: --json, --stdin, or --name with --prompt"
        )
    if input_sources > 1:
        raise click.ClickException(
            "Cannot combine --json, --stdin, and quick-create options"
        )

    # Build task data
    task_data: dict = {}

    if json_input:
        try:
            task_data = json.loads(json_input)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON: {exc}") from exc
    elif stdin:
        try:
            task_data = json.load(sys.stdin)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON from stdin: {exc}") from exc
    elif name and prompt:
        # Quick-create mode
        task_data = {
            "name": name,
            "priority": priority,
            "task": {
                "prompt": prompt,
            }
        }
        if schedule:
            task_data["schedule"] = {
                "type": "cron",
                "expression": schedule,
            }
        if tools:
            task_data["task"]["allowed_tools"] = [t.strip() for t in tools.split(",")]
    else:
        raise click.ClickException("--name requires --prompt")

    # Create the task
    try:
        config, task_path = create_task_from_json(task_data)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    # Output result
    if output_format == "json":
        result = {
            "status": "created",
            "task_id": config.name,
            "path": str(task_path),
            "config": task_to_json(config),
        }
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"✅ Task '{config.name}' created at {task_path}")
        if config.schedule:
            click.echo(f"   Schedule: {config.schedule.expression}")
        if config.trigger:
            click.echo(f"   Trigger: {config.trigger.type}")
        click.echo(f"   Priority: {config.priority}")

    # Test if requested
    if test:
        if output_format == "text":
            click.echo(f"\n🧪 Testing task '{config.name}'...")

        with QueueManager() as queue:
            item = queue.enqueue(config.name, priority=config.priority, metadata={"test": True})
            executor = TaskExecutor(queue_manager=queue)
            results = executor.process_queue()
            outcome = next((r for r in results if r.task_id == item.id), None)

            if outcome:
                if output_format == "json":
                    test_result = {
                        "test_status": outcome.status,
                        "duration": outcome.duration,
                        "error": outcome.error,
                    }
                    click.echo(json.dumps(test_result, indent=2))
                else:
                    _print_execution_result(outcome)
            else:
                if output_format == "text":
                    click.echo("   Task queued but not executed (another task may be running)")


@cli.command()
@click.argument("task_name")
@click.option("--priority", type=click.Choice(["normal", "high"]), default="normal")
@click.option("--enqueue-only", is_flag=True, help="Only enqueue the task, do not execute it now.")
def run(task_name: str, priority: str, enqueue_only: bool) -> None:
    """Enqueue and optionally execute a task."""
    try:
        load_task_by_name(task_name)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    with QueueManager() as queue:
        item = queue.enqueue(task_name, priority=priority, metadata={"manual": True})
        status = queue.get_status()
        position = _compute_queue_position(status, item.id)
        click.echo(
            f"Enqueued {task_name} ({item.id}) at position {position or 1} "
            f"with priority {priority}."
        )
        if enqueue_only:
            return
        executor = TaskExecutor(queue_manager=queue)
        results = executor.process_queue()
        outcome = next((r for r in results if r.task_id == item.id), None)
        if outcome:
            _print_execution_result(outcome)
        else:
            click.echo("Task did not execute in this session (another task may still be running).")


@cli.command()
@click.option(
    "--tail", type=int, default=10, show_default=True, help="Number of entries to display."
)
@click.option("--task", "task_filter", help="Filter logs to a specific task name.")
@click.option("--follow", is_flag=True, help="Follow log output (like tail -f).")
@click.option("--json", "json_output", is_flag=True, help="Output raw JSON events.")
def logs(tail: int, task_filter: Optional[str], follow: bool, json_output: bool) -> None:
    """Display structured execution logs."""
    if not LOG_FILE.exists():
        click.echo("No log entries yet.")
        return

    def display(entries: Iterable[dict]) -> None:
        for event in entries:
            task_name = event.get("task_name")
            if task_filter and task_name != task_filter:
                continue
            if json_output:
                click.echo(json.dumps(event))
                continue
            ts = event.get("timestamp", "unknown")
            if event.get("event") == "task_completed":
                duration = event.get("result", {}).get("duration")
                duration_str = _format_duration(duration) if duration else "-"
                return_code = event.get("result", {}).get("return_code")
                parse_error = event.get("result", {}).get("parse_error")
                extras = []
                if return_code is not None:
                    extras.append(f"code={return_code}")
                if parse_error:
                    extras.append(f"parse_error={parse_error}")
                extra_text = f" {' '.join(extras)}" if extras else ""
                click.echo(f"{ts} ✅ {task_name} duration={duration_str}{extra_text}")
            elif event.get("event") == "task_failed":
                error_payload = event.get("error", {})
                if isinstance(error_payload, dict):
                    err = error_payload.get("error") or "unknown"
                    return_code = error_payload.get("return_code")
                    parse_error = error_payload.get("parse_error")
                else:
                    err = error_payload or "unknown"
                    return_code = None
                    parse_error = None
                extras = []
                if return_code is not None:
                    extras.append(f"code={return_code}")
                if parse_error:
                    extras.append(f"parse_error={parse_error}")
                extra_text = f" {' '.join(extras)}" if extras else ""
                click.echo(f"{ts} ❌ {task_name} error={err}{extra_text}")
            elif event.get("event") == "task_started":
                click.echo(f"{ts} ▶️  {task_name}")
            else:
                click.echo(f"{ts} ℹ️  {task_name} event={event.get('event')}")

    display(tail_events(limit=tail))
    if not follow:
        return

    with LOG_FILE.open("r", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)
        try:
            while True:
                where = handle.tell()
                line = handle.readline()
                if not line:
                    time.sleep(1)
                    handle.seek(where)
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                display([event])
        except KeyboardInterrupt:  # pragma: no cover
            pass


@cli.command()
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--filter", "filter_by", type=click.Choice(["all", "enabled", "disabled", "scheduled"]), default="all", help="Filter tasks by status")
def list(output_format: str, filter_by: str) -> None:  # type: ignore[override]
    """List configured tasks."""
    ensure_tasks_dir()
    configs, errors = validate_all_tasks()

    # Apply filters
    filtered_configs = configs
    if filter_by == "enabled":
        filtered_configs = [c for c in configs if c.enabled]
    elif filter_by == "disabled":
        filtered_configs = [c for c in configs if not c.enabled]
    elif filter_by == "scheduled":
        filtered_configs = [c for c in configs if c.enabled and c.schedule]

    # JSON output
    if output_format == "json":
        result = {
            "tasks": [task_to_json(cfg) for cfg in filtered_configs],
            "count": len(filtered_configs),
            "errors": [{"path": str(path), "error": error} for path, error in errors]
        }
        click.echo(json.dumps(result, indent=2))
        return

    # Text output
    if filtered_configs:
        click.echo("Configured tasks:")
        for cfg in filtered_configs:
            status = "enabled" if cfg.enabled else "disabled"
            schedule = cfg.schedule.expression if cfg.schedule else "-"
            if cfg.trigger:
                if cfg.trigger.type == "file_watch":
                    trigger_desc = (
                        f"file_watch path={cfg.trigger.path} pattern={cfg.trigger.pattern} "
                        f"event={cfg.trigger.event}"
                    )
                elif cfg.trigger.type == "interval":
                    trigger_desc = f"interval every {cfg.trigger.seconds}s"
                else:
                    trigger_desc = cfg.trigger.type
            else:
                trigger_desc = "manual"
            click.echo(f" • {cfg.name} [{status}] trigger={trigger_desc} schedule={schedule}")
    else:
        click.echo("No task configs found.")

    if errors:
        click.echo("\nTasks with validation errors:")
        for path, error in errors:
            click.echo(f" • {path}: {error}")


@cli.command()
@click.argument("task_name")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
def inspect(task_name: str, output_format: str) -> None:
    """Get detailed information about a specific task."""
    try:
        config = load_task_by_name(task_name)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    if output_format == "json":
        # Include task metadata from queue metrics if available
        with QueueManager(auto_lock=False) as queue:
            status = queue.get_status()
            metrics = status.get("metrics", {}).get(task_name, {})

        result = {
            "config": task_to_json(config),
            "metrics": metrics if metrics else None,
        }
        click.echo(json.dumps(result, indent=2))
        return

    # Text output
    click.echo(f"Task: {config.name}")
    click.echo(f"Enabled: {'yes' if config.enabled else 'no'}")
    click.echo(f"Priority: {config.priority}")

    if config.description:
        click.echo(f"Description: {config.description}")

    if config.schedule:
        click.echo(f"\nSchedule:")
        click.echo(f"  Type: {config.schedule.type}")
        click.echo(f"  Expression: {config.schedule.expression}")
        if config.schedule.timezone:
            click.echo(f"  Timezone: {config.schedule.timezone}")
        click.echo(f"  Catch-up: {config.schedule.catch_up}")

    if config.trigger:
        click.echo(f"\nTrigger:")
        click.echo(f"  Type: {config.trigger.type}")
        if config.trigger.type == "file_watch":
            click.echo(f"  Path: {config.trigger.path}")
            click.echo(f"  Pattern: {config.trigger.pattern}")
            click.echo(f"  Event: {config.trigger.event}")
            click.echo(f"  Debounce: {config.trigger.debounce}ms")
        elif config.trigger.type == "interval":
            click.echo(f"  Interval: {config.trigger.seconds}s")

    click.echo(f"\nTask Configuration:")
    click.echo(f"  Timeout: {config.task.timeout}s")
    click.echo(f"  Permission mode: {config.task.permission_mode}")
    click.echo(f"  Max retries: {config.task.max_retries}")

    if config.task.allowed_tools:
        click.echo(f"  Allowed tools: {', '.join(config.task.allowed_tools)}")
    if config.task.disallowed_tools:
        click.echo(f"  Disallowed tools: {', '.join(config.task.disallowed_tools)}")

    if config.task.mcp_config:
        click.echo(f"  MCP config: {config.task.mcp_config}")

    click.echo(f"\nPrompt:")
    click.echo(f"  {config.task.prompt[:200]}{'...' if len(config.task.prompt) > 200 else ''}")

    # Show metrics if available
    with QueueManager(auto_lock=False) as queue:
        status = queue.get_status()
        metrics = status.get("metrics", {}).get(task_name)

    if metrics:
        click.echo(f"\nMetrics:")
        click.echo(f"  Success: {metrics['success']}")
        click.echo(f"  Failure: {metrics['failure']}")
        click.echo(f"  Avg duration: {metrics['avg_duration']:.2f}s")


@cli.command()
@click.argument("keyword")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
def search(keyword: str, output_format: str) -> None:
    """Search tasks by keyword in name, description, or prompt."""
    ensure_tasks_dir()
    configs, errors = validate_all_tasks()

    keyword_lower = keyword.lower()
    matches = []

    for cfg in configs:
        # Search in name, description, and prompt
        if (keyword_lower in cfg.name.lower() or
            (cfg.description and keyword_lower in cfg.description.lower()) or
            keyword_lower in cfg.task.prompt.lower()):
            matches.append(cfg)

    if output_format == "json":
        result = {
            "query": keyword,
            "matches": [task_to_json(cfg) for cfg in matches],
            "count": len(matches),
        }
        click.echo(json.dumps(result, indent=2))
        return

    # Text output
    if matches:
        click.echo(f"Found {len(matches)} task(s) matching '{keyword}':")
        for cfg in matches:
            status = "enabled" if cfg.enabled else "disabled"
            click.echo(f" • {cfg.name} [{status}]")
            if cfg.description:
                click.echo(f"   {cfg.description}")
    else:
        click.echo(f"No tasks found matching '{keyword}'")

    if errors:
        click.echo(f"\nWarning: {len(errors)} task(s) have validation errors (not searched)")


@cli.command()
@click.argument("task_name")
@click.option("--enable", "set_enabled", flag_value=True, help="Enable the task")
@click.option("--disable", "set_enabled", flag_value=False, help="Disable the task")
@click.option("--priority", type=click.Choice(["normal", "high"]), help="Set task priority")
@click.option("--schedule", help="Set cron schedule expression")
@click.option("--prompt", help="Update task prompt")
@click.option("--add-tool", "add_tools", multiple=True, help="Add allowed tool (can be used multiple times)")
@click.option("--remove-tool", "remove_tools", multiple=True, help="Remove allowed tool (can be used multiple times)")
@click.option("--timeout", type=int, help="Set timeout in seconds")
@click.option("--max-retries", type=int, help="Set max retry attempts")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
def modify(
    task_name: str,
    set_enabled: Optional[bool],
    priority: Optional[str],
    schedule: Optional[str],
    prompt: Optional[str],
    add_tools: tuple[str, ...],
    remove_tools: tuple[str, ...],
    timeout: Optional[int],
    max_retries: Optional[int],
    output_format: str,
) -> None:
    """Modify an existing task configuration.

    Examples:
        # Enable/disable task
        clodputer modify my-task --enable
        clodputer modify my-task --disable

        # Update schedule
        clodputer modify my-task --schedule "0 9 * * *"

        # Update prompt
        clodputer modify my-task --prompt "New task prompt"

        # Add tools
        clodputer modify my-task --add-tool Read --add-tool Write

        # Remove tools
        clodputer modify my-task --remove-tool mcp__gmail

        # Update multiple settings
        clodputer modify my-task --priority high --timeout 900
    """
    # Load existing config
    try:
        config = load_task_by_name(task_name)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    # Track if any changes were made
    changes = []

    # Apply modifications
    if set_enabled is not None:
        config.enabled = set_enabled
        changes.append(f"enabled={set_enabled}")

    if priority:
        config.priority = priority  # type: ignore
        changes.append(f"priority={priority}")

    if schedule:
        from .config import ScheduleConfig
        config.schedule = ScheduleConfig(type="cron", expression=schedule)
        changes.append(f"schedule={schedule}")

    if prompt:
        config.task.prompt = prompt
        changes.append("prompt updated")

    if add_tools:
        for tool in add_tools:
            if tool not in config.task.allowed_tools:
                config.task.allowed_tools.append(tool)
                changes.append(f"added tool {tool}")

    if remove_tools:
        for tool in remove_tools:
            if tool in config.task.allowed_tools:
                config.task.allowed_tools.remove(tool)
                changes.append(f"removed tool {tool}")

    if timeout is not None:
        config.task.timeout = timeout
        changes.append(f"timeout={timeout}s")

    if max_retries is not None:
        config.task.max_retries = max_retries
        changes.append(f"max_retries={max_retries}")

    # Check if any changes were made
    if not changes:
        raise click.ClickException("No modifications specified. Use --help to see available options.")

    # Save updated config
    try:
        import yaml
        task_path = TASKS_DIR / f"{task_name}.yaml"
        task_dict = config.model_dump(exclude_none=True, mode='json')
        yaml_content = yaml.dump(task_dict, default_flow_style=False, sort_keys=False)
        task_path.write_text(yaml_content, encoding='utf-8')
    except Exception as exc:
        raise click.ClickException(f"Failed to save modified config: {exc}") from exc

    # Output result
    if output_format == "json":
        result = {
            "task": task_name,
            "changes": changes,
            "config": task_to_json(config),
        }
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"✅ Modified task '{task_name}'")
        for change in changes:
            click.echo(f"   • {change}")


@cli.command()
@click.argument("task_name")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--no-mcp-check", is_flag=True, help="Skip MCP tool availability check")
def validate(task_name: str, output_format: str, no_mcp_check: bool) -> None:
    """Validate a task configuration without executing it (dry-run).

    Performs comprehensive validation including:
    - Schema validation (required fields, types)
    - Schedule syntax validation (cron expression)
    - MCP tool availability check
    - Resource usage warnings (timeout, retries)
    - Best practice recommendations

    Examples:
        # Validate task configuration
        clodputer validate my-task

        # JSON output for programmatic use
        clodputer validate my-task --format json

        # Skip MCP check for faster validation
        clodputer validate my-task --no-mcp-check
    """
    from .validation import validate_task

    result = validate_task(task_name, check_mcp=not no_mcp_check)

    if output_format == "json":
        output = {
            "task": task_name,
            "valid": result.is_valid,
            "errors": [{"level": i.level, "message": i.message, "field": i.field} for i in result.get_errors()],
            "warnings": [{"level": i.level, "message": i.message, "field": i.field} for i in result.get_warnings()],
            "info": [{"level": i.level, "message": i.message, "field": i.field} for i in result.get_infos()],
        }
        click.echo(json.dumps(output, indent=2))
        return

    # Text output
    if result.is_valid:
        click.echo(f"✅ Task '{task_name}' is valid")
    else:
        click.echo(f"❌ Task '{task_name}' has validation errors:")
        for issue in result.get_errors():
            click.echo(f"   ERROR: {issue}")

    if result.has_warnings:
        click.echo(f"\n⚠️  Warnings:")
        for issue in result.get_warnings():
            click.echo(f"   {issue}")

    if result.get_infos():
        click.echo(f"\nℹ️  Info:")
        for issue in result.get_infos():
            click.echo(f"   {issue}")

    if not result.is_valid:
        sys.exit(1)


@cli.command()
@click.argument("task_name")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--tree", is_flag=True, help="Show full dependency tree")
@click.option("--reverse", is_flag=True, help="Show tasks that depend on this task")
def deps(task_name: str, output_format: str, tree: bool, reverse: bool) -> None:
    """Show task dependencies.

    Examples:
        # Show dependencies for a task
        clodputer deps my-task

        # Show full dependency tree
        clodputer deps my-task --tree

        # Show which tasks depend on this task
        clodputer deps my-task --reverse
    """
    try:
        config = load_task_by_name(task_name)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    if reverse:
        # Find tasks that depend on this task
        configs, errors = validate_all_tasks()
        dependent_tasks = [c for c in configs if any(d.task == task_name for d in c.depends_on)]

        if output_format == "json":
            result = {
                "task": task_name,
                "dependent_tasks": [
                    {
                        "name": c.name,
                        "dependencies": [{"task": d.task, "condition": d.condition, "max_age": d.max_age} for d in c.depends_on if d.task == task_name]
                    }
                    for c in dependent_tasks
                ]
            }
            click.echo(json.dumps(result, indent=2))
        else:
            if dependent_tasks:
                click.echo(f"Tasks that depend on '{task_name}':")
                for c in dependent_tasks:
                    deps = [d for d in c.depends_on if d.task == task_name]
                    for dep in deps:
                        condition_info = f" (condition: {dep.condition}"
                        if dep.max_age:
                            condition_info += f", max_age: {dep.max_age}s"
                        condition_info += ")"
                        click.echo(f" • {c.name}{condition_info}")
            else:
                click.echo(f"No tasks depend on '{task_name}'")
        return

    if tree:
        # Show full dependency tree
        from .dependencies import get_dependency_order
        configs, errors = validate_all_tasks()

        # Get all tasks involved in the dependency chain
        involved_tasks = set([task_name])
        to_check = [config]

        while to_check:
            current = to_check.pop()
            for dep in current.depends_on:
                if dep.task not in involved_tasks:
                    involved_tasks.add(dep.task)
                    try:
                        dep_config = load_task_by_name(dep.task)
                        to_check.append(dep_config)
                    except ConfigError:
                        pass

        # Get all involved task configs
        involved_configs = [c for c in configs if c.name in involved_tasks]

        try:
            ordered = get_dependency_order(involved_configs)

            if output_format == "json":
                result = {
                    "task": task_name,
                    "execution_order": [t.name for t in ordered],
                    "dependencies": {
                        t.name: [{"task": d.task, "condition": d.condition, "max_age": d.max_age} for d in t.depends_on]
                        for t in ordered if t.depends_on
                    }
                }
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo(f"Dependency tree for '{task_name}' (execution order):\n")
                for i, task in enumerate(ordered, 1):
                    marker = "▶️ " if task.name == task_name else "  "
                    click.echo(f"{marker}{i}. {task.name}")
                    if task.depends_on:
                        for dep in task.depends_on:
                            condition_info = f"condition={dep.condition}"
                            if dep.max_age:
                                condition_info += f", max_age={dep.max_age}s"
                            click.echo(f"      ↳ depends on: {dep.task} ({condition_info})")
        except Exception as exc:
            raise click.ClickException(f"Failed to build dependency tree: {exc}") from exc
        return

    # Show direct dependencies
    if output_format == "json":
        result = {
            "task": task_name,
            "dependencies": [
                {
                    "task": dep.task,
                    "condition": dep.condition,
                    "max_age": dep.max_age
                }
                for dep in config.depends_on
            ]
        }
        click.echo(json.dumps(result, indent=2))
    else:
        if config.depends_on:
            click.echo(f"Dependencies for '{task_name}':")
            for dep in config.depends_on:
                condition_info = f"condition: {dep.condition}"
                if dep.max_age:
                    condition_info += f", max_age: {dep.max_age}s"
                click.echo(f" • {dep.task} ({condition_info})")
        else:
            click.echo(f"Task '{task_name}' has no dependencies")


@cli.command()
@click.argument("task_name")
@click.option("--latest", is_flag=True, help="Show only the latest execution result")
@click.option("--limit", type=int, default=10, help="Number of results to show")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--compare", is_flag=True, help="Compare latest run with previous run")
@click.option("--markdown", is_flag=True, help="Show markdown report for latest run")
@click.option("--detailed", is_flag=True, help="Show detailed debugging info from reports")
def results(
    task_name: str,
    latest: bool,
    limit: int,
    output_format: str,
    compare: bool,
    markdown: bool,
    detailed: bool,
) -> None:
    """Get execution results for a task."""
    from .reports import list_reports, compare_reports

    # If markdown flag, show markdown report
    if markdown:
        task_dir = Path.home() / ".clodputer" / "outputs" / task_name
        if not task_dir.exists():
            click.echo(f"No reports found for task '{task_name}'", err=True)
            return

        md_files = sorted(task_dir.glob("*.md"), reverse=True)
        if not md_files:
            click.echo(f"No markdown reports found for task '{task_name}'", err=True)
            return

        content = md_files[0].read_text(encoding="utf-8")
        click.echo(content)
        return

    # If compare flag, compare latest two runs
    if compare:
        reports = list_reports(task_name, limit=2)
        if len(reports) < 2:
            click.echo(f"Need at least 2 execution reports to compare (found {len(reports)})", err=True)
            return

        comparison = compare_reports(reports[0], reports[1])

        if output_format == "json":
            click.echo(json.dumps(comparison, indent=2))
        else:
            click.echo(f"Comparison: Latest vs Previous\n")
            click.echo(f"Status: {comparison['status_from']} → {comparison['status_to']}")

            if comparison["status_changed"]:
                click.echo("  ⚠️  Status changed!")

            duration_delta = comparison["duration_delta"]
            if duration_delta != 0:
                sign = "+" if duration_delta > 0 else ""
                click.echo(f"Duration: {sign}{duration_delta:.2f}s")

            if comparison["return_code_changed"]:
                click.echo(
                    f"Return code: {comparison['return_code_from']} → {comparison['return_code_to']}"
                )

            if comparison.get("error_changed"):
                click.echo(f"\nError changed:")
                click.echo(f"  From: {comparison.get('error_from', 'None')}")
                click.echo(f"  To: {comparison.get('error_to', 'None')}")

            if comparison["output_changed"]:
                click.echo("  ⚠️  Output changed between runs")
        return

    # Use new report system if detailed flag or reports exist
    if detailed:
        reports = list_reports(task_name, limit=limit if not latest else 1)
        if reports:
            if output_format == "json":
                click.echo(json.dumps(reports, indent=2))
            else:
                click.echo(f"Detailed execution reports for '{task_name}' ({len(reports)} shown):\n")
                for report in reports:
                    status_symbol = {
                        "success": "✅",
                        "failure": "❌",
                        "timeout": "⏱️",
                        "error": "⚠️",
                    }.get(report.get("status", ""), "❓")

                    timestamp = report.get("report_timestamp", "unknown")
                    click.echo(f"{status_symbol} {timestamp} - {report.get('status', 'unknown')}")
                    click.echo(f"   Duration: {report.get('duration', 0):.2f}s")
                    click.echo(f"   Return code: {report.get('return_code')}")

                    if report.get("error"):
                        click.echo(f"   Error: {report['error']}")

                    if report.get("output_parse_error"):
                        click.echo(f"   Parse error: {report['output_parse_error']}")

                    if report.get("stdout"):
                        preview = report["stdout"][:100] + "..." if len(report["stdout"]) > 100 else report["stdout"]
                        click.echo(f"   Stdout: {preview}")

                    if report.get("stderr"):
                        preview = report["stderr"][:100] + "..." if len(report["stderr"]) > 100 else report["stderr"]
                        click.echo(f"   Stderr: {preview}")

                    click.echo(f"   Report: {report.get('report_file')}")
                    click.echo()
            return

    # Collect results from logs
    task_results = []
    for event in iter_events(reverse=True):
        if event.get("task_name") != task_name:
            continue

        event_type = event.get("event")
        if event_type == "task_completed":
            result = event.get("result", {})
            task_results.append({
                "timestamp": event.get("timestamp"),
                "status": "success",
                "duration": result.get("duration"),
                "return_code": result.get("return_code"),
                "output": result.get("result"),
            })
        elif event_type == "task_failed":
            error = event.get("error", {})
            task_results.append({
                "timestamp": event.get("timestamp"),
                "status": "failure",
                "error": error.get("error") if isinstance(error, dict) else error,
                "return_code": error.get("return_code") if isinstance(error, dict) else None,
            })

        if latest and task_results:
            break
        if len(task_results) >= limit:
            break

    if not task_results:
        if output_format == "json":
            click.echo("[]")
        else:
            click.echo(f"No execution results found for task '{task_name}'")
        return

    if output_format == "json":
        click.echo(json.dumps(task_results, indent=2))
    else:
        click.echo(f"Execution results for '{task_name}' ({len(task_results)} shown):\n")
        for result in task_results:
            status_symbol = "✅" if result["status"] == "success" else "❌"
            timestamp = result.get("timestamp", "unknown")
            click.echo(f"{status_symbol} {timestamp}")

            if result["status"] == "success":
                duration = result.get("duration")
                if duration:
                    click.echo(f"   Duration: {_format_duration(duration)}")
                if result.get("return_code") is not None:
                    click.echo(f"   Return code: {result['return_code']}")
            else:
                click.echo(f"   Error: {result.get('error', 'unknown')}")
                if result.get("return_code") is not None:
                    click.echo(f"   Return code: {result['return_code']}")
            click.echo()


@cli.command(name="health-check")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
def health_check(output_format: str) -> None:
    """Check health of all tasks based on recent execution results."""
    # Collect latest result for each task
    task_health = {}
    for event in iter_events(reverse=True):
        task_name = event.get("task_name")
        if not task_name or task_name in task_health:
            continue

        event_type = event.get("event")
        if event_type == "task_completed":
            task_health[task_name] = {
                "status": "healthy",
                "last_run": event.get("timestamp"),
                "last_result": "success",
            }
        elif event_type == "task_failed":
            error = event.get("error", {})
            task_health[task_name] = {
                "status": "unhealthy",
                "last_run": event.get("timestamp"),
                "last_result": "failure",
                "error": error.get("error") if isinstance(error, dict) else error,
            }

    if not task_health:
        if output_format == "json":
            click.echo("{}")
        else:
            click.echo("No task execution history found")
        return

    if output_format == "json":
        click.echo(json.dumps(task_health, indent=2))
    else:
        healthy = [t for t, h in task_health.items() if h["status"] == "healthy"]
        unhealthy = [t for t, h in task_health.items() if h["status"] == "unhealthy"]

        click.echo(f"Task Health Summary ({len(task_health)} tasks):\n")

        if healthy:
            click.echo(f"✅ Healthy ({len(healthy)}):")
            for task in sorted(healthy):
                click.echo(f"   • {task} - last run: {task_health[task]['last_run']}")
            click.echo()

        if unhealthy:
            click.echo(f"❌ Unhealthy ({len(unhealthy)}):")
            for task in sorted(unhealthy):
                h = task_health[task]
                click.echo(f"   • {task} - last run: {h['last_run']}")
                click.echo(f"     Error: {h.get('error', 'unknown')}")
            click.echo()


@cli.group()
def state() -> None:
    """Manage task state persistence."""


@state.command("get")
@click.argument("task_name")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--key", help="Get specific key from state")
def state_get(task_name: str, output_format: str, key: Optional[str]) -> None:
    """Get state for a task."""
    try:
        task_state = load_state(task_name)
    except StateError as exc:
        raise click.ClickException(str(exc)) from exc

    if not task_state:
        if output_format == "json":
            click.echo("{}")
        else:
            click.echo(f"No state found for task '{task_name}'")
        return

    # Get specific key if requested
    if key:
        if key not in task_state:
            raise click.ClickException(f"Key '{key}' not found in state for '{task_name}'")
        value = task_state[key]
        if output_format == "json":
            click.echo(json.dumps({key: value}, indent=2))
        else:
            click.echo(f"{key}: {json.dumps(value)}")
        return

    # Output full state
    if output_format == "json":
        click.echo(json.dumps(task_state, indent=2))
    else:
        click.echo(f"State for '{task_name}':")
        for k, v in task_state.items():
            click.echo(f"  {k}: {json.dumps(v)}")


@state.command("set")
@click.argument("task_name")
@click.option("--json", "json_input", help="JSON state to set")
@click.option("--key", help="Set specific key (requires --value)")
@click.option("--value", help="Value for key (requires --key)")
@click.option("--merge", is_flag=True, help="Merge with existing state instead of replacing")
def state_set(
    task_name: str,
    json_input: Optional[str],
    key: Optional[str],
    value: Optional[str],
    merge: bool,
) -> None:
    """Set state for a task."""
    # Validate input
    if json_input and (key or value):
        raise click.ClickException("Cannot use --json with --key/--value")
    if key and not value:
        raise click.ClickException("--key requires --value")
    if value and not key:
        raise click.ClickException("--value requires --key")
    if not json_input and not key:
        raise click.ClickException("Must provide either --json or --key with --value")

    try:
        if json_input:
            # Parse JSON input
            try:
                new_state = json.loads(json_input)
            except json.JSONDecodeError as exc:
                raise click.ClickException(f"Invalid JSON: {exc}") from exc

            if not isinstance(new_state, dict):
                raise click.ClickException("State must be a JSON object")

            if merge:
                # Merge with existing state
                current_state = load_state(task_name)
                current_state.update(new_state)
                save_state(task_name, current_state)
            else:
                # Replace state
                save_state(task_name, new_state)
        else:
            # Set specific key
            # Try to parse value as JSON, fall back to string
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = value

            update_state(task_name, {key: parsed_value})

        click.echo(f"✅ State updated for '{task_name}'")

    except StateError as exc:
        raise click.ClickException(str(exc)) from exc


@state.command("delete")
@click.argument("task_name")
@click.option("--key", help="Delete specific key instead of entire state")
def state_delete(task_name: str, key: Optional[str]) -> None:
    """Delete state for a task."""
    try:
        if key:
            # Delete specific key
            task_state = load_state(task_name)
            if key not in task_state:
                raise click.ClickException(f"Key '{key}' not found in state for '{task_name}'")
            del task_state[key]
            save_state(task_name, task_state)
            click.echo(f"✅ Deleted key '{key}' from state for '{task_name}'")
        else:
            # Delete entire state
            if delete_state(task_name):
                click.echo(f"✅ Deleted state for '{task_name}'")
            else:
                click.echo(f"No state found for '{task_name}'")
    except StateError as exc:
        raise click.ClickException(str(exc)) from exc


@state.command("list")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
def state_list(output_format: str) -> None:
    """List all task states."""
    try:
        states = list_states()
    except StateError as exc:
        raise click.ClickException(str(exc)) from exc

    if not states:
        if output_format == "json":
            click.echo("{}")
        else:
            click.echo("No task states found")
        return

    if output_format == "json":
        click.echo(json.dumps(states, indent=2))
    else:
        click.echo(f"Task states ({len(states)} total):")
        for task_name in sorted(states.keys()):
            state = states[task_name]
            key_count = len(state)
            click.echo(f" • {task_name}: {key_count} key(s)")


@cli.group()
def template() -> None:
    """Manage bundled task templates."""


@template.command("list")
def template_list() -> None:
    templates = available_templates()
    if not templates:
        click.echo("No bundled templates available.")
        return
    click.echo("Available templates:")
    for name in templates:
        click.echo(f" • {name}")


@template.command("export")
@click.argument("name")
@click.option(
    "--directory",
    "directory",
    default=str(TASKS_DIR),
    type=click.Path(path_type=Path),
    help="Directory to copy the template into (default: ~/.clodputer/tasks).",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    help="Optional explicit file path to write the template to.",
)
@click.option("--overwrite", is_flag=True, help="Overwrite the destination file if it exists.")
def template_export(
    name: str, directory: Path, output_path: Optional[Path], overwrite: bool
) -> None:
    """Copy a bundled template into your workspace."""

    directory_path = directory.expanduser()

    target: Path
    if output_path:
        target = output_path.expanduser()
    else:
        target = directory_path / name
        directory_path.mkdir(parents=True, exist_ok=True)

    if target.exists() and not overwrite:
        raise click.ClickException(
            f"Destination {target} already exists. Re-run with --overwrite to replace it."
        )

    try:
        destination = target if output_path else directory_path
        written = export_template(name, destination)
    except FileNotFoundError as exc:
        available = ", ".join(available_templates()) or "<none>"
        raise click.ClickException(
            f"Unknown template {name!r}. Available templates: {available}."
        ) from exc

    click.echo(f"Template {name} copied to {written}")


@cli.command()
@click.option("--clear", is_flag=True, help="Clear all queued tasks (does not stop running task).")
def queue(clear: bool) -> None:
    """Inspect or clear the task queue."""
    with QueueManager() as queue_manager:
        if clear:
            queue_manager.clear_queue()
            click.echo("Queue cleared.")
            return
        status = queue_manager.get_status()
        running = status.get("running")
        if running:
            started = _parse_iso(running.get("started_at", "")) or datetime.now(timezone.utc)
            elapsed = datetime.now(timezone.utc) - started
            click.echo(
                f"Running: {running['name']} (pid {running['pid']}) for {_format_duration(elapsed.total_seconds())}"
            )
        else:
            click.echo("No task currently running.")

        if status.get("queued"):
            click.echo("\nQueued tasks:")
            for item in status["queued"]:
                extras = []
                attempt = item.get("attempt", 0)

                # Show retry status if this is a retry
                if attempt > 0:
                    # Try to get max_retries from config
                    try:
                        from .config import load_task_by_name
                        config = load_task_by_name(item['name'])
                        max_retries = config.task.max_retries
                        extras.append(f"retry {attempt}/{max_retries}")
                    except:
                        extras.append(f"retry {attempt}")

                if item.get("not_before"):
                    # Calculate time until retry
                    not_before_dt = _parse_iso(item['not_before'])
                    if not_before_dt:
                        now = datetime.now(timezone.utc)
                        if not_before_dt > now:
                            wait_seconds = (not_before_dt - now).total_seconds()
                            extras.append(f"in {_format_duration(wait_seconds)}")
                        else:
                            extras.append("ready")
                    else:
                        extras.append(f"not_before={item['not_before']}")

                extra_text = f" ({', '.join(extras)})" if extras else ""
                click.echo(
                    f" • {item['name']} [{item['priority']}] enqueued_at={item['enqueued_at']}{extra_text}"
                )
        else:
            click.echo("\nQueue is empty.")

        if status.get("metrics"):
            click.echo("\nTask metrics:")
            for name, stats in status["metrics"].items():
                click.echo(
                    f" • {name}: success={stats['success']} failure={stats['failure']} avg_duration={stats['avg_duration']:.2f}s"
                )


@cli.command(name="catch-up")
@click.option("--dry-run", is_flag=True, help="Show missed tasks without queueing them.")
def catch_up_command(dry_run: bool) -> None:
    """Check for missed scheduled tasks and queue them for catch-up.

    This command detects tasks that:
    1. Have catch_up enabled (run_once or run_all)
    2. Missed their scheduled run time(s)
    3. Have a record of previous successful runs

    Missed tasks are queued with [CATCH-UP] marker in logs.
    """
    configs, errors = validate_all_tasks()
    if errors:
        click.echo("⚠️  Some task configs are invalid; skipping catch-up check:")
        for path, err in errors:
            click.echo(f" • {path}: {err}")
        return

    # Detect missed tasks
    missed = detect_missed_tasks(configs)

    if not missed:
        click.echo("✅ No missed tasks to catch up.")
        return

    # Group by task name for clearer output
    by_task = {}
    for miss in missed:
        if miss.task_name not in by_task:
            by_task[miss.task_name] = []
        by_task[miss.task_name].append(miss)

    click.echo(f"Found {len(missed)} missed task run(s) across {len(by_task)} task(s):\n")

    for task_name, misses in by_task.items():
        config = next((c for c in configs if c.name == task_name), None)
        catch_up_mode = config.schedule.catch_up if config and config.schedule else "skip"

        click.echo(f" • {task_name} ({catch_up_mode}): {len(misses)} missed run(s)")
        for miss in misses:
            click.echo(f"   - Missed at: {miss.missed_at}")

    if dry_run:
        click.echo("\n(Dry run - tasks not queued)")
        return

    # Queue missed tasks
    click.echo()
    queued_count = 0
    with QueueManager() as queue:
        for miss in missed:
            queue.enqueue(
                miss.task_name,
                priority="normal",
                metadata={"catch_up": True, "missed_at": miss.missed_at},
            )
            click.echo(f"[CATCH-UP] Queued {miss.task_name} (missed {miss.missed_at})")
            queued_count += 1

    click.echo(f"\n✅ Queued {queued_count} catch-up task(s).")
    click.echo("   Run `clodputer run <task>` or wait for queue processing.")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview cron entries without modifying crontab.")
def install(dry_run: bool) -> None:
    """Install scheduled tasks into the user's crontab."""
    configs, errors = validate_all_tasks()
    if errors:
        click.echo("⚠️  Some task configs are invalid; fix them before installing cron jobs:")
        for path, err in errors:
            click.echo(f" • {path}: {err}")
        raise click.ClickException("Task config validation failed")

    entries = scheduled_tasks(configs)
    if not entries:
        click.echo("No enabled cron or interval tasks found.")
        return

    section = generate_cron_section(entries)
    if dry_run:
        click.echo(section.rstrip())
        return

    try:
        result = install_cron_jobs(entries)
    except CronError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"Installed {result['installed']} cron job(s). Backup written to {result['backup']}."
    )
    click.echo(f"Cron log: {CRON_LOG_FILE}")


@cli.command()
@click.option(
    "--dry-run", is_flag=True, help="Show current Clodputer cron section without removing it."
)
def uninstall(dry_run: bool) -> None:
    """Remove Clodputer-managed cron jobs."""
    try:
        current = read_crontab()
    except CronError as exc:
        raise click.ClickException(str(exc)) from exc

    if CRON_SECTION_BEGIN not in current:
        click.echo("No Clodputer cron section found.")
        return

    if dry_run:
        click.echo(
            current[
                current.index(CRON_SECTION_BEGIN) : current.index(CRON_SECTION_END)
                + len(CRON_SECTION_END)
            ]
        )
        return

    try:
        result = uninstall_cron_jobs()
    except CronError as exc:
        raise click.ClickException(str(exc)) from exc

    if result["removed"]:
        click.echo(f"Removed Clodputer cron section. Backup written to {result['backup']}.")
    else:
        click.echo("No Clodputer cron section found.")


@cli.command("schedule-preview")
@click.argument("task_name")
@click.option("--count", default=5, show_default=True, help="Number of upcoming runs to display.")
def schedule_preview_command(task_name: str, count: int) -> None:
    """Preview upcoming run times for a scheduled or interval task."""

    configs, errors = validate_all_tasks()
    if errors:
        click.echo("⚠️  Cannot preview schedule until configuration errors are resolved:")
        for path, err in errors:
            click.echo(f" • {path}: {err}")
        raise click.ClickException("Task config validation failed")

    entries = scheduled_tasks(configs)
    for entry in entries:
        if entry.task.name == task_name:
            try:
                runs = preview_schedule(entry, count=count)
            except CronError as exc:
                raise click.ClickException(str(exc)) from exc

            click.echo(f"Upcoming runs for {task_name}:")
            for dt in runs:
                click.echo(f" • {dt.isoformat()}")
            return

    raise click.ClickException(
        f"Task '{task_name}' is not enabled with a cron schedule or interval trigger."
    )


@cli.command()
@click.option("--daemon", is_flag=True, help="Run watcher service in the background")
@click.option("--stop", is_flag=True, help="Stop the watcher daemon")
@click.option("--status", is_flag=True, help="Show watcher daemon status")
def watch(daemon: bool, stop: bool, status: bool) -> None:
    """Manage the file watcher service."""

    chosen = sum(1 for flag in (daemon, stop, status) if flag)
    if chosen > 1:
        raise click.ClickException("Choose only one of --daemon, --stop, or --status")

    if status:
        info = watcher_status()
        if info["running"]:
            click.echo(f"Watcher daemon running (PID {info['pid']}). Log: {info['log_file']}")
        else:
            click.echo("Watcher daemon not running.")
        return

    if stop:
        if stop_watch_daemon():
            click.echo("Watcher daemon stopped.")
        else:
            click.echo("Watcher daemon is not running.")
        return

    configs, errors = validate_all_tasks()
    if errors:
        click.echo("⚠️  Some task configs are invalid; fix them before starting the watcher:")
        for path, err in errors:
            click.echo(f" • {path}: {err}")
        raise click.ClickException("Task config validation failed")

    tasks = file_watch_tasks(configs)
    if not tasks:
        click.echo("No tasks configured with file_watch triggers.")
        return

    if daemon:
        try:
            pid = start_watch_daemon()
        except WatcherError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Watcher daemon started (PID {pid}). Log: {WATCHER_LOG_FILE}")
        return

    click.echo("Starting watcher in foreground. Press Ctrl+C to stop.")
    try:
        run_watch_service(tasks)
    except WatcherError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
def menu() -> None:
    """Start the Clodputer menu bar application."""

    try:
        run_menu_bar()
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(f"Failed to start menu bar: {exc}") from exc


@cli.command()
def dashboard() -> None:
    """Launch the interactive terminal dashboard."""

    try:
        run_dashboard()
    except KeyboardInterrupt:  # pragma: no cover - user exit
        pass
    except Exception as exc:  # pragma: no cover - curses failures
        raise click.ClickException(f"Failed to start dashboard: {exc}") from exc


@cli.command()
def status() -> None:
    """Show queue state and recent activity."""
    queue_manager = QueueManager(auto_lock=False)
    status = queue_manager.get_status()
    running = status.get("running")
    if running:
        started = _parse_iso(running.get("started_at", "")) or datetime.now(timezone.utc)
        elapsed = datetime.now(timezone.utc) - started
        click.echo(
            f"🔵 Running: {running['name']} (pid {running['pid']}) "
            f"{_format_duration(elapsed.total_seconds())} elapsed"
        )
    else:
        click.echo("🟢 Idle: no active task.")

    total = status["queued_counts"]["total"]
    high = status["queued_counts"]["high_priority"]
    click.echo(f"📦 Queue: {total} queued ({high} high priority)")

    click.echo("\nRecent executions:")
    recent = tail_events(limit=10)
    if not recent:
        click.echo("  (no executions logged yet)")
    else:
        for event in recent:
            ts = event.get("timestamp", "unknown")
            task = event.get("task_name", "unknown")
            if event.get("event") == "task_completed":
                duration = event.get("result", {}).get("duration")
                duration_str = _format_duration(duration) if duration else "-"
                click.echo(f" • {ts} ✅ {task} ({duration_str})")
            elif event.get("event") == "task_failed":
                err = event.get("error", {}).get("error") or "unknown"
                click.echo(f" • {ts} ❌ {task} ({err})")
            else:
                click.echo(f" • {ts} ▶️  {task}")

    success, failure = _today_stats()
    click.echo(f"\n📊 Today: {success} success / {failure} failed")

    metrics = status.get("metrics") or {}
    if metrics:
        click.echo("\n📈 Task Metrics:")
        for name, stats in list(metrics.items())[:5]:
            click.echo(
                f" • {name}: success={stats['success']} failure={stats['failure']} avg={stats['avg_duration']:.2f}s"
            )


@cli.command()
def manage() -> None:
    """Launch the interactive task manager (browse, edit, run, delete tasks)."""
    try:
        run_manager()
    except KeyboardInterrupt:
        click.echo("\n\nExiting task manager...")
    except Exception as exc:  # pragma: no cover - defensive guard
        raise click.ClickException(f"Task manager failed: {exc}") from exc


@cli.command()
def doctor() -> None:
    """Run diagnostics and output pass/fail checks."""
    results = gather_diagnostics()
    all_passed = True

    for result in results:
        symbol = "✅" if result.passed else "❌"
        click.echo(f"{symbol} {result.name}")
        if result.details:
            for detail in result.details:
                click.echo(f"   • {detail}")
        all_passed = all_passed and result.passed

    sys.exit(0 if all_passed else 1)


@cli.group()
def debug() -> None:
    """Debug logging utilities."""
    pass


debug.add_command(debug_view_command)


@debug.command(name="test-claude")
def test_claude_command() -> None:
    """Test Claude CLI health by sending a simple prompt.

    Verifies that:
    - Claude CLI executable is found and accessible
    - Claude can process prompts and return JSON
    - JSON parsing works correctly

    This helps diagnose whether failures are from Claude CLI
    or from your task configuration.
    """
    click.echo("🔍 Testing Claude CLI health...\n")

    # Import here to avoid circular dependencies
    from .executor import TaskExecutor
    from .config import TaskConfig, TaskDefinition

    # Create a minimal test task
    test_config = TaskConfig(
        name="health-check",
        enabled=True,
        priority="normal",
        task=TaskDefinition(
            prompt='Reply with JSON: {"status": "ok", "message": "Claude CLI is working"}',
            timeout=30,
        ),
    )

    # Create a test queue item
    from .queue import QueueItem
    import uuid

    test_item = QueueItem(
        id=f"health-{uuid.uuid4()}",
        name="health-check",
        priority="normal",
        enqueued_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    # Execute the test
    executor = TaskExecutor()
    try:
        result = executor._execute(test_config, queue_item=test_item, update_queue=False)

        if result.status == "success":
            click.echo("✅ Claude CLI is working correctly!\n")
            click.echo(f"   Response time: {result.duration:.2f}s")
            click.echo(f"   Return code: {result.return_code}")
            if result.output_json:
                click.echo(f"   JSON parsed: {result.output_json}")
        elif result.status == "timeout":
            click.echo("❌ Claude CLI timed out\n")
            click.echo("   This suggests Claude CLI is slow or unresponsive")
            click.echo(f"   Duration: {result.duration:.2f}s")
            sys.exit(1)
        else:
            click.echo("❌ Claude CLI test failed\n")
            if result.output_parse_error:
                click.echo(f"   Parse error: {result.output_parse_error}")
                click.echo(
                    f"   Claude returned: {result.stdout[:200] if result.stdout else '(empty)'}"
                )
                click.echo("\n   Troubleshooting:")
                click.echo("   - Check that Claude CLI is installed: which claude")
                click.echo("   - Verify Claude CLI works: claude -p 'Hello' --output-format json")
            else:
                click.echo(f"   Return code: {result.return_code}")
                click.echo(f"   Error: {result.error}")
                if result.stderr:
                    click.echo(f"   Stderr: {result.stderr[:200]}")
            sys.exit(1)

    except Exception as exc:
        click.echo("❌ Claude CLI test failed with error\n")
        click.echo(f"   Error: {exc}")
        click.echo("\n   Troubleshooting:")
        click.echo("   - Verify Claude CLI is installed: which claude")
        click.echo("   - Check CLODPUTER_CLAUDE_BIN environment variable")
        click.echo("   - Run: clodputer doctor")
        sys.exit(1)


def main() -> None:  # pragma: no cover
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
