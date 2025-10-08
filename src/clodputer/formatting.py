"""Terminal formatting utilities using Rich for beautiful output."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def print_step_header(step: int, total: int, title: str) -> None:
    """Print a formatted step header with progress indicator.

    Args:
        step: Current step number (1-indexed)
        total: Total number of steps
        title: Title of the current step

    Example:
        >>> print_step_header(3, 7, "Template Installation")
        ╔════════════════════════════════════════════════════════════╗
        ║  Step 3/7: Template Installation                          ║
        ╚════════════════════════════════════════════════════════════╝
    """
    header_text = f"Step {step}/{total}: {title}"
    panel = Panel(
        Text(header_text, style="bold cyan"),
        box=box.DOUBLE,
        border_style="cyan",
        padding=(0, 1),
    )
    console.print()
    console.print(panel)


def print_success(message: str, prefix: str = "✓") -> None:
    """Print a success message in green.

    Args:
        message: The success message
        prefix: Symbol to prefix the message with

    Example:
        >>> print_success("Configuration saved")
          ✓ Configuration saved
    """
    click.echo(f"  {prefix} {message}")


def print_error(message: str, prefix: str = "✗") -> None:
    """Print an error message in red.

    Args:
        message: The error message
        prefix: Symbol to prefix the message with

    Example:
        >>> print_error("Failed to connect")
          ✗ Failed to connect
    """
    click.echo(f"  {prefix} {message}")


def print_warning(message: str, prefix: str = "⚠") -> None:
    """Print a warning message in yellow.

    Args:
        message: The warning message
        prefix: Symbol to prefix the message with

    Example:
        >>> print_warning("Network may be unavailable")
          ⚠ Network may be unavailable
    """
    click.echo(f"  {prefix} {message}")


def print_info(message: str, prefix: str = "ℹ") -> None:
    """Print an info message in blue.

    Args:
        message: The info message
        prefix: Symbol to prefix the message with

    Example:
        >>> print_info("Optional step - you can skip this")
          ℹ Optional step - you can skip this
    """
    click.echo(f"  {prefix} {message}")


def print_section_title(title: str) -> None:
    """Print a section title in bold cyan.

    Args:
        title: The section title

    Example:
        >>> print_section_title("Claude CLI Configuration")

        Claude CLI Configuration
    """
    click.echo()
    click.echo(title)


def print_completion_header() -> None:
    """Print a celebration header for setup completion."""
    panel = Panel(
        Text("Setup Complete! 🎉", style="bold green", justify="center"),
        box=box.DOUBLE,
        border_style="green",
        padding=(0, 2),
    )
    console.print()
    console.print(panel)


def print_dim(message: str) -> None:
    """Print a dimmed/muted message.

    Args:
        message: The message to print dimly

    Example:
        >>> print_dim("Optional configuration")
          Optional configuration
    """
    click.echo(f"  • {message}")
