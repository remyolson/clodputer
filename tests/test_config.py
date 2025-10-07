from __future__ import annotations

import os
from pathlib import Path

import pytest

from clodputer.config import ConfigError, TaskConfig, load_task_config


def _write_config(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_load_task_config_with_env_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PLACEHOLDER", "world")
    config_path = tmp_path / "sample.yaml"
    _write_config(
        config_path,
        """
name: sample
enabled: true
task:
  prompt: "Hello {{ env.PLACEHOLDER }}"
  allowed_tools: ["Read"]
        """,
    )
    config = load_task_config(config_path)
    assert isinstance(config, TaskConfig)
    assert config.task.prompt == "Hello world"


def test_missing_env_variable_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "missing.yaml"
    _write_config(
        config_path,
        """
name: missing
task:
  prompt: "Hello {{ env.UNKNOWN }}"
  allowed_tools: []
        """,
    )
    with pytest.raises(ConfigError):
        load_task_config(config_path)


def test_disallow_overlap(tmp_path: Path) -> None:
    config_path = tmp_path / "overlap.yaml"
    _write_config(
        config_path,
        """
name: overlap
task:
  prompt: "Hi"
  allowed_tools: ["Read"]
  disallowed_tools: ["Read"]
        """,
    )
    with pytest.raises(ConfigError):
        load_task_config(config_path)
