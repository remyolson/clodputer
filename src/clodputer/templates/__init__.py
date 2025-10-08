"""
Built-in task templates distributed with Clodputer.

Use `available()` to list template filenames and `export(name, destination)`
to copy a template to a target path.
"""

from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path
from typing import Iterable, List


def available() -> List[str]:
    """Return the names of all packaged template files."""
    template_dir = resources.files(__package__)
    return sorted(str(item.name) for item in template_dir.iterdir() if item.suffix == ".yaml")


def export(name: str, destination: Path | str) -> Path:
    """
    Copy a template to ``destination``.

    Args:
        name: Template filename (e.g. ``daily-email.yaml``).
        destination: Directory or file path where the template should be copied.

    Returns:
        The written file path.
    """
    template_path = resources.files(__package__).joinpath(name)
    if not template_path.is_file():
        raise FileNotFoundError(f"Template {name!r} not found. Available: {available()}")

    destination_path = Path(destination)
    if destination_path.is_dir():
        destination_path = destination_path / name
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with resources.as_file(template_path) as src:
        shutil.copyfile(src, destination_path)
    return destination_path


def export_all(destination: Path | str) -> Iterable[Path]:
    """
    Copy every template into ``destination``.

    Args:
        destination: Directory where templates will be created.

    Yields:
        The path to each written file.
    """
    target_dir = Path(destination)
    target_dir.mkdir(parents=True, exist_ok=True)
    for template in available():
        yield export(template, target_dir / template)
