# Copyright (c) 2025 Rémy Olson
"""Tests for task validation (dry-run)."""

from __future__ import annotations

from pathlib import Path

import pytest

from clodputer.config import create_task_from_json
from clodputer.validation import validate_task


@pytest.fixture
def temp_tasks_dir(tmp_path):
    """Create temporary tasks directory."""
    return tmp_path / "tasks"


def test_validate_valid_task(temp_tasks_dir):
    """Test validation of a valid task."""
    # Create a valid task
    task_data = {
        "name": "test-task",
        "enabled": True,
        "schedule": {
            "type": "cron",
            "expression": "0 9 * * *",
        },
        "task": {
            "prompt": "This is a test task with a reasonable prompt",
            "allowed_tools": ["Read", "Write"],
            "timeout": 300,
        }
    }

    create_task_from_json(task_data, temp_tasks_dir)

    # Validate task (skip MCP check for testing)
    result = validate_task("test-task", temp_tasks_dir, check_mcp=False)

    assert result.is_valid
    assert len(result.get_errors()) == 0


def test_validate_invalid_cron(temp_tasks_dir):
    """Test validation detects invalid cron expression."""
    task_data = {
        "name": "bad-cron",
        "schedule": {
            "type": "cron",
            "expression": "invalid cron",
        },
        "task": {
            "prompt": "Test task",
            "allowed_tools": ["Read"],
        }
    }

    create_task_from_json(task_data, temp_tasks_dir)

    result = validate_task("bad-cron", temp_tasks_dir, check_mcp=False)

    assert not result.is_valid
    errors = result.get_errors()
    assert len(errors) > 0
    assert "cron" in str(errors[0]).lower()


def test_validate_warnings(temp_tasks_dir):
    """Test validation warnings for potential issues."""
    task_data = {
        "name": "warning-task",
        "enabled": True,
        "schedule": {
            "type": "cron",
            "expression": "* * * * *",  # Every minute - should warn
        },
        "task": {
            "prompt": "Short",  # Too short - should warn
            "timeout": 7200,  # 2 hours - should warn
            "max_retries": 10,  # Many retries - should warn
        }
    }

    create_task_from_json(task_data, temp_tasks_dir)

    result = validate_task("warning-task", temp_tasks_dir, check_mcp=False)

    # Should be valid but have warnings
    assert result.is_valid
    assert result.has_warnings
    warnings = result.get_warnings()
    assert len(warnings) >= 3  # Schedule, prompt, timeout/retries


def test_validate_no_schedule(temp_tasks_dir):
    """Test validation of manual task with no schedule."""
    task_data = {
        "name": "manual-task",
        "task": {
            "prompt": "Manual task with reasonable prompt",
            "allowed_tools": ["Read"],
        }
    }

    create_task_from_json(task_data, temp_tasks_dir)

    result = validate_task("manual-task", temp_tasks_dir, check_mcp=False)

    assert result.is_valid
    # Should have info about no schedule
    infos = result.get_infos()
    assert any("schedule" in str(i).lower() for i in infos)


def test_validate_no_tools(temp_tasks_dir):
    """Test validation warns about no tools specified."""
    task_data = {
        "name": "no-tools",
        "task": {
            "prompt": "Task with no tools specified",
            "allowed_tools": [],
        }
    }

    create_task_from_json(task_data, temp_tasks_dir)

    result = validate_task("no-tools", temp_tasks_dir, check_mcp=False)

    assert result.is_valid
    warnings = result.get_warnings()
    assert any("tools" in str(w).lower() for w in warnings)
