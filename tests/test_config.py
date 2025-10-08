from __future__ import annotations

from pathlib import Path

import pytest

from clodputer.config import (
    ConfigError,
    TaskConfig,
    load_all_tasks,
    load_task_config,
    list_task_names,
    validate_all_tasks,
)


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


def test_validation_error_message_is_readable(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid.yaml"
    _write_config(
        config_path,
        """
name: invalid
task:
  allowed_tools: ["Read"]
        """,
    )
    with pytest.raises(ConfigError) as exc_info:
        load_task_config(config_path)
    message = str(exc_info.value)
    assert "task.prompt" in message


def test_tool_validation(tmp_path: Path) -> None:
    config_path = tmp_path / "tools.yaml"
    _write_config(
        config_path,
        """
name: tools
task:
  prompt: ok
  allowed_tools: ["UnknownTool"]
        """,
    )
    with pytest.raises(ConfigError) as exc_info:
        load_task_config(config_path)
    assert "Unknown allowed_tools" in str(exc_info.value)


def test_validate_all_tasks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    valid = tmp_path / "valid.yaml"
    invalid = tmp_path / "invalid.yaml"
    _write_config(
        valid,
        """
name: valid
task:
  prompt: ok
  allowed_tools: ["Read", "mcp__gmail"]
        """,
    )
    _write_config(
        invalid,
        """
name: invalid
task:
  allowed_tools: ["Read"]
        """,
    )
    configs, errors = validate_all_tasks(tmp_path)
    assert len(configs) == 1
    assert configs[0].name == "valid"
    assert errors and "task.prompt" in errors[0][1]


def test_list_task_names(tmp_path: Path) -> None:
    _write_config(
        tmp_path / "one.yaml",
        """
name: one
task:
  prompt: ok
  allowed_tools: ["Read"]
        """,
    )
    _write_config(
        tmp_path / "two.yaml",
        """
name: two
task:
  prompt: ok
  allowed_tools: ["Read"]
        """,
    )
    names = list_task_names(tmp_path)
    assert names == ["one", "two"]


def test_load_all_tasks_reports_errors(tmp_path: Path) -> None:
    _write_config(
        tmp_path / "good.yaml",
        """
name: good
task:
  prompt: ok
  allowed_tools: ["Read"]
        """,
    )
    _write_config(
        tmp_path / "bad.yaml",
        """
name: bad
task:
  allowed_tools: ["Read"]
        """,
    )
    with pytest.raises(ConfigError) as exc:
        load_all_tasks(tmp_path)
    assert "bad" in str(exc.value)
