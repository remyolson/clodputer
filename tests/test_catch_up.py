"""Tests for catch-up logic for missed scheduled tasks."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from clodputer.catch_up import (
    MissedTask,
    calculate_next_expected_run,
    detect_missed_tasks,
    should_catch_up,
)
from clodputer.config import ScheduleConfig, TaskConfig, TaskSpec
from clodputer.task_state import (
    TaskState,
    get_task_state,
    load_task_states,
    record_task_execution,
    save_task_states,
    update_task_state,
)


@pytest.fixture
def isolated_task_state(tmp_path, monkeypatch):
    """Isolate task state file to temp directory."""
    state_file = tmp_path / "task_state.json"
    # Only need to patch task_state module - catch_up uses its functions
    monkeypatch.setattr("clodputer.task_state.TASK_STATE_FILE", state_file)
    return state_file


def make_task(
    name: str,
    cron_expression: str,
    catch_up: str = "skip",
    enabled: bool = True,
) -> TaskConfig:
    """Helper to create a task config for testing."""
    return TaskConfig(
        name=name,
        enabled=enabled,
        schedule=ScheduleConfig(
            type="cron",
            expression=cron_expression,
            catch_up=catch_up,
        ),
        task=TaskSpec(prompt="test prompt"),
    )


class TestTaskState:
    """Tests for task state tracking."""

    def test_task_state_to_dict(self):
        """Test TaskState serialization."""
        state = TaskState(
            last_run="2025-10-09T08:00:00Z",
            last_success="2025-10-09T08:00:00Z",
            next_expected="2025-10-10T08:00:00Z",
        )
        assert state.to_dict() == {
            "last_run": "2025-10-09T08:00:00Z",
            "last_success": "2025-10-09T08:00:00Z",
            "next_expected": "2025-10-10T08:00:00Z",
        }

    def test_task_state_from_dict(self):
        """Test TaskState deserialization."""
        data = {
            "last_run": "2025-10-09T08:00:00Z",
            "last_success": "2025-10-09T08:00:00Z",
            "next_expected": "2025-10-10T08:00:00Z",
        }
        state = TaskState.from_dict(data)
        assert state.last_run == "2025-10-09T08:00:00Z"
        assert state.last_success == "2025-10-09T08:00:00Z"
        assert state.next_expected == "2025-10-10T08:00:00Z"

    def test_load_task_states_empty(self, isolated_task_state):
        """Test loading task states when file doesn't exist."""
        states = load_task_states()
        assert states == {}

    def test_save_and_load_task_states(self, isolated_task_state):
        """Test saving and loading task states."""
        states = {
            "task1": TaskState(last_run="2025-10-09T08:00:00Z"),
            "task2": TaskState(last_success="2025-10-09T09:00:00Z"),
        }
        save_task_states(states)

        loaded = load_task_states()
        assert "task1" in loaded
        assert "task2" in loaded
        assert loaded["task1"].last_run == "2025-10-09T08:00:00Z"
        assert loaded["task2"].last_success == "2025-10-09T09:00:00Z"

    def test_get_task_state(self, isolated_task_state):
        """Test getting state for a specific task."""
        states = {
            "task1": TaskState(last_run="2025-10-09T08:00:00Z"),
        }
        save_task_states(states)

        state = get_task_state("task1")
        assert state is not None
        assert state.last_run == "2025-10-09T08:00:00Z"

        state = get_task_state("nonexistent")
        assert state is None

    def test_update_task_state(self, isolated_task_state):
        """Test updating state for a specific task."""
        update_task_state("task1", last_run="2025-10-09T08:00:00Z")

        states = load_task_states()
        assert "task1" in states
        assert states["task1"].last_run == "2025-10-09T08:00:00Z"

        update_task_state("task1", last_success="2025-10-09T08:00:00Z")

        states = load_task_states()
        assert states["task1"].last_run == "2025-10-09T08:00:00Z"
        assert states["task1"].last_success == "2025-10-09T08:00:00Z"

    def test_record_task_execution_success(self, isolated_task_state):
        """Test recording a successful task execution."""
        record_task_execution("task1", success=True, next_expected="2025-10-10T08:00:00Z")

        state = get_task_state("task1")
        assert state is not None
        assert state.last_run is not None
        assert state.last_success is not None
        assert state.last_run == state.last_success
        assert state.next_expected == "2025-10-10T08:00:00Z"

    def test_record_task_execution_failure(self, isolated_task_state):
        """Test recording a failed task execution."""
        # Record initial success
        record_task_execution("task1", success=True)
        first_success = get_task_state("task1").last_success

        time.sleep(1.1)  # Ensure different timestamp (timestamps have 1-second granularity)

        # Record failure
        record_task_execution("task1", success=False)

        state = get_task_state("task1")
        assert state is not None
        assert state.last_run != state.last_success
        assert state.last_success == first_success  # Success timestamp unchanged


class TestCalculateNextExpectedRun:
    """Tests for calculating next expected run time."""

    def test_calculate_next_expected_run_cron(self):
        """Test calculating next run for cron schedule."""
        schedule = ScheduleConfig(
            type="cron",
            expression="0 9 * * *",  # Daily at 9 AM
        )

        # Freeze time to a known moment
        after = datetime(2025, 10, 9, 8, 0, 0, tzinfo=timezone.utc)
        next_run = calculate_next_expected_run(schedule, after=after)

        assert next_run is not None
        assert next_run == "2025-10-09T09:00:00Z"

    def test_calculate_next_expected_run_invalid_cron(self):
        """Test handling invalid cron expression."""
        schedule = ScheduleConfig(
            type="cron",
            expression="invalid cron",
        )

        next_run = calculate_next_expected_run(schedule)
        assert next_run is None


class TestShouldCatchUp:
    """Tests for determining if a task should use catch-up."""

    def test_should_catch_up_enabled_run_once(self):
        """Test catch-up check for enabled task with run_once."""
        task = make_task("test", "0 9 * * *", catch_up="run_once")
        assert should_catch_up(task) is True

    def test_should_catch_up_enabled_run_all(self):
        """Test catch-up check for enabled task with run_all."""
        task = make_task("test", "0 9 * * *", catch_up="run_all")
        assert should_catch_up(task) is True

    def test_should_catch_up_skip(self):
        """Test catch-up check for task with skip mode."""
        task = make_task("test", "0 9 * * *", catch_up="skip")
        assert should_catch_up(task) is False

    def test_should_catch_up_disabled(self):
        """Test catch-up check for disabled task."""
        task = make_task("test", "0 9 * * *", catch_up="run_once", enabled=False)
        assert should_catch_up(task) is False

    def test_should_catch_up_no_schedule(self):
        """Test catch-up check for task without schedule."""
        task = TaskConfig(
            name="test",
            enabled=True,
            task=TaskSpec(prompt="test"),
        )
        assert should_catch_up(task) is False


class TestDetectMissedTasks:
    """Tests for detecting missed scheduled tasks."""

    def test_detect_missed_tasks_no_tasks(self, isolated_task_state):
        """Test detection with no tasks."""
        missed = detect_missed_tasks([])
        assert missed == []

    def test_detect_missed_tasks_disabled_task(self, isolated_task_state):
        """Test that disabled tasks are skipped."""
        task = make_task("test", "0 9 * * *", catch_up="run_once", enabled=False)

        # Record a successful run yesterday
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        update_task_state(
            "test",
            last_success=yesterday.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        missed = detect_missed_tasks([task])
        assert missed == []

    def test_detect_missed_tasks_no_schedule(self, isolated_task_state):
        """Test that tasks without schedules are skipped."""
        task = TaskConfig(
            name="test",
            enabled=True,
            task=TaskSpec(prompt="test"),
        )

        missed = detect_missed_tasks([task])
        assert missed == []

    def test_detect_missed_tasks_catch_up_skip(self, isolated_task_state):
        """Test that tasks with catch_up=skip are skipped."""
        task = make_task("test", "0 9 * * *", catch_up="skip")

        # Record a successful run yesterday
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        update_task_state(
            "test",
            last_success=yesterday.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        missed = detect_missed_tasks([task])
        assert missed == []

    def test_detect_missed_tasks_no_previous_run(self, isolated_task_state):
        """Test that tasks with no previous runs are skipped."""
        task = make_task("test", "0 9 * * *", catch_up="run_once")

        missed = detect_missed_tasks([task])
        assert missed == []

    def test_detect_missed_tasks_run_once_single_miss(self, isolated_task_state):
        """Test detection with run_once mode and single missed run."""
        # Daily task at 9 AM
        task = make_task("test", "0 9 * * *", catch_up="run_once")

        # Last successful run was 2 days ago at 9 AM
        # This should detect 2 missed runs but only return the most recent one
        two_days_ago = datetime.now(timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        ) - timedelta(days=2)

        update_task_state(
            "test",
            last_success=two_days_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        missed = detect_missed_tasks([task])

        # run_once mode should only return the most recent miss
        assert len(missed) == 1
        assert missed[0].task_name == "test"
        assert missed[0].catch_up_mode == "run_once"

    def test_detect_missed_tasks_run_all_multiple_misses(self, isolated_task_state):
        """Test detection with run_all mode and multiple missed runs."""
        # Daily task at 9 AM
        task = make_task("test", "0 9 * * *", catch_up="run_all")

        # Last successful run was 3 days ago at 9 AM
        # This should detect 3 missed runs
        three_days_ago = datetime.now(timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        ) - timedelta(days=3)

        update_task_state(
            "test",
            last_success=three_days_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        missed = detect_missed_tasks([task])

        # run_all mode should return all missed runs
        assert len(missed) == 3
        assert all(m.task_name == "test" for m in missed)
        assert all(m.catch_up_mode == "run_all" for m in missed)

    def test_detect_missed_tasks_hourly_run_all(self, isolated_task_state):
        """Test detection with hourly schedule and run_all mode."""
        # Hourly task
        task = make_task("test", "0 * * * *", catch_up="run_all")

        # Last successful run was 5 hours ago
        five_hours_ago = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        ) - timedelta(hours=5)

        update_task_state(
            "test",
            last_success=five_hours_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        missed = detect_missed_tasks([task])

        # Should detect approximately 5 missed runs
        # (exact count depends on current time relative to hour boundary)
        assert len(missed) >= 4
        assert len(missed) <= 5
        assert all(m.task_name == "test" for m in missed)

    def test_detect_missed_tasks_multiple_tasks(self, isolated_task_state):
        """Test detection with multiple tasks."""
        # Task 1: Daily, run_once, missed 1
        task1 = make_task("task1", "0 9 * * *", catch_up="run_once")
        yesterday = datetime.now(timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        update_task_state("task1", last_success=yesterday.strftime("%Y-%m-%dT%H:%M:%SZ"))

        # Task 2: Daily, run_all, missed 2
        task2 = make_task("task2", "0 10 * * *", catch_up="run_all")
        two_days_ago = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        ) - timedelta(days=2)
        update_task_state("task2", last_success=two_days_ago.strftime("%Y-%m-%dT%H:%M:%SZ"))

        # Task 3: Daily, skip
        task3 = make_task("task3", "0 11 * * *", catch_up="skip")
        update_task_state("task3", last_success=yesterday.strftime("%Y-%m-%dT%H:%M:%SZ"))

        missed = detect_missed_tasks([task1, task2, task3])

        # Should detect 1 from task1 and 2 from task2, none from task3
        assert len(missed) == 3
        task1_misses = [m for m in missed if m.task_name == "task1"]
        task2_misses = [m for m in missed if m.task_name == "task2"]
        task3_misses = [m for m in missed if m.task_name == "task3"]

        assert len(task1_misses) == 1
        assert len(task2_misses) == 2
        assert len(task3_misses) == 0

    def test_detect_missed_tasks_no_misses(self, isolated_task_state):
        """Test detection when no tasks have missed runs."""
        # Task that ran recently
        task = make_task("test", "0 9 * * *", catch_up="run_once")

        # Last run was 5 minutes ago
        recent = datetime.now(timezone.utc) - timedelta(minutes=5)
        update_task_state("test", last_success=recent.strftime("%Y-%m-%dT%H:%M:%SZ"))

        missed = detect_missed_tasks([task])
        assert missed == []

    def test_detect_missed_tasks_invalid_timestamp(self, isolated_task_state):
        """Test handling of invalid timestamps in task state."""
        task = make_task("test", "0 9 * * *", catch_up="run_once")

        # Set invalid timestamp
        update_task_state("test", last_success="invalid-timestamp")

        missed = detect_missed_tasks([task])
        assert missed == []


class TestMissedTask:
    """Tests for MissedTask class."""

    def test_missed_task_creation(self):
        """Test creating a MissedTask instance."""
        missed = MissedTask(
            task_name="test",
            missed_at="2025-10-09T09:00:00Z",
            catch_up_mode="run_once",
        )

        assert missed.task_name == "test"
        assert missed.missed_at == "2025-10-09T09:00:00Z"
        assert missed.catch_up_mode == "run_once"
