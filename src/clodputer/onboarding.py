"""Interactive onboarding utilities."""

from __future__ import annotations

import difflib
import os
import shlex
import shutil
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import List, Optional, Sequence

import json as json_module

import click
import yaml

from .config import TASKS_DIR, TaskConfig, ensure_tasks_dir, validate_all_tasks
from .formatting import (
    print_completion_header,
    print_dim,
    print_error,
    print_info,
    print_section_title,
    print_step_header,
    print_success,
    print_warning,
)
from .cron import (
    CRON_LOG_FILE,
    CronError,
    generate_cron_section,
    install_cron_jobs,
    preview_schedule,
    scheduled_tasks,
)
from .diagnostics import CheckResult, gather_diagnostics
from .environment import (
    STATE_FILE,
    claude_cli_path,
    onboarding_state,
    reset_state,
    store_claude_cli_path,
    update_state,
)
from .executor import ExecutionResult, TaskExecutionError, TaskExecutor
from .queue import QUEUE_DIR, ensure_queue_dir
from .templates import available as available_templates, export as export_template
from .watcher import (
    WATCHER_LOG_FILE,
    WatcherError,
    file_watch_tasks,
    start_daemon as start_watch_daemon,
    watcher_status,
)

LOG_DIR = QUEUE_DIR / "logs"
ARCHIVE_DIR = QUEUE_DIR / "archive"

# Configuration constants
MEGABYTE = 1024 * 1024
NETWORK_CHECK_TIMEOUT_SECONDS = 3
NETWORK_CHECK_HOST = "1.1.1.1"  # Cloudflare DNS
NETWORK_CHECK_PORT = 53
CLAUDE_CLI_VERIFY_TIMEOUT_SECONDS = 10
CLAUDE_MD_SIZE_WARN_MB = 1
CLAUDE_MD_SIZE_SKIP_DIFF_MB = 5
BACKUP_TIMESTAMP_SUFFIX = ".backup-"
TASK_GENERATION_TIMEOUT_SECONDS = 60


class OnboardingLogger:
    """Capture onboarding output to a persistent transcript with log rotation."""

    MAX_LOG_SIZE_BYTES = 10 * MEGABYTE  # 10 MB
    MAX_BACKUP_COUNT = 5

    def __init__(self) -> None:
        self._original_echo = None
        self._handle = None
        self._path: Optional[Path] = None

    def __enter__(self) -> "OnboardingLogger":
        self._path = _onboarding_log_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate_if_needed()
        self._handle = self._path.open("a", encoding="utf-8")
        self._original_echo = click.echo

        def logging_echo(*args, **kwargs) -> None:
            if self._original_echo:
                self._original_echo(*args, **kwargs)
            self._write_log(args, kwargs)

        click.echo = logging_echo  # type: ignore[assignment]
        return self

    def _rotate_if_needed(self) -> None:
        """Rotate log files if the current log exceeds size limit."""
        if not self._path or not self._path.exists():
            return

        try:
            size = self._path.stat().st_size
            if size <= self.MAX_LOG_SIZE_BYTES:
                return

            # Rotate existing backup files (delete oldest if at max count)
            for i in range(self.MAX_BACKUP_COUNT - 1, 0, -1):
                old_backup = self._path.parent / f"{self._path.name}.{i}"
                new_backup = self._path.parent / f"{self._path.name}.{i + 1}"

                if i == self.MAX_BACKUP_COUNT - 1:
                    # Delete the oldest backup if it exists
                    if new_backup.exists():
                        new_backup.unlink()

                if old_backup.exists():
                    old_backup.rename(new_backup)

            # Move current log to .1
            backup_path = self._path.parent / f"{self._path.name}.1"
            self._path.rename(backup_path)

        except OSError:
            # Non-fatal if rotation fails - continue with existing log
            pass

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._original_echo is not None:
            click.echo = self._original_echo  # type: ignore[assignment]
        if self._handle:
            self._handle.close()

    def _write_log(self, args: tuple, kwargs: dict) -> None:
        if not self._handle:
            return
        target = kwargs.get("file")
        if target not in (None, sys.stdout):
            return
        message = " ".join(str(arg) for arg in args) if args else ""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        entry = f"[{timestamp}] {message}"
        if kwargs.get("nl", True):
            entry += "\n"
        self._handle.write(entry)
        self._handle.flush()


CLAUDE_MD_SENTINEL = "## Clodputer: Autonomous Task Automation"
CLAUDE_MD_SECTION = textwrap.dedent(
    """
    ## Clodputer: Autonomous Task Automation

    Clodputer is installed on this machine. Use it to run autonomous tasks defined in
    `~/.clodputer/tasks`. Each task executes as a single Claude CLI run, so craft prompts that
    contain every instruction and piece of context needed for completion.

    ### Creating or Updating Tasks
    1. Create a YAML file in `~/.clodputer/tasks/<task-name>.yaml`.
    2. Include a `prompt` section with a complete, single-turn instruction set.
    3. Specify any required tools under `allowed_tools` (MCP tools must use the `mcp__` prefix).
    4. When scheduling automation, guide the user to run `clodputer install` (cron) or
       `clodputer watch --daemon` (file watcher) after drafting a task.

    ### Quick Test
    Ask the user to run `clodputer run <task-name>` once after creating a task to validate the flow.
    """
).strip()


def run_onboarding(reset: bool = False) -> None:
    """Execute the interactive onboarding sequence for Clodputer.

    Guides the user through:
    1. Claude CLI detection and configuration
    2. Template installation (starter task templates)
    3. CLAUDE.md setup (project instructions for Claude)
    4. Optional automation (cron jobs, file watcher)
    5. Runtime shortcuts (menu bar app, dashboard)
    6. Smoke test to verify the setup

    All state is persisted to ~/.clodputer/env.json with automatic
    backups and corruption recovery.

    Args:
        reset: If True, clears existing onboarding state before starting.
               Useful for reconfiguring from scratch.

    Example:
        >>> run_onboarding()  # First-time setup
        >>> run_onboarding(reset=True)  # Reconfigure from scratch
    """

    removed_paths = _reset_onboarding_state() if reset else []

    with OnboardingLogger():
        print_section_title("Clodputer Onboarding")

        if reset:
            if removed_paths:
                print_info("Reset onboarding state:")
                for path in removed_paths:
                    click.echo(f"    • Cleared {path}")
            else:
                print_info("No existing onboarding state found to reset.")

        print_step_header(1, 7, "Directory Setup")
        _ensure_directories()

        print_step_header(2, 7, "Claude CLI Configuration")
        selected_path = _choose_claude_cli()
        _verify_claude_cli(selected_path)
        store_claude_cli_path(selected_path)
        print_success(f"Stored Claude CLI path in {STATE_FILE}")

        print_step_header(3, 7, "Intelligent Task Generation")
        # Try intelligent generation first, fall back to templates on failure
        if not _offer_intelligent_task_generation():
            print_info("Using template system instead")
            _offer_template_install()

        print_step_header(4, 7, "CLAUDE.md Integration")
        _offer_claude_md_update()

        print_step_header(5, 7, "Automation Setup")
        configs = _offer_automation()

        print_step_header(6, 7, "Runtime Shortcuts")
        _offer_runtime_shortcuts()

        print_step_header(7, 7, "Smoke Test")
        _offer_smoke_test(configs)

        print_completion_header()
        click.echo("\n  Next steps:")
        click.echo("  • Add tasks to ~/.clodputer/tasks/ (try `clodputer template list`).")
        click.echo("  • Run `clodputer run <task>` to execute a task once.")
        click.echo(
            "  • Use `clodputer install` and `clodputer watch` when you're ready for automation."
        )
        click.echo("  • Re-run `clodputer init` anytime to update settings.")

        results = gather_diagnostics()
        _render_doctor_summary(results)
        _record_onboarding_completion()


def _ensure_directories() -> None:
    ensure_queue_dir()
    ensure_tasks_dir()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    print_success(f"Ensured base directory at {QUEUE_DIR}")
    print_success(f"Ensured tasks directory at {TASKS_DIR}")
    print_success(f"Ensured logs directory at {LOG_DIR}")
    print_success(f"Ensured archive directory at {ARCHIVE_DIR}")


def _onboarding_log_path() -> Path:
    return QUEUE_DIR / "onboarding.log"


def _select_from_list(items: list[str] | list[Path], prompt_text: str, default: int = 1) -> int:
    """Present a numbered list and prompt user to select an item.

    Args:
        items: List of items to display (strings or Paths).
        prompt_text: Text to show in the selection prompt.
        default: Default selection (1-based index). Defaults to 1.

    Returns:
        The 0-based index of the selected item.

    Example:
        >>> templates = ["task1.yaml", "task2.yaml"]
        >>> index = _select_from_list(templates, "Select a template")
        >>> selected = templates[index]
    """
    for index, item in enumerate(items, start=1):
        click.echo(f"    {index}. {item}")

    selection = click.prompt(
        f"  {prompt_text}",
        type=click.IntRange(1, len(items)),
        default=default,
    )
    return selection - 1  # Convert to 0-based index


def _validate_user_path(path: Path, allow_create: bool = True) -> Path:
    """Validate a user-provided path for security.

    Ensures the path:
    1. Is under the user's home directory (prevents traversal to system files)
    2. Does not contain suspicious patterns
    3. Resolves to an absolute path

    Args:
        path: The path to validate.
        allow_create: If False, path must already exist.

    Returns:
        The validated, resolved absolute Path.

    Raises:
        click.ClickException: If path is invalid or suspicious.
    """
    try:
        # Resolve to absolute path and expand user
        resolved = path.expanduser().resolve()

        # Ensure path is under home directory
        home = Path.home().resolve()
        try:
            resolved.relative_to(home)
        except ValueError:
            raise click.ClickException(
                f"Path must be within your home directory ({home}). " f"Provided path: {resolved}"
            )

        # Check if path must exist
        if not allow_create and not resolved.exists():
            raise click.ClickException(f"Path does not exist: {resolved}")

        return resolved

    except (OSError, RuntimeError) as exc:
        raise click.ClickException(f"Invalid path: {exc}") from exc


def _choose_claude_cli() -> str:
    candidate = claude_cli_path(os.getenv("CLODPUTER_CLAUDE_BIN"))
    if candidate:
        try:
            if Path(candidate).exists() and click.confirm(
                f"  Use Claude CLI at {candidate}?", default=True
            ):
                return candidate
        except (OSError, ValueError) as exc:
            print_warning(f"Cannot access {candidate}: {exc}")
            candidate = None

    while True:
        if candidate:
            path_text = click.prompt("  Enter path to Claude CLI executable", default=candidate)
        else:
            path_text = click.prompt("  Enter path to Claude CLI executable")
        path = os.path.expanduser(path_text.strip())

        try:
            if Path(path).exists():
                return path
            print_error("Path not found. Please try again.")
        except (OSError, ValueError) as exc:
            print_error(f"Invalid path: {exc}")
            click.echo("    Please enter a valid file path.")

        candidate = None


def _offer_template_install() -> None:
    templates = available_templates()
    if not templates:
        print_warning("No built-in templates found. Skipping.")
        return

    if not click.confirm("  Copy a starter template into ~/.clodputer/tasks now?", default=True):
        print_dim("Skipped template import.")
        return

    index = _select_from_list(templates, "Select a template number")
    chosen_template = templates[index]

    default_filename = Path(chosen_template).name
    save_as = click.prompt(
        "  Save as (relative to ~/.clodputer/tasks/)", default=default_filename
    ).strip()
    if not save_as:
        save_as = default_filename
    if not save_as.endswith(".yaml"):
        save_as = f"{save_as}.yaml"
    destination = TASKS_DIR / save_as

    if destination.exists():
        if not click.confirm(f"  {destination.name} exists. Overwrite?", default=False):
            print_dim("Skipped template import.")
            return

    written = export_template(chosen_template, destination)
    print_success(f"Copied template to {written}")


def _offer_claude_md_update() -> None:
    candidates = _detect_claude_md_candidates()

    claude_md_path: Path | None = None
    if candidates:
        if len(candidates) == 1:
            claude_md_path = candidates[0]
            if not click.confirm(
                f"  Update CLAUDE.md at {claude_md_path} with Clodputer instructions?",
                default=True,
            ):
                print_dim("Skipped CLAUDE.md update.")
                return
        else:
            print_info("Found multiple CLAUDE.md candidates:")
            index = _select_from_list(candidates, "Select the file to update")
            claude_md_path = candidates[index]
    else:
        print_warning("CLAUDE.md not found in default locations.")
        if not click.confirm("  Provide a path to create or update CLAUDE.md now?", default=False):
            print_dim("Skipped CLAUDE.md integration.")
            return
        entered = click.prompt("  Enter full path to CLAUDE.md").strip()
        user_path = Path(os.path.expanduser(entered))

        try:
            # Validate the path for security
            claude_md_path = _validate_user_path(user_path, allow_create=True)
            claude_md_path.parent.mkdir(parents=True, exist_ok=True)
            if not claude_md_path.exists():
                claude_md_path.touch()
                print_success(f"Created CLAUDE.md at {claude_md_path}")
        except click.ClickException:
            # Re-raise click exceptions (from validation)
            raise

    if claude_md_path is None:
        print_dim("Skipped CLAUDE.md update.")
        return

    _apply_claude_md_update(claude_md_path)


def _load_task_configs() -> tuple[List[TaskConfig], List[tuple[Path, str]]]:
    configs, errors = validate_all_tasks()
    if errors:
        print_warning("Some task configs could not be validated:")
        for path, err in errors:
            click.echo(f"    • {path}: {err}")
    return configs, errors


def _offer_automation(configs: Optional[List[TaskConfig]] = None) -> List[TaskConfig]:
    task_errors: List[tuple[Path, str]] = []
    if configs is None:
        configs, task_errors = _load_task_configs()
    else:
        task_errors = []

    if task_errors:
        print_warning("Resolve task validation errors before enabling automation.")
        return configs

    if not configs:
        print_info("No tasks detected yet. Add YAML files to ~/.clodputer/tasks/.")
        return configs

    _offer_cron_setup(configs)
    _offer_watcher_setup(configs)
    return configs


def _offer_cron_setup(configs: Sequence[TaskConfig]) -> None:
    print_info("Cron scheduling")
    try:
        entries = scheduled_tasks(configs)
    except CronError as exc:
        print_error(f"Unable to prepare cron entries: {exc}")
        return

    if not entries:
        print_dim("No enabled cron or interval tasks found.")
        return

    section = generate_cron_section(entries).strip()
    if section:
        click.echo("\n  Proposed cron section:")
        for line in section.splitlines():
            click.echo(f"    {line}")

    for entry in entries:
        upcoming = []
        try:
            upcoming = preview_schedule(entry, count=3)
        except CronError as exc:
            print_warning(f"Unable to preview schedule for {entry.task.name}: {exc}")
        else:
            click.echo(f"  • {entry.task.name} -> {entry.expression}")
            if entry.timezone:
                click.echo(f"    Timezone: {entry.timezone}")
            if entry.note:
                click.echo(f"    Note: {entry.note}")
            for dt_obj in upcoming:
                click.echo(f"      - {dt_obj.isoformat()}")

    if not click.confirm("\n  Install these cron jobs now?", default=False):
        print_dim("Skipped cron installation.")
        return

    print_info("Installing cron jobs...")
    try:
        result = install_cron_jobs(entries)
        print_success("Cron jobs installed successfully")
    except CronError as exc:
        print_error(f"Failed to install cron jobs: {exc}")
        click.echo("     • macOS users: Grant Full Disk Access to Terminal in System Settings")
        click.echo("     • Or install manually later with: clodputer install")
        return

    print_success(f"Installed {result.get('installed', 0)} cron job(s).")
    backup = result.get("backup")
    if backup:
        click.echo(f"    Backup: {backup}")
    click.echo(f"    Cron log: {CRON_LOG_FILE}")


def _offer_watcher_setup(configs: Sequence[TaskConfig]) -> None:
    print_info("File watcher")
    tasks = file_watch_tasks(configs)
    if not tasks:
        print_dim("No tasks with file_watch triggers detected.")
        return

    for task in tasks:
        trigger = task.trigger
        assert trigger is not None and trigger.type == "file_watch"
        watch_path = Path(trigger.path).expanduser()
        click.echo(
            f"  • {task.name}: path={watch_path} pattern={trigger.pattern} event={trigger.event}"
        )
        if not watch_path.exists():
            if click.confirm(f"    Create missing directory {watch_path}?", default=True):
                try:
                    watch_path.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    print_error(f"Failed to create {watch_path}: {exc}")
                else:
                    print_success(f"Created {watch_path}")
            else:
                print_warning("Directory not created; watcher may not trigger.")

    status = watcher_status()
    if status.get("running"):
        print_success(
            f"Watcher daemon already running (PID {status.get('pid')}). "
            f"Log: {status.get('log_file')}"
        )
        return

    if not click.confirm("\n  Start the watcher daemon now?", default=False):
        print_dim("Skipped watcher daemon start.")
        return

    try:
        pid = start_watch_daemon()
    except WatcherError as exc:
        print_error(f"Failed to start watcher daemon: {exc}")
        click.echo("     • Check that watch paths exist and are readable")
        click.echo("     • Or start manually later with: clodputer watch --daemon")
        return

    print_success(f"Watcher daemon started (PID {pid}). Log: {WATCHER_LOG_FILE}")


def _offer_runtime_shortcuts() -> None:
    print_info("Dashboard shows live queue + logs (opens in Terminal).")

    if sys.platform == "darwin":
        print_info("Menu bar adds status + quick actions (requires accessibility permission).")
        if click.confirm("  Launch the menu bar app now?", default=False):
            _launch_menu_bar_app()

        if click.confirm("  Open the dashboard in a new Terminal window?", default=False):
            _launch_dashboard_terminal()
        else:
            print_dim("Run `clodputer dashboard` anytime for a live view.")
    else:
        print_info("Menu bar is only available on macOS.")
        print_dim("Run `clodputer dashboard` anytime for a live view.")


def _launch_menu_bar_app() -> None:
    command = [sys.executable, "-m", "clodputer.cli", "menu"]
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        print_error(f"Failed to launch menu bar app: {exc}")
    else:
        print_success("Menu bar launched (look for the Clodputer icon in the macOS menu bar).")


def _launch_dashboard_terminal() -> None:
    command = shlex.join(["clodputer", "dashboard"])
    script = f'tell application "Terminal"\n  activate\n  do script "{command}"\nend tell'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        print_error(f"Failed to launch dashboard: {exc}")
    else:
        print_success("Dashboard opened in a new Terminal window.")


def _offer_smoke_test(configs: Optional[Sequence[TaskConfig]] = None) -> None:
    task_errors: List[tuple[Path, str]] = []
    if configs is None:
        configs, task_errors = _load_task_configs()
    else:
        configs = list(configs)
    if task_errors and not configs:
        print_dim("Skipping smoke test until configuration errors are resolved.")
        return

    enabled_tasks = [task for task in configs if task.enabled]
    if not enabled_tasks:
        print_dim("No enabled tasks available yet.")
        return

    # Check network connectivity before offering smoke test
    if not _check_network_connectivity():
        print_warning("Network connectivity issue detected.")
        click.echo("     Tasks may require internet access to complete successfully.")
        if not click.confirm("  Continue with smoke test anyway?", default=False):
            print_dim("Skipped smoke test. Check your network connection and try again.")
            return

    if not click.confirm("  Run a task now to verify end-to-end execution?", default=False):
        print_dim("Skipped smoke test.")
        return

    for index, task in enumerate(enabled_tasks, start=1):
        click.echo(f"    {index}. {task.name}")

    selection = click.prompt(
        "  Select a task number",
        type=click.IntRange(1, len(enabled_tasks)),
        default=1,
    )
    chosen = enabled_tasks[selection - 1]

    print_info(f"Running task '{chosen.name}'...")
    executor = TaskExecutor()
    try:
        result = executor.run_task_by_name(chosen.name)
    except TaskExecutionError as exc:
        print_error(f"Task execution failed: {exc}")
        cli_path = claude_cli_path(None)
        click.echo("     • Check logs: clodputer logs --tail 20")
        if cli_path:
            click.echo(f"     • Verify Claude CLI: {cli_path} --version")
        click.echo("     • Run diagnostics: clodputer doctor")
        return
    except Exception as exc:  # pragma: no cover - defensive
        print_error(f"Smoke test errored: {exc}")
        click.echo("     • Check logs: clodputer logs --tail 20")
        click.echo("     • Run diagnostics: clodputer doctor")
        return

    _render_smoke_test_result(result)


def _render_smoke_test_result(result: ExecutionResult) -> None:
    status_symbol = {"success": "✅", "failure": "❌", "timeout": "⏱️", "error": "⚠️"}.get(
        getattr(result, "status", ""), "ℹ️"
    )
    duration = getattr(result, "duration", 0.0) or 0.0
    duration_str = _format_seconds(duration)
    click.echo(
        f"  {status_symbol} {getattr(result, 'task_name', 'task')} finished with status "
        f"{getattr(result, 'status', 'unknown')} in {duration_str}."
    )
    if getattr(result, "output_parse_error", None):
        click.echo(f"    Output parse error: {result.output_parse_error}")
    elif getattr(result, "output_json", None) is not None:
        # Show a concise summary instead of dumping the entire JSON
        output = result.output_json
        if isinstance(output, dict):
            # Extract key metrics from the output
            if "result" in output:
                result_text = output["result"]
                # Try to show a brief summary
                lines = str(result_text).split('\n')[:3]  # First 3 lines
                summary = '\n    '.join(lines)
                click.echo(f"    Result preview: {summary}...")
            if "num_turns" in output:
                click.echo(f"    Turns: {output['num_turns']}")
            if "total_cost_usd" in output:
                cost = output['total_cost_usd']
                click.echo(f"    Cost: ${cost:.4f}")
        else:
            # Fallback for non-dict output
            output_str = str(output)
            if len(output_str) > 200:
                click.echo(f"    Output: {output_str[:200]}...")
            else:
                click.echo(f"    Output: {output_str}")
        click.echo(f"    💡 View full output with: clodputer logs --task {getattr(result, 'task_name', '')}")
    if getattr(result, "error", None):
        click.echo(f"    Error: {result.error}")
    cleanup = getattr(result, "cleanup", None)
    if cleanup and getattr(cleanup, "actions", None):
        click.echo(f"    Cleanup actions: {cleanup.actions}")


def _format_seconds(seconds: float) -> str:
    seconds = float(seconds or 0.0)
    minutes, remainder = divmod(int(seconds), 60)
    if minutes:
        return f"{minutes}m{remainder:02d}s"
    return f"{remainder}s"


def _check_network_connectivity() -> bool:
    """Check if network connectivity is available.

    Attempts a quick DNS lookup to verify internet connectivity.
    Uses Cloudflare's 1.1.1.1 DNS server as a reliable test endpoint.

    Returns:
        True if network is available, False otherwise.

    Example:
        >>> if not _check_network_connectivity():
        ...     click.echo("  ⚠️ Network connectivity issue detected")
    """
    try:
        # Try to resolve a DNS name (Cloudflare's DNS)
        socket.create_connection(
            (NETWORK_CHECK_HOST, NETWORK_CHECK_PORT), timeout=NETWORK_CHECK_TIMEOUT_SECONDS
        )
        return True
    except (socket.timeout, socket.error, OSError):
        return False


def _render_doctor_summary(results: Sequence[CheckResult]) -> None:
    """Render a summary of diagnostic checks, filtering out optional ones during onboarding."""
    # Filter out optional checks that might fail during onboarding
    # These are user choices, not actual problems
    optional_check_names = {
        "Clodputer cron jobs installed",  # User may choose not to install cron
        "Onboarding completion recorded",  # Will be set after this function returns
    }

    # Show all checks but mark optional ones differently
    required_results = [r for r in results if r.name not in optional_check_names]
    optional_results = [r for r in results if r.name in optional_check_names]

    click.echo("\nSetup complete! 🎉")

    # Show required checks
    if required_results:
        required_passed = sum(1 for r in required_results if r.passed)
        required_total = len(required_results)
        click.echo(f"  • {required_passed}/{required_total} required checks passing.")

        # Show any failing required checks
        failing_required = [r for r in required_results if not r.passed]
        if failing_required:
            click.echo("  ⚠️ Issues detected:")
            for result in failing_required:
                click.echo(f"  ❌ {result.name}")
                if result.details:
                    for detail in result.details:
                        click.echo(f"      {detail}")

    # Show optional items status without treating them as errors
    if optional_results:
        skipped_optional = [r for r in optional_results if not r.passed]
        if skipped_optional:
            click.echo("  ℹ️  Optional setup items:")
            for result in skipped_optional:
                # Use a neutral indicator, not an error symbol
                if "cron" in result.name.lower():
                    click.echo("  ⊝ Cron scheduling not installed (optional)")
                    click.echo("      Run `clodputer install` to enable scheduled tasks")

    click.echo("  💡 Run `clodputer doctor` anytime for full diagnostics.")


def _record_onboarding_completion() -> None:
    state = onboarding_state()
    try:
        runs = int(state.get("onboarding_runs", 0) or 0)
    except (TypeError, ValueError):
        runs = 0
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    update_state({
        "onboarding_last_run": timestamp,
        "onboarding_runs": runs + 1,
        "onboarding_completed_at": timestamp
    })


def _reset_onboarding_state() -> List[str]:
    removed: List[str] = []
    if STATE_FILE.exists():
        reset_state()
        removed.append(str(STATE_FILE))
    log_path = _onboarding_log_path()
    if log_path.exists():
        log_path.unlink()
        removed.append(str(log_path))
    return removed


def _detect_claude_md_candidates() -> list[Path]:
    locations = [
        Path.home() / "CLAUDE.md",
        Path.home() / ".config" / "claude" / "CLAUDE.md",
        Path.home() / "Documents" / "CLAUDE.md",
    ]
    return [path for path in locations if path.exists()]


def _apply_claude_md_update(path: Path) -> None:
    # Check file size before loading
    try:
        file_size = path.stat().st_size
    except OSError as exc:
        raise click.ClickException(f"Failed to check {path}: {exc}") from exc

    # Warn if file is large (>1MB), skip diff if >5MB
    if file_size > CLAUDE_MD_SIZE_SKIP_DIFF_MB * MEGABYTE:
        print_warning(f"CLAUDE.md is very large ({file_size // MEGABYTE}MB).")
        click.echo("     Skipping diff preview to avoid memory issues.")
        if not click.confirm("  Add Clodputer guidance without preview?", default=False):
            print_dim("Skipped CLAUDE.md update.")
            return
        skip_diff = True
    elif file_size > CLAUDE_MD_SIZE_WARN_MB * MEGABYTE:
        print_warning(f"CLAUDE.md is large ({file_size // MEGABYTE}MB). Diff may be slow.")
        skip_diff = False
    else:
        skip_diff = False

    try:
        current_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(f"Failed to read {path}: {exc}") from exc

    if CLAUDE_MD_SENTINEL in current_text:
        print_info("CLAUDE.md already includes Clodputer guidance.")
        return

    addition = CLAUDE_MD_SECTION.strip() + "\n"
    if current_text.strip():
        new_text = current_text.rstrip() + "\n\n" + addition
    else:
        new_text = addition
    if not new_text.endswith("\n"):
        new_text += "\n"

    if skip_diff:
        # Skip diff for very large files
        diff = None
    else:
        diff = "".join(
            difflib.unified_diff(
                current_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path),
            )
        )

    if diff is not None:
        if not diff:
            print_info("No changes required for CLAUDE.md.")
            return

        click.echo("\n  Proposed CLAUDE.md update:")
        diff_lines = diff.splitlines()
        preview_limit = 80
        for line in diff_lines[:preview_limit]:
            click.echo(f"    {line}")
        if len(diff_lines) > preview_limit:
            click.echo("    ... (diff truncated)")

        if not click.confirm("\n  Apply this update?", default=True):
            print_dim("Skipped CLAUDE.md update.")
            return
    # If diff is None, we already confirmed above for large files

    backup_path = path.with_name(f"{path.name}{BACKUP_TIMESTAMP_SUFFIX}{int(time.time())}")
    try:
        shutil.copy2(path, backup_path)
    except FileNotFoundError:
        backup_path = None
    except OSError as exc:
        raise click.ClickException(f"Failed to back up CLAUDE.md: {exc}") from exc

    try:
        path.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(f"Failed to update {path}: {exc}") from exc

    if backup_path:
        print_success(f"Updated CLAUDE.md (backup at {backup_path})")
    else:
        print_success("Updated CLAUDE.md")


def _verify_claude_cli(path: str) -> None:
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=CLAUDE_CLI_VERIFY_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(f"Claude CLI not executable at {path}") from exc
    except subprocess.TimeoutExpired:
        print_warning(
            f"Claude CLI --version timed out after {CLAUDE_CLI_VERIFY_TIMEOUT_SECONDS} seconds."
        )
        click.echo("     This may indicate an issue with the Claude installation.")
        return

    if result.returncode != 0:
        print_warning("Unable to confirm Claude CLI version (non-zero exit code).")
    else:
        version_line = (result.stdout or result.stderr or "").strip().splitlines()[:1]
        if version_line:
            print_success(f"Detected Claude CLI: {version_line[0]}")
        else:
            print_success("Claude CLI responded to --version.")


def _build_task_generation_prompt(mcps: list[dict]) -> str:
    """Build the prompt for generating personalized task suggestions.

    Args:
        mcps: List of detected MCPs with their metadata

    Returns:
        Complete prompt string for Claude Code to generate tasks
    """
    # Filter to only connected MCPs
    connected_mcps = [m for m in mcps if m["status"] == "connected"]

    # Build MCP context
    if connected_mcps:
        mcp_section = "Available MCPs in this Claude Code installation:\n"
        for mcp in connected_mcps:
            mcp_section += f"- {mcp['name']}: {mcp['command']}\n"
    else:
        mcp_section = "No MCPs are currently configured in Claude Code.\n"

    # MCP-specific task guidance
    task_guidance = ""
    mcp_names = {m["name"] for m in connected_mcps}

    if "gmail" in mcp_names:
        task_guidance += """
- Email MCP detected: Consider email triage, inbox summarization, or draft response tasks
  Examples: morning-email-triage, newsletter-digest, urgent-email-alerts
"""

    if any(cal in mcp_names for cal in ["google-calendar", "calendar"]):
        task_guidance += """
- Calendar MCP detected: Consider meeting prep, schedule analysis, or availability tasks
  Examples: meeting-prep, schedule-optimizer, calendar-summary
"""

    if any(search in mcp_names for search in ["google-search", "duckduckgo-search", "crawl4ai"]):
        task_guidance += """
- Search/Crawl MCPs detected: Consider research, monitoring, or content extraction tasks
  Examples: daily-news-brief, competitor-monitor, topic-research
"""

    if any(docs in mcp_names for docs in ["google-docs", "ultimate-google-docs", "google-drive"]):
        task_guidance += """
- Document MCPs detected: Consider document organization, summarization, or collaboration tasks
  Examples: doc-organizer, meeting-notes-summary, shared-doc-monitor
"""

    if not task_guidance:
        task_guidance = """
- No specialized MCPs detected: Consider file operations, git automation, or system tasks
  Examples: git-health-check, downloads-cleanup, todo-reminder, repo-analyzer
"""

    # Complete prompt
    prompt = f"""You are helping set up Clodputer, an autonomous task automation system that runs Claude Code tasks on a schedule.

{mcp_section}

Your goal: Generate exactly 3 useful, safe, and immediately valuable task suggestions for this user.

{task_guidance}

IMPORTANT REQUIREMENTS:
1. Each task must be IMMEDIATELY USEFUL (not a toy example)
2. Tasks should complete in 30-60 seconds
3. NO destructive operations (no delete, rm, drop, uninstall commands)
4. Use available MCPs when relevant, but don't force it
5. Include complete, valid YAML configuration
6. Add helpful comments in the YAML
7. Set reasonable schedules (cron expressions)

OUTPUT FORMAT (must be valid JSON):
{{
  "tasks": [
    {{
      "name": "task-filename",
      "description": "Brief user-facing description of value (1-2 sentences)",
      "yaml_config": "Complete YAML including name, prompt, allowed_tools, trigger",
      "reasoning": "Why this task is useful for this user (internal, not shown)"
    }}
  ]
}}

YAML TEMPLATE for each task:
```yaml
name: task-name
prompt: |
  Clear, specific instructions for Claude.
  Explain what to do, what tools to use, what output to produce.
allowed_tools:
  - tool_name_1
  - tool_name_2
trigger:
  type: cron
  expression: "0 9 * * *"  # Daily at 9am
  timezone: America/Los_Angeles
enabled: true
```

Generate 3 tasks now. Focus on practical value and safety."""

    return prompt


def _generate_task_suggestions(mcps: list[dict]) -> Optional[list[dict]]:
    """Use Claude Code to generate personalized task suggestions.

    Args:
        mcps: List of detected MCPs with metadata

    Returns:
        List of task dicts with name, description, yaml_config, reasoning.
        Returns None if generation fails.

    Example:
        >>> tasks = _generate_task_suggestions(mcps)
        >>> tasks[0]["name"]
        'morning-email-triage'
    """
    try:
        # Get Claude CLI path
        cli_path = claude_cli_path(None)
        if not cli_path:
            click.echo("    [debug] Claude CLI path not found", err=True)
            return None

        # Build the prompt
        prompt = _build_task_generation_prompt(mcps)

        # Invoke Claude Code in headless mode
        result = subprocess.run(
            [cli_path, "--headless", "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=TASK_GENERATION_TIMEOUT_SECONDS,
            check=False,
        )

        if result.returncode != 0:
            click.echo(f"    [debug] Claude CLI returned code {result.returncode}", err=True)
            if result.stderr:
                click.echo(f"    [debug] stderr: {result.stderr[:200]}", err=True)
            return None

        # Parse JSON response
        try:
            response = json_module.loads(result.stdout)
        except json_module.JSONDecodeError as exc:
            click.echo(f"    [debug] JSON parse error: {exc}", err=True)
            click.echo(f"    [debug] stdout: {result.stdout[:200]}", err=True)
            return None

        # Validate response structure
        if not isinstance(response, dict) or "tasks" not in response:
            click.echo("    [debug] Invalid response structure", err=True)
            return None

        tasks = response["tasks"]
        if not isinstance(tasks, list):
            click.echo("    [debug] 'tasks' is not a list", err=True)
            return None

        # Accept 1-3 tasks (not strict on 3)
        if len(tasks) == 0 or len(tasks) > 3:
            click.echo(f"    [debug] Got {len(tasks)} tasks, expected 1-3", err=True)
            return None

        # Validate each task
        validated_tasks = []
        for idx, task in enumerate(tasks):
            if _validate_generated_task(task):
                validated_tasks.append(task)
            else:
                click.echo(f"    [debug] Task {idx + 1} failed validation", err=True)

        # Need at least 1 valid task
        if not validated_tasks:
            click.echo("    [debug] No tasks passed validation", err=True)
            return None

        return validated_tasks

    except subprocess.TimeoutExpired:
        click.echo(f"    [debug] Generation timed out after {TASK_GENERATION_TIMEOUT_SECONDS}s", err=True)
        return None
    except (FileNotFoundError, OSError) as exc:
        click.echo(f"    [debug] Subprocess error: {exc}", err=True)
        return None


def _validate_generated_task(task: dict) -> bool:
    """Validate a single generated task for safety and correctness.

    Args:
        task: Task dict with name, description, yaml_config, reasoning

    Returns:
        True if task is valid and safe, False otherwise
    """
    # Check required fields
    required_fields = ["name", "description", "yaml_config"]
    if not all(field in task for field in required_fields):
        return False

    # Validate name is a safe filename
    name = task.get("name", "")
    if not name or "/" in name or "\\" in name or ".." in name:
        return False

    # Validate YAML syntax
    yaml_config = task.get("yaml_config", "")
    try:
        parsed = yaml.safe_load(yaml_config)
        if not isinstance(parsed, dict):
            return False
    except Exception:
        return False

    # Safety check: scan for destructive keywords
    dangerous_keywords = [
        "rm -rf",
        "delete",
        "drop database",
        "drop table",
        "uninstall",
        "sudo rm",
        "format",
        "mkfs",
    ]

    yaml_lower = yaml_config.lower()
    for keyword in dangerous_keywords:
        if keyword in yaml_lower:
            return False

    # Check that task has a prompt
    if "prompt" not in parsed or not parsed["prompt"]:
        return False

    return True


def _detect_available_mcps() -> list[dict]:
    """Detect what MCPs the user has configured in Claude Code.

    Returns:
        List of dicts with MCP metadata: [{"name": str, "status": str, "command": str}]
        Returns empty list if detection fails.

    Example:
        >>> mcps = _detect_available_mcps()
        >>> [m["name"] for m in mcps if m["status"] == "connected"]
        ['gmail', 'calendar', 'crawl4ai']
    """
    try:
        # Get the claude CLI path
        cli_path = claude_cli_path(None)
        if not cli_path:
            return []

        # Run `claude mcp list`
        result = subprocess.run(
            [cli_path, "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            return []

        # Parse the output
        return _parse_mcp_list_output(result.stdout)

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def _parse_mcp_list_output(output: str) -> list[dict]:
    """Parse the output of `claude mcp list`.

    Expected format:
        Checking MCP server health...

        name: command - ✓ Connected
        name: command - ✗ Failed to connect

    Args:
        output: Raw stdout from `claude mcp list`

    Returns:
        List of dicts with MCP info: [{"name": str, "status": str, "command": str}]
    """
    mcps = []

    for line in output.splitlines():
        line = line.strip()

        # Skip header and empty lines
        if not line or "Checking MCP" in line:
            continue

        # Look for pattern: "name: command - ✓ Connected" or "name: command - ✗ Failed"
        if ":" in line and ("-" in line):
            try:
                # Split on first colon to get name
                name_part, rest = line.split(":", 1)
                name = name_part.strip()

                # Split on last dash to get status
                if " - " in rest:
                    command_part, status_part = rest.rsplit(" - ", 1)
                    command = command_part.strip()
                    status = status_part.strip()

                    # Normalize status
                    if "Connected" in status or "✓" in status:
                        normalized_status = "connected"
                    else:
                        normalized_status = "failed"

                    mcps.append({
                        "name": name,
                        "command": command,
                        "status": normalized_status,
                    })
            except ValueError:
                # Skip malformed lines
                continue

    return mcps


def _offer_intelligent_task_generation() -> bool:
    """Offer AI-generated task suggestions based on user's MCP setup.

    Returns:
        True if tasks were generated and installed successfully.
        False if generation failed (caller should fall back to templates).
    """
    # Check if user wants to skip intelligent generation
    if os.environ.get("CLODPUTER_SKIP_INTELLIGENT_GENERATION"):
        click.echo("    Skipping intelligent generation (CLODPUTER_SKIP_INTELLIGENT_GENERATION set)")
        return False

    print_info("Analyzing your Claude Code setup...")

    # Detect MCPs
    mcps = _detect_available_mcps()
    connected_count = sum(1 for m in mcps if m["status"] == "connected")

    if mcps:
        click.echo(f"    Found {len(mcps)} MCP(s), {connected_count} connected")
    else:
        click.echo("    No MCPs detected")

    # Optionally skip generation if user says no
    if not click.confirm("\n  Generate AI-powered task suggestions based on your setup?", default=True):
        print_dim("Skipped intelligent generation")
        return False

    # Generate task suggestions
    print_info("Generating personalized task suggestions...")
    click.echo("    This may take 30-60 seconds...")

    tasks = _generate_task_suggestions(mcps)

    if not tasks:
        print_warning("Could not generate task suggestions")
        click.echo("    Possible reasons:")
        click.echo("      • Claude CLI may not support --headless mode")
        click.echo("      • Network connectivity issues")
        click.echo("      • Task validation failed for safety")
        click.echo("    Will use template system instead")
        return False

    # Present tasks to user
    click.echo(f"\n  📋 Generated {len(tasks)} task suggestion(s) for you:\n")

    for idx, task in enumerate(tasks, 1):
        click.echo(f"  {idx}. {task['name']}")
        click.echo(f"     {task['description']}")
        click.echo()

    # Get user selection
    if len(tasks) == 1:
        default_selection = "1"
    else:
        default_selection = "all"

    try:
        selection = click.prompt(
            "  Select tasks to install (e.g., '1,3' or 'all', or 'none' to skip)",
            default=default_selection,
            type=str,
        ).strip()
    except (KeyboardInterrupt, EOFError):
        print_dim("\nCancelled task selection")
        return False

    # Parse selection
    if selection.lower() == "all":
        selected_indices = list(range(len(tasks)))
    elif selection.lower() == "none" or not selection:
        print_dim("No tasks selected")
        return False
    else:
        try:
            # Parse comma-separated numbers
            selected_indices = []
            for part in selection.split(","):
                part = part.strip()
                if not part:
                    continue
                idx = int(part) - 1  # Convert to 0-based
                if 0 <= idx < len(tasks):
                    selected_indices.append(idx)
                else:
                    print_warning(f"Invalid selection: {part} (out of range)")
        except ValueError as exc:
            print_error(f"Invalid selection format: {exc}")
            print_dim("Expected format: '1,3' or 'all' or 'none'")
            return False

    if not selected_indices:
        print_dim("No valid tasks selected")
        return False

    # Install selected tasks
    click.echo()
    installed_count = 0

    for idx in selected_indices:
        task = tasks[idx]
        filename = f"{task['name']}.yaml"
        filepath = TASKS_DIR / filename

        # Check for conflicts
        if filepath.exists():
            try:
                if not click.confirm(f"  {filename} exists. Overwrite?", default=False):
                    print_dim(f"Skipped {filename}")
                    continue
            except (KeyboardInterrupt, EOFError):
                print_dim(f"\nSkipped {filename}")
                continue

        # Write task file
        try:
            filepath.write_text(task['yaml_config'], encoding='utf-8')
            print_success(f"Created {filename}")
            installed_count += 1
        except OSError as exc:
            print_error(f"Failed to create {filename}: {exc}")

    if installed_count > 0:
        click.echo(f"\n  🎉 Installed {installed_count} task(s) successfully")
        return True
    else:
        print_warning("No tasks were installed")
        return False


__all__ = ["run_onboarding"]
