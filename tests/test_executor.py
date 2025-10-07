from __future__ import annotations

import os
from pathlib import Path

from clodputer.config import TaskConfig, TaskSpec
from clodputer.executor import build_command, _extract_json


def make_task_config() -> TaskConfig:
    return TaskConfig.model_validate(
        {
            "name": "sample",
            "task": {
                "prompt": "Say hello",
                "allowed_tools": ["Read", "Write"],
                "permission_mode": "acceptEdits",
                "timeout": 60,
            },
        }
    )


def test_build_command_includes_flags(monkeypatch) -> None:
    monkeypatch.setenv("CLODPUTER_CLAUDE_BIN", "/usr/bin/claude")
    config = make_task_config()
    cmd = build_command(config)
    assert cmd[0] == "/usr/bin/claude"
    assert "--allowed-tools" in cmd
    assert "--permission-mode" in cmd


def test_extract_json_handles_code_block() -> None:
    stdout = """```json
{"ok": true}
```"""
    parsed, error = _extract_json(stdout)
    assert error is None
    assert parsed == {"ok": True}
