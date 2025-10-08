from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from clodputer import cli as cli_module
from clodputer import config as config_module
from clodputer import logger as logger_module
from clodputer import metrics as metrics_module


def _write_events(log_file: Path) -> None:
    events = [
        {
            "event": "task_completed",
            "timestamp": "2025-10-07T00:00:00Z",
            "task_name": "alpha",
            "result": {"duration": 1.2, "return_code": 0},
        },
        {
            "event": "task_failed",
            "timestamp": "2025-10-07T00:01:00Z",
            "task_name": "beta",
            "error": {"error": "boom", "return_code": 1, "parse_error": "invalid"},
        },
    ]
    log_file.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")


def _configure_paths(tmp_path: Path, monkeypatch) -> Path:
    log_dir = tmp_path / ".clodputer"
    archive_dir = log_dir / "archive"
    log_file = log_dir / "execution.log"
    archive_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(logger_module, "LOG_DIR", log_dir)
    monkeypatch.setattr(logger_module, "LOG_FILE", log_file)
    monkeypatch.setattr(logger_module, "ARCHIVE_DIR", archive_dir)
    monkeypatch.setattr(cli_module, "LOG_FILE", log_file)
    return log_file


def _configure_tasks_env(tmp_path: Path, monkeypatch) -> Path:
    home = tmp_path / "home"
    tasks_dir = home / ".clodputer" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(config_module, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(
        cli_module,
        "validate_all_tasks",
        lambda: config_module.validate_all_tasks(tasks_dir=tasks_dir),
    )
    metrics_path = home / ".clodputer" / "metrics.json"
    monkeypatch.setattr(metrics_module, "METRICS_FILE", metrics_path)
    return tasks_dir


def test_cli_logs_json(monkeypatch, tmp_path: Path) -> None:
    log_file = _configure_paths(tmp_path, monkeypatch)
    _write_events(log_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.cli, ["logs", "--json"])
    assert result.exit_code == 0
    assert '"task_name": "alpha"' in result.output


def test_cli_logs_text(monkeypatch, tmp_path: Path) -> None:
    log_file = _configure_paths(tmp_path, monkeypatch)
    _write_events(log_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.cli, ["logs"])
    assert result.exit_code == 0
    assert "code=0" in result.output
    assert "parse_error=invalid" in result.output


def test_cli_schedule_preview_cron(monkeypatch, tmp_path: Path) -> None:
    tasks_dir = _configure_tasks_env(tmp_path, monkeypatch)
    task_file = tasks_dir / "cron-task.yaml"
    task_file.write_text(
        """
name: cron-task
enabled: true
schedule:
  type: cron
  expression: "0 9 * * *"
task:
  prompt: ok
  allowed_tools: ["Read"]
        """,
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli_module.cli, ["schedule-preview", "cron-task", "--count", "1"])
    assert result.exit_code == 0
    assert "Upcoming runs for cron-task" in result.output


def test_cli_schedule_preview_interval(monkeypatch, tmp_path: Path) -> None:
    tasks_dir = _configure_tasks_env(tmp_path, monkeypatch)
    task_file = tasks_dir / "interval-task.yaml"
    task_file.write_text(
        """
name: interval-task
enabled: true
trigger:
  type: interval
  seconds: 600
task:
  prompt: ok
  allowed_tools: ["Read"]
        """,
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli_module.cli, ["schedule-preview", "interval-task", "--count", "1"])
    assert result.exit_code == 0
    assert "Upcoming runs for interval-task" in result.output
