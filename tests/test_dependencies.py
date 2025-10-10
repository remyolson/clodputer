# Copyright (c) 2025 Rémy Olson
"""Tests for task dependency validation and resolution."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from clodputer.config import TaskConfig, create_task_from_json
from clodputer.dependencies import (
    DependencyError,
    check_dependency_satisfied,
    detect_dependency_cycles,
    get_dependency_order,
    validate_dependencies,
)


@pytest.fixture
def temp_tasks_dir(tmp_path):
    """Create temporary tasks directory."""
    return tmp_path / "tasks"


@pytest.fixture
def temp_outputs_dir(tmp_path):
    """Create temporary outputs directory."""
    return tmp_path / "outputs"


def create_sample_task(name: str, deps: list[dict] = None, tasks_dir: Path = None) -> TaskConfig:
    """Helper to create a sample task with dependencies."""
    task_data = {
        "name": name,
        "task": {
            "prompt": f"Sample task: {name}",
            "allowed_tools": ["Read"],
        }
    }
    if deps:
        task_data["depends_on"] = deps

    config, _ = create_task_from_json(task_data, tasks_dir)
    return config


def create_task_report(task_name: str, status: str, outputs_dir: Path, age_seconds: int = 0):
    """Helper to create a task execution report."""
    task_dir = outputs_dir / task_name
    task_dir.mkdir(parents=True, exist_ok=True

)

    # Calculate timestamp
    timestamp = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    timestamp_str = timestamp.isoformat()

    report = {
        "task_id": f"test-{task_name}",
        "task_name": task_name,
        "status": status,
        "timestamp": timestamp_str,
        "duration": 1.0,
        "return_code": 0 if status == "success" else 1,
    }

    # Save report with timestamp filename
    filename = timestamp.strftime("%Y-%m-%d_%H-%M-%S") + ".json"
    report_path = task_dir / filename
    report_path.write_text(json.dumps(report), encoding="utf-8")


class TestValidateDependencies:
    """Tests for validate_dependencies function."""

    def test_no_dependencies(self, temp_tasks_dir):
        """Test validation with no dependencies."""
        task = create_sample_task("task1", deps=None, tasks_dir=temp_tasks_dir)
        errors = validate_dependencies(task, temp_tasks_dir)
        assert errors == []

    def test_valid_dependency(self, temp_tasks_dir):
        """Test validation with valid dependency."""
        # Create dependency task first
        create_sample_task("dep-task", deps=None, tasks_dir=temp_tasks_dir)

        # Create task that depends on it
        task = create_sample_task("task1", deps=[{"task": "dep-task"}], tasks_dir=temp_tasks_dir)

        errors = validate_dependencies(task, temp_tasks_dir, all_tasks=[task])
        assert errors == []

    def test_missing_dependency(self, temp_tasks_dir):
        """Test validation detects missing dependency task."""
        task = create_sample_task("task1", deps=[{"task": "nonexistent"}], tasks_dir=temp_tasks_dir)

        errors = validate_dependencies(task, temp_tasks_dir)
        assert len(errors) == 1
        assert "nonexistent" in errors[0]
        assert "does not exist" in errors[0]

    def test_invalid_max_age(self, temp_tasks_dir):
        """Test validation detects invalid max_age."""
        create_sample_task("dep-task", deps=None, tasks_dir=temp_tasks_dir)

        task = create_sample_task(
            "task1",
            deps=[{"task": "dep-task", "max_age": -1}],
            tasks_dir=temp_tasks_dir
        )

        errors = validate_dependencies(task, temp_tasks_dir, all_tasks=[task])
        assert len(errors) == 1
        assert "max_age must be positive" in errors[0]

    def test_self_dependency(self, temp_tasks_dir):
        """Test validation detects self-dependency."""
        task = create_sample_task("task1", deps=[{"task": "task1"}], tasks_dir=temp_tasks_dir)

        errors = validate_dependencies(task, temp_tasks_dir, all_tasks=[task])
        # Self-dependency triggers both self-check and circular dependency check
        assert len(errors) == 2
        assert any("cannot depend on itself" in e for e in errors)
        assert any("Circular dependency" in e for e in errors)

    def test_circular_dependency(self, temp_tasks_dir):
        """Test validation detects circular dependencies."""
        # Create circular dependency: task1 -> task2 -> task3 -> task1
        task1 = create_sample_task("task1", deps=[{"task": "task2"}], tasks_dir=temp_tasks_dir)
        task2 = create_sample_task("task2", deps=[{"task": "task3"}], tasks_dir=temp_tasks_dir)
        task3 = create_sample_task("task3", deps=[{"task": "task1"}], tasks_dir=temp_tasks_dir)

        all_tasks = [task1, task2, task3]

        errors = validate_dependencies(task1, temp_tasks_dir, all_tasks=all_tasks)
        assert len(errors) == 1
        assert "Circular dependency" in errors[0]


class TestDetectDependencyCycles:
    """Tests for detect_dependency_cycles function."""

    def test_no_cycle(self, temp_tasks_dir):
        """Test detection with no cycles."""
        task1 = create_sample_task("task1", deps=[{"task": "task2"}], tasks_dir=temp_tasks_dir)
        task2 = create_sample_task("task2", deps=None, tasks_dir=temp_tasks_dir)

        cycle = detect_dependency_cycles(task1, [task1, task2])
        assert cycle == []

    def test_simple_cycle(self, temp_tasks_dir):
        """Test detection of simple cycle (A -> B -> A)."""
        task1 = create_sample_task("task1", deps=[{"task": "task2"}], tasks_dir=temp_tasks_dir)
        task2 = create_sample_task("task2", deps=[{"task": "task1"}], tasks_dir=temp_tasks_dir)

        cycle = detect_dependency_cycles(task1, [task1, task2])
        assert len(cycle) > 0
        assert "task1" in cycle
        assert "task2" in cycle

    def test_complex_cycle(self, temp_tasks_dir):
        """Test detection of complex cycle (A -> B -> C -> A)."""
        task1 = create_sample_task("task1", deps=[{"task": "task2"}], tasks_dir=temp_tasks_dir)
        task2 = create_sample_task("task2", deps=[{"task": "task3"}], tasks_dir=temp_tasks_dir)
        task3 = create_sample_task("task3", deps=[{"task": "task1"}], tasks_dir=temp_tasks_dir)

        cycle = detect_dependency_cycles(task1, [task1, task2, task3])
        assert len(cycle) > 0
        # Cycle should contain all three tasks
        assert all(task in cycle for task in ["task1", "task2", "task3"])


class TestGetDependencyOrder:
    """Tests for get_dependency_order function."""

    def test_single_task(self, temp_tasks_dir):
        """Test ordering with single task."""
        task = create_sample_task("task1", deps=None, tasks_dir=temp_tasks_dir)

        ordered = get_dependency_order([task])
        assert len(ordered) == 1
        assert ordered[0].name == "task1"

    def test_linear_dependencies(self, temp_tasks_dir):
        """Test ordering with linear dependencies (A -> B -> C)."""
        task3 = create_sample_task("task3", deps=None, tasks_dir=temp_tasks_dir)
        task2 = create_sample_task("task2", deps=[{"task": "task3"}], tasks_dir=temp_tasks_dir)
        task1 = create_sample_task("task1", deps=[{"task": "task2"}], tasks_dir=temp_tasks_dir)

        # Order should be: task3, task2, task1 (dependencies first)
        ordered = get_dependency_order([task1, task2, task3])
        assert [t.name for t in ordered] == ["task3", "task2", "task1"]

    def test_multiple_dependencies(self, temp_tasks_dir):
        """Test ordering with multiple dependencies."""
        task1 = create_sample_task("task1", deps=None, tasks_dir=temp_tasks_dir)
        task2 = create_sample_task("task2", deps=None, tasks_dir=temp_tasks_dir)
        task3 = create_sample_task("task3", deps=[{"task": "task1"}, {"task": "task2"}], tasks_dir=temp_tasks_dir)

        # task1 and task2 should come before task3
        ordered = get_dependency_order([task3, task1, task2])
        names = [t.name for t in ordered]
        assert names.index("task1") < names.index("task3")
        assert names.index("task2") < names.index("task3")

    def test_circular_dependency_error(self, temp_tasks_dir):
        """Test that circular dependencies raise error."""
        task1 = create_sample_task("task1", deps=[{"task": "task2"}], tasks_dir=temp_tasks_dir)
        task2 = create_sample_task("task2", deps=[{"task": "task1"}], tasks_dir=temp_tasks_dir)

        with pytest.raises(DependencyError, match="Circular dependency"):
            get_dependency_order([task1, task2])

    def test_missing_dependency_error(self, temp_tasks_dir):
        """Test that missing dependencies raise error."""
        task = create_sample_task("task1", deps=[{"task": "nonexistent"}], tasks_dir=temp_tasks_dir)

        with pytest.raises(DependencyError, match="non-existent"):
            get_dependency_order([task])


class TestCheckDependencySatisfied:
    """Tests for check_dependency_satisfied function."""

    def test_no_report(self, temp_outputs_dir):
        """Test check when dependency has never run."""
        satisfied, reason = check_dependency_satisfied(
            "nonexistent",
            "success",
            None,
            temp_outputs_dir
        )

        assert not satisfied
        assert "never run" in reason

    def test_success_condition_satisfied(self, temp_outputs_dir):
        """Test success condition when task succeeded."""
        create_task_report("dep-task", "success", temp_outputs_dir)

        satisfied, reason = check_dependency_satisfied(
            "dep-task",
            "success",
            None,
            temp_outputs_dir
        )

        assert satisfied
        assert reason is None

    def test_success_condition_not_satisfied(self, temp_outputs_dir):
        """Test success condition when task failed."""
        create_task_report("dep-task", "failure", temp_outputs_dir)

        satisfied, reason = check_dependency_satisfied(
            "dep-task",
            "success",
            None,
            temp_outputs_dir
        )

        assert not satisfied
        assert "did not succeed" in reason

    def test_complete_condition_success(self, temp_outputs_dir):
        """Test complete condition when task succeeded."""
        create_task_report("dep-task", "success", temp_outputs_dir)

        satisfied, reason = check_dependency_satisfied(
            "dep-task",
            "complete",
            None,
            temp_outputs_dir
        )

        assert satisfied
        assert reason is None

    def test_complete_condition_failure(self, temp_outputs_dir):
        """Test complete condition when task failed."""
        create_task_report("dep-task", "failure", temp_outputs_dir)

        satisfied, reason = check_dependency_satisfied(
            "dep-task",
            "complete",
            None,
            temp_outputs_dir
        )

        assert satisfied
        assert reason is None

    def test_always_condition(self, temp_outputs_dir):
        """Test always condition accepts any status."""
        create_task_report("dep-task", "failure", temp_outputs_dir)

        satisfied, reason = check_dependency_satisfied(
            "dep-task",
            "always",
            None,
            temp_outputs_dir
        )

        assert satisfied
        assert reason is None

    def test_max_age_within_limit(self, temp_outputs_dir):
        """Test max_age when report is recent enough."""
        # Report from 30 seconds ago, max_age is 60 seconds
        create_task_report("dep-task", "success", temp_outputs_dir, age_seconds=30)

        satisfied, reason = check_dependency_satisfied(
            "dep-task",
            "success",
            max_age=60,
            outputs_dir=temp_outputs_dir
        )

        assert satisfied
        assert reason is None

    def test_max_age_exceeded(self, temp_outputs_dir):
        """Test max_age when report is too old."""
        # Report from 120 seconds ago, max_age is 60 seconds
        create_task_report("dep-task", "success", temp_outputs_dir, age_seconds=120)

        satisfied, reason = check_dependency_satisfied(
            "dep-task",
            "success",
            max_age=60,
            outputs_dir=temp_outputs_dir
        )

        assert not satisfied
        assert "too old" in reason


class TestDependencyIntegration:
    """Integration tests for dependency features."""

    def test_full_workflow(self, temp_tasks_dir, temp_outputs_dir):
        """Test complete dependency workflow."""
        # Create tasks: task1 <- task2 <- task3
        task1 = create_sample_task("task1", deps=None, tasks_dir=temp_tasks_dir)
        task2 = create_sample_task("task2", deps=[{"task": "task1"}], tasks_dir=temp_tasks_dir)
        task3 = create_sample_task("task3", deps=[{"task": "task2", "condition": "success"}], tasks_dir=temp_tasks_dir)

        # Validate all tasks
        for task in [task1, task2, task3]:
            errors = validate_dependencies(task, temp_tasks_dir, all_tasks=[task1, task2, task3])
            assert errors == []

        # Get execution order
        ordered = get_dependency_order([task3, task2, task1])
        assert [t.name for t in ordered] == ["task1", "task2", "task3"]

        # Simulate task1 success
        create_task_report("task1", "success", temp_outputs_dir)

        # Check task2 can run (depends on task1 success)
        satisfied, reason = check_dependency_satisfied("task1", "success", None, temp_outputs_dir)
        assert satisfied

        # Simulate task2 success
        create_task_report("task2", "success", temp_outputs_dir)

        # Check task3 can run (depends on task2 success)
        satisfied, reason = check_dependency_satisfied("task2", "success", None, temp_outputs_dir)
        assert satisfied
