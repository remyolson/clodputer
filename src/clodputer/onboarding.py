"""Interactive onboarding utilities."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
import click

from .config import TASKS_DIR, ensure_tasks_dir
from .environment import STATE_FILE, claude_cli_path, store_claude_cli_path
from .queue import QUEUE_DIR, ensure_queue_dir

LOG_DIR = QUEUE_DIR / "logs"
ARCHIVE_DIR = QUEUE_DIR / "archive"


def run_onboarding() -> None:
    """Execute the interactive onboarding sequence."""

    click.echo("\n=== Clodputer Onboarding ===")

    _ensure_directories()

    click.echo("\nClaude CLI configuration")
    selected_path = _choose_claude_cli()
    _verify_claude_cli(selected_path)
    store_claude_cli_path(selected_path)
    click.echo(f"  ✓ Stored Claude CLI path in {STATE_FILE}")

    click.echo("\nSetup complete! Next steps:")
    click.echo("  • Add tasks to ~/.clodputer/tasks/ (try `clodputer template list`).")
    click.echo("  • Run `clodputer run <task>` to execute a task once.")
    click.echo("  • Use `clodputer install` and `clodputer watch` when you're ready for automation.")
    click.echo("  • Re-run `clodputer init` anytime to update settings.")


def _ensure_directories() -> None:
    ensure_queue_dir()
    ensure_tasks_dir()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    click.echo(f"  ✓ Ensured base directory at {QUEUE_DIR}")
    click.echo(f"  ✓ Ensured tasks directory at {TASKS_DIR}")


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
