"""Interactive task manager for browsing and managing Clodputer tasks."""

from __future__ import annotations

import os
import subprocess

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import TASKS_DIR, TaskConfig, validate_all_tasks
from .executor import TaskExecutor, TaskExecutionError

console = Console()


def run_manager() -> None:
    """Launch the interactive task manager.

    Provides a terminal UI for browsing, viewing, editing, running, and deleting tasks.

    Example:
        >>> run_manager()  # Opens interactive task browser
    """
    manager = TaskManager()
    manager.run()


class TaskManager:
    """Interactive task manager with keyboard navigation."""

    def __init__(self) -> None:
        self.tasks: list[TaskConfig] = []
        self.selected_index: int = 0
        self.running = True
        self.executor = TaskExecutor()

    def run(self) -> None:
        """Main event loop for the task manager."""
        while self.running:
            self._refresh_tasks()
            self._render_ui()
            action = self._get_user_action()
            self._handle_action(action)

    def _refresh_tasks(self) -> None:
        """Reload tasks from disk."""
        configs, errors = validate_all_tasks()
        if errors:
            console.print("\n[yellow]⚠ Some task configs have validation errors:[/yellow]")
            for path, err in errors:
                console.print(f"  • {path}: {err}")
        self.tasks = configs

        # Keep selection in bounds
        if self.selected_index >= len(self.tasks):
            self.selected_index = max(0, len(self.tasks) - 1)

    def _render_ui(self) -> None:
        """Render the main task list UI."""
        console.clear()

        # Header
        header = Panel(
            Text("Clodputer Task Manager", style="bold cyan", justify="center"),
            subtitle=f"[dim]{TASKS_DIR}[/dim]",
            border_style="cyan",
        )
        console.print(header)

        if not self.tasks:
            console.print("\n[yellow]No tasks found in ~/.clodputer/tasks/[/yellow]")
            console.print("\n[dim]Press [n] to create a new task, or [q] to quit[/dim]")
            return

        # Task table
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("", width=2)  # Selection indicator
        table.add_column("Task", style="cyan")
        table.add_column("Type", style="magenta", width=12)
        table.add_column("Status", width=10)

        for idx, task in enumerate(self.tasks):
            # Selection indicator
            indicator = "→" if idx == self.selected_index else " "

            # Task name
            name = task.name

            # Task type
            if task.trigger:
                if task.trigger.type == "cron":
                    task_type = "Cron"
                elif task.trigger.type == "file_watch":
                    task_type = "Watch"
                elif task.trigger.type == "interval":
                    task_type = "Interval"
                else:
                    task_type = "Manual"
            else:
                task_type = "Manual"

            # Status
            if task.enabled:
                status = "[green]Enabled[/green]"
            else:
                status = "[dim]Disabled[/dim]"

            # Highlight selected row
            if idx == self.selected_index:
                table.add_row(
                    f"[bold yellow]{indicator}[/bold yellow]",
                    f"[bold]{name}[/bold]",
                    f"[bold]{task_type}[/bold]",
                    status,
                )
            else:
                table.add_row(indicator, name, task_type, status)

        console.print(table)

        # Actions footer
        actions_text = (
            "[bold]Actions:[/bold] "
            "[cyan]↑↓[/cyan]/[cyan]jk[/cyan] Navigate  "
            "[cyan]Enter[/cyan] View  "
            "[cyan]e[/cyan] Edit  "
            "[cyan]r[/cyan] Run  "
            "[cyan]d[/cyan] Delete  "
            "[cyan]q[/cyan] Quit"
        )
        console.print(f"\n{actions_text}")

    def _get_user_action(self) -> str:
        """Get a single keypress from the user."""
        # Use click.getchar() for single character input
        try:
            char = click.getchar()
            return char
        except (KeyboardInterrupt, EOFError):
            return "q"

    def _handle_action(self, action: str) -> None:
        """Handle user action."""
        # Navigation
        if action in ("\x1b[A", "k"):  # Up arrow or k
            self.selected_index = max(0, self.selected_index - 1)
        elif action in ("\x1b[B", "j"):  # Down arrow or j
            self.selected_index = min(len(self.tasks) - 1, self.selected_index + 1)

        # Actions
        elif action in ("\r", "\n"):  # Enter - view details
            self._view_task_details()
        elif action == "e":  # Edit
            self._edit_task()
        elif action == "r":  # Run
            self._run_task()
        elif action == "d":  # Delete
            self._delete_task()
        elif action == "q":  # Quit
            self.running = False

        # Ignore other keys

    def _view_task_details(self) -> None:
        """Show detailed view of the selected task."""
        if not self.tasks or self.selected_index >= len(self.tasks):
            return

        task = self.tasks[self.selected_index]

        console.clear()

        # Header
        header = Panel(
            Text(f"{task.name}.yaml", style="bold cyan", justify="center"),
            border_style="cyan",
        )
        console.print(header)

        # Task details
        details = Table.grid(padding=(0, 2))
        details.add_column(style="bold")
        details.add_column()

        details.add_row("Name:", task.name)
        details.add_row("File:", str(task.path))
        details.add_row("Enabled:", "✓ Yes" if task.enabled else "✗ No")

        if task.trigger:
            if task.trigger.type == "cron":
                details.add_row("Type:", "Scheduled (Cron)")
                details.add_row("Schedule:", task.trigger.expression or "N/A")
            elif task.trigger.type == "file_watch":
                details.add_row("Type:", "File Watch")
                details.add_row("Watch Path:", task.trigger.path or "N/A")
                details.add_row("Pattern:", task.trigger.pattern or "*")
            elif task.trigger.type == "interval":
                details.add_row("Type:", "Interval")
                details.add_row("Interval:", f"{task.trigger.seconds}s")
        else:
            details.add_row("Type:", "Manual")

        console.print(details)

        # Prompt preview
        if task.prompt:
            prompt_preview = task.prompt[:200] + "..." if len(task.prompt) > 200 else task.prompt
            prompt_panel = Panel(
                Text(prompt_preview, style="dim"),
                title="[bold]Prompt Preview[/bold]",
                border_style="blue",
            )
            console.print("\n", prompt_panel)

        # Footer
        console.print("\n[dim]Press [e] to edit, [r] to run, or [Esc] to go back[/dim]")

        # Wait for action
        action = click.getchar()
        if action == "e":
            self._edit_task()
        elif action == "r":
            self._run_task()
        # ESC or any other key returns to list

    def _edit_task(self) -> None:
        """Open the selected task in $EDITOR."""
        if not self.tasks or self.selected_index >= len(self.tasks):
            return

        task = self.tasks[self.selected_index]
        editor = os.environ.get("EDITOR", "nano")

        console.print(f"\n[cyan]Opening {task.name}.yaml in {editor}...[/cyan]")

        try:
            subprocess.run([editor, str(task.path)], check=True)
            console.print(f"[green]✓[/green] Saved changes to {task.name}.yaml")
        except subprocess.CalledProcessError as exc:
            console.print(f"[red]✗[/red] Editor exited with error: {exc}")
        except FileNotFoundError:
            console.print(f"[red]✗[/red] Editor '{editor}' not found. Set $EDITOR environment variable.")

        console.print("\n[dim]Press any key to continue...[/dim]")
        click.getchar()

    def _run_task(self) -> None:
        """Run the selected task immediately."""
        if not self.tasks or self.selected_index >= len(self.tasks):
            return

        task = self.tasks[self.selected_index]

        console.print(f"\n[cyan]⏳ Running task '{task.name}'...[/cyan]")

        try:
            result = self.executor.run_task_by_name(task.name)

            # Show result
            status_emoji = {"success": "✅", "failure": "❌", "timeout": "⏱️", "error": "⚠️"}.get(
                result.status, "ℹ️"
            )
            duration = f"{result.duration:.1f}s" if result.duration else "N/A"

            console.print(
                f"{status_emoji} Task finished with status [bold]{result.status}[/bold] "
                f"in {duration}"
            )

            if result.error:
                console.print(f"[red]Error:[/red] {result.error}")

        except TaskExecutionError as exc:
            console.print(f"[red]✗[/red] Task execution failed: {exc}")
        except Exception as exc:
            console.print(f"[red]✗[/red] Unexpected error: {exc}")

        console.print("\n[dim]Press any key to continue...[/dim]")
        click.getchar()

    def _delete_task(self) -> None:
        """Delete the selected task with confirmation."""
        if not self.tasks or self.selected_index >= len(self.tasks):
            return

        task = self.tasks[self.selected_index]

        console.print(f"\n[yellow]⚠[/yellow] Delete task '{task.name}'?")
        console.print(f"[dim]File: {task.path}[/dim]")

        if not click.confirm("\nAre you sure?", default=False):
            console.print("[dim]Cancelled deletion[/dim]")
            console.print("\n[dim]Press any key to continue...[/dim]")
            click.getchar()
            return

        try:
            task.path.unlink()
            console.print(f"[green]✓[/green] Deleted {task.name}.yaml")
        except OSError as exc:
            console.print(f"[red]✗[/red] Failed to delete: {exc}")

        console.print("\n[dim]Press any key to continue...[/dim]")
        click.getchar()


__all__ = ["run_manager", "TaskManager"]
