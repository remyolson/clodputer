"""Interactive onboarding utilities."""

from __future__ import annotations

import difflib
import os
import shlex
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import List, Optional, Sequence

import click

from .config import TASKS_DIR, TaskConfig, ensure_tasks_dir, validate_all_tasks
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
from .executor import TaskExecutionError, TaskExecutor
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


class OnboardingLogger:
    """Capture onboarding output to a persistent transcript."""

    def __init__(self) -> None:
        self._original_echo = None
        self._handle = None
        self._path: Optional[Path] = None

    def __enter__(self) -> "OnboardingLogger":
        self._path = _onboarding_log_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._path.open("a", encoding="utf-8")
        self._original_echo = click.echo

        def logging_echo(*args, **kwargs) -> None:
            if self._original_echo:
                self._original_echo(*args, **kwargs)
            self._write_log(args, kwargs)

        click.echo = logging_echo  # type: ignore[assignment]
        return self

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
    """Execute the interactive onboarding sequence."""

    removed_paths = _reset_onboarding_state() if reset else []

    with OnboardingLogger():
        click.echo("\n=== Clodputer Onboarding ===")

        if reset:
            if removed_paths:
                click.echo("Reset onboarding state:")
                for path in removed_paths:
                    click.echo(f"  • Cleared {path}")
            else:
                click.echo("No existing onboarding state found to reset.")

        _ensure_directories()

        click.echo("\nClaude CLI configuration")
        selected_path = _choose_claude_cli()
        _verify_claude_cli(selected_path)
        store_claude_cli_path(selected_path)
        click.echo(f"  ✓ Stored Claude CLI path in {STATE_FILE}")

        _offer_template_install()
        _offer_claude_md_update()

        configs = _offer_automation()
        _offer_runtime_shortcuts()
        _offer_smoke_test(configs)

        click.echo("\nSetup complete! Next steps:")
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
    click.echo(f"  ✓ Ensured base directory at {QUEUE_DIR}")
    click.echo(f"  ✓ Ensured tasks directory at {TASKS_DIR}")
    click.echo(f"  ✓ Ensured logs directory at {LOG_DIR}")
    click.echo(f"  ✓ Ensured archive directory at {ARCHIVE_DIR}")


def _onboarding_log_path() -> Path:
    return QUEUE_DIR / "onboarding.log"


def _choose_claude_cli() -> str:
    candidate = claude_cli_path(os.getenv("CLODPUTER_CLAUDE_BIN"))
    if candidate:
        if Path(candidate).exists() and click.confirm(
            f"  Use Claude CLI at {candidate}?", default=True
        ):
            return candidate

    while True:
        if candidate:
            path_text = click.prompt("  Enter path to Claude CLI executable", default=candidate)
        else:
            path_text = click.prompt("  Enter path to Claude CLI executable")
        path = os.path.expanduser(path_text.strip())
        if Path(path).exists():
            return path
        click.echo("  ❌ Path not found. Please try again.")
        candidate = None


def _offer_template_install() -> None:
    click.echo("\nStarter task templates")
    templates = available_templates()
    if not templates:
        click.echo("  ⚠️ No built-in templates found. Skipping.")
        return

    if not click.confirm("  Copy a starter template into ~/.clodputer/tasks now?", default=True):
        click.echo("  • Skipped template import.")
        return

    for index, name in enumerate(templates, start=1):
        click.echo(f"    {index}. {name}")

    selection = click.prompt(
        "  Select a template number",
        type=click.IntRange(1, len(templates)),
        default=1,
    )
    chosen_template = templates[selection - 1]

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
            click.echo("  • Skipped template import.")
            return

    written = export_template(chosen_template, destination)
    click.echo(f"  ✓ Copied template to {written}")


def _offer_claude_md_update() -> None:
    click.echo("\nCLAUDE.md integration")
    candidates = _detect_claude_md_candidates()

    claude_md_path: Path | None = None
    if candidates:
        if len(candidates) == 1:
            claude_md_path = candidates[0]
            if not click.confirm(
                f"  Update CLAUDE.md at {claude_md_path} with Clodputer instructions?",
                default=True,
            ):
                click.echo("  • Skipped CLAUDE.md update.")
                return
        else:
            click.echo("  Found multiple CLAUDE.md candidates:")
            for index, path in enumerate(candidates, start=1):
                click.echo(f"    {index}. {path}")
            selection = click.prompt(
                "  Select the file to update",
                type=click.IntRange(1, len(candidates)),
                default=1,
            )
            claude_md_path = candidates[selection - 1]
    else:
        click.echo("  ⚠️ CLAUDE.md not found in default locations.")
        if not click.confirm("  Provide a path to create or update CLAUDE.md now?", default=False):
            click.echo("  • Skipped CLAUDE.md integration.")
            return
        entered = click.prompt("  Enter full path to CLAUDE.md").strip()
        claude_md_path = Path(os.path.expanduser(entered)).expanduser()
        claude_md_path.parent.mkdir(parents=True, exist_ok=True)
        if not claude_md_path.exists():
            claude_md_path.touch()
            click.echo(f"  ✓ Created CLAUDE.md at {claude_md_path}")

    if claude_md_path is None:
        click.echo("  • Skipped CLAUDE.md update.")
        return

    _apply_claude_md_update(claude_md_path)


def _load_task_configs() -> tuple[List[TaskConfig], List[tuple[Path, str]]]:
    configs, errors = validate_all_tasks()
    if errors:
        click.echo("\n⚠️  Some task configs could not be validated:")
        for path, err in errors:
            click.echo(f"  • {path}: {err}")
    return configs, errors


def _offer_automation(configs: Optional[List[TaskConfig]] = None) -> List[TaskConfig]:
    click.echo("\nAutomation options")
    task_errors: List[tuple[Path, str]] = []
    if configs is None:
        configs, task_errors = _load_task_configs()
    else:
        task_errors = []

    if task_errors:
        click.echo("  ⚠️ Resolve task validation errors before enabling automation.")
        return configs

    if not configs:
        click.echo("  • No tasks detected yet. Add YAML files to ~/.clodputer/tasks/.")
        return configs

    _offer_cron_setup(configs)
    _offer_watcher_setup(configs)
    return configs


def _offer_cron_setup(configs: Sequence[TaskConfig]) -> None:
    click.echo("\nCron scheduling")
    try:
        entries = scheduled_tasks(configs)
    except CronError as exc:
        click.echo(f"  ❌ Unable to prepare cron entries: {exc}")
        return

    if not entries:
        click.echo("  • No enabled cron or interval tasks found.")
        return

    section = generate_cron_section(entries).strip()
    if section:
        click.echo("  Proposed cron section:")
        for line in section.splitlines():
            click.echo(f"    {line}")

    for entry in entries:
        upcoming = []
        try:
            upcoming = preview_schedule(entry, count=3)
        except CronError as exc:
            click.echo(f"  ⚠️ Unable to preview schedule for {entry.task.name}: {exc}")
        else:
            click.echo(f"  • {entry.task.name} -> {entry.expression}")
            if entry.timezone:
                click.echo(f"    Timezone: {entry.timezone}")
            if entry.note:
                click.echo(f"    Note: {entry.note}")
            for dt_obj in upcoming:
                click.echo(f"      - {dt_obj.isoformat()}")

    if not click.confirm("  Install these cron jobs now?", default=False):
        click.echo("  • Skipped cron installation.")
        return

    try:
        result = install_cron_jobs(entries)
    except CronError as exc:
        click.echo(f"  ❌ Failed to install cron jobs: {exc}")
        return

    click.echo(f"  ✓ Installed {result.get('installed', 0)} cron job(s).")
    backup = result.get("backup")
    if backup:
        click.echo(f"    Backup: {backup}")
    click.echo(f"    Cron log: {CRON_LOG_FILE}")


def _offer_watcher_setup(configs: Sequence[TaskConfig]) -> None:
    click.echo("\nFile watcher")
    tasks = file_watch_tasks(configs)
    if not tasks:
        click.echo("  • No tasks with file_watch triggers detected.")
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
                    click.echo(f"    ❌ Failed to create {watch_path}: {exc}")
                else:
                    click.echo(f"    ✓ Created {watch_path}")
            else:
                click.echo("    ⚠️ Directory not created; watcher may not trigger.")

    status = watcher_status()
    if status.get("running"):
        click.echo(
            f"  ✓ Watcher daemon already running (PID {status.get('pid')}). "
            f"Log: {status.get('log_file')}"
        )
        return

    if not click.confirm("  Start the watcher daemon now?", default=False):
        click.echo("  • Skipped watcher daemon start.")
        return

    try:
        pid = start_watch_daemon()
    except WatcherError as exc:
        click.echo(f"  ❌ Failed to start watcher daemon: {exc}")
        return

    click.echo(f"  ✓ Watcher daemon started (PID {pid}). Log: {WATCHER_LOG_FILE}")


def _offer_runtime_shortcuts() -> None:
    click.echo("\nRuntime helpers")
    click.echo("  • Dashboard shows live queue + logs (opens in Terminal).")

    if sys.platform == "darwin":
        click.echo("  • Menu bar adds status + quick actions (requires accessibility permission).")
        if click.confirm("  Launch the menu bar app now?", default=False):
            _launch_menu_bar_app()

        if click.confirm("  Open the dashboard in a new Terminal window?", default=False):
            _launch_dashboard_terminal()
        else:
            click.echo("  • Run `clodputer dashboard` anytime for a live view.")
    else:
        click.echo("  • Menu bar is only available on macOS.")
        click.echo("  • Run `clodputer dashboard` anytime for a live view.")


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
        click.echo(f"  ❌ Failed to launch menu bar app: {exc}")
    else:
        click.echo("  ✓ Menu bar launched (look for the Clodputer icon in the macOS menu bar).")


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
        click.echo(f"  ❌ Failed to launch dashboard: {exc}")
    else:
        click.echo("  ✓ Dashboard opened in a new Terminal window.")


def _offer_smoke_test(configs: Optional[Sequence[TaskConfig]] = None) -> None:
    click.echo("\nSmoke test")
    task_errors: List[tuple[Path, str]] = []
    if configs is None:
        configs, task_errors = _load_task_configs()
    else:
        configs = list(configs)
    if task_errors and not configs:
        click.echo("  • Skipping smoke test until configuration errors are resolved.")
        return

    enabled_tasks = [task for task in configs if task.enabled]
    if not enabled_tasks:
        click.echo("  • No enabled tasks available yet.")
        return

    if not click.confirm("  Run a task now to verify end-to-end execution?", default=False):
        click.echo("  • Skipped smoke test.")
        return

    for index, task in enumerate(enabled_tasks, start=1):
        click.echo(f"    {index}. {task.name}")

    selection = click.prompt(
        "  Select a task number",
        type=click.IntRange(1, len(enabled_tasks)),
        default=1,
    )
    chosen = enabled_tasks[selection - 1]

    executor = TaskExecutor()
    try:
        result = executor.run_task_by_name(chosen.name)
    except TaskExecutionError as exc:
        click.echo(f"  ❌ Task execution failed: {exc}")
        return
    except Exception as exc:  # pragma: no cover - defensive
        click.echo(f"  ❌ Smoke test errored: {exc}")
        return

    _render_smoke_test_result(result)


def _render_smoke_test_result(result) -> None:
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
        click.echo(f"    Output JSON: {result.output_json}")
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


def _render_doctor_summary(results: Sequence[CheckResult]) -> None:
    click.echo("\nDoctor summary")
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    click.echo(f"  • {passed}/{total} checks passing.")

    if passed == total:
        click.echo("  ✅ All diagnostics passed.")
        return

    click.echo("  ⚠️ Issues detected:")
    for result in results:
        if result.passed:
            continue
        click.echo(f"  ❌ {result.name}")
        if result.details:
            for detail in result.details:
                click.echo(f"      {detail}")
    click.echo("  ℹ️ Run `clodputer doctor` for full diagnostics.")


def _record_onboarding_completion() -> None:
    state = onboarding_state()
    try:
        runs = int(state.get("onboarding_runs", 0) or 0)
    except (TypeError, ValueError):
        runs = 0
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    update_state({"onboarding_last_run": timestamp, "onboarding_runs": runs + 1})


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
    try:
        current_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(f"Failed to read {path}: {exc}") from exc

    if CLAUDE_MD_SENTINEL in current_text:
        click.echo("  • CLAUDE.md already includes Clodputer guidance.")
        return

    addition = CLAUDE_MD_SECTION.strip() + "\n"
    if current_text.strip():
        new_text = current_text.rstrip() + "\n\n" + addition
    else:
        new_text = addition
    if not new_text.endswith("\n"):
        new_text += "\n"

    diff = "".join(
        difflib.unified_diff(
            current_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )

    if not diff:
        click.echo("  • No changes required for CLAUDE.md.")
        return

    click.echo("  Proposed CLAUDE.md update:")
    diff_lines = diff.splitlines()
    preview_limit = 80
    for line in diff_lines[:preview_limit]:
        click.echo(f"    {line}")
    if len(diff_lines) > preview_limit:
        click.echo("    ... (diff truncated)")

    if not click.confirm("  Apply this update?", default=True):
        click.echo("  • Skipped CLAUDE.md update.")
        return

    backup_path = path.with_name(f"{path.name}.backup-{int(time.time())}")
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
        click.echo(f"  ✓ Updated CLAUDE.md (backup at {backup_path})")
    else:
        click.echo("  ✓ Updated CLAUDE.md")


def _verify_claude_cli(path: str) -> None:
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(f"Claude CLI not executable at {path}") from exc

    if result.returncode != 0:
        click.echo("  ⚠️ Unable to confirm Claude CLI version (non-zero exit code).")
    else:
        version_line = (result.stdout or result.stderr or "").strip().splitlines()[:1]
        if version_line:
            click.echo(f"  ✓ Detected Claude CLI: {version_line[0]}")
        else:
            click.echo("  ✓ Claude CLI responded to --version.")


__all__ = ["run_onboarding"]
