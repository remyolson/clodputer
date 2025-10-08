from __future__ import annotations

from importlib import metadata

try:  # pragma: no cover - resolved at runtime
    __version__ = metadata.version("clodputer")
except metadata.PackageNotFoundError:  # pragma: no cover - editable install
    __version__ = "0.0.0"

__all__ = ["__version__"]
