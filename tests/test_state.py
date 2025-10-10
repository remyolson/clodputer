"""Tests for task state persistence."""

from __future__ import annotations

import json

import pytest

from clodputer.state import (
    StateError,
    delete_state,
    ensure_state_dir,
    get_state_path,
    list_states,
    load_state,
    save_state,
    update_state,
)


@pytest.fixture
def temp_state_dir(tmp_path, monkeypatch):
    """Create temporary state directory and patch STATE_DIR."""
    state_dir = tmp_path / "state"
    monkeypatch.setattr("clodputer.state.STATE_DIR", state_dir)
    return state_dir


class TestEnsureStateDir:
    """Tests for ensure_state_dir function."""

    def test_ensure_state_dir_creates_directory(self, temp_state_dir):
        """Test that ensure_state_dir creates the directory."""
        assert not temp_state_dir.exists()

        ensure_state_dir(temp_state_dir)

        assert temp_state_dir.exists()
        assert temp_state_dir.is_dir()

    def test_ensure_state_dir_idempotent(self, temp_state_dir):
        """Test that ensure_state_dir is idempotent."""
        ensure_state_dir(temp_state_dir)
        ensure_state_dir(temp_state_dir)  # Should not raise

        assert temp_state_dir.exists()


class TestGetStatePath:
    """Tests for get_state_path function."""

    def test_get_state_path_format(self, temp_state_dir):
        """Test that get_state_path returns correct path."""
        path = get_state_path("test-task", temp_state_dir)

        assert path == temp_state_dir / "test-task.json"
        assert path.suffix == ".json"
        assert path.stem == "test-task"


class TestLoadState:
    """Tests for load_state function."""

    def test_load_state_empty_when_not_exists(self, temp_state_dir):
        """Test loading state when file doesn't exist."""
        state = load_state("test-task", temp_state_dir)

        assert state == {}

    def test_load_state_existing(self, temp_state_dir):
        """Test loading existing state."""
        # Create state file
        ensure_state_dir(temp_state_dir)
        state_path = get_state_path("test-task", temp_state_dir)
        state_data = {"key": "value", "count": 42}
        state_path.write_text(json.dumps(state_data), encoding="utf-8")

        # Load state
        state = load_state("test-task", temp_state_dir)

        assert state == state_data

    def test_load_state_corrupted_json(self, temp_state_dir):
        """Test loading state with corrupted JSON."""
        # Create corrupted state file
        ensure_state_dir(temp_state_dir)
        state_path = get_state_path("test-task", temp_state_dir)
        state_path.write_text("{ invalid json", encoding="utf-8")

        # Should raise StateError
        with pytest.raises(StateError, match="Corrupted state file"):
            load_state("test-task", temp_state_dir)

    def test_load_state_not_dict(self, temp_state_dir):
        """Test loading state when content is not a dict."""
        # Create state file with list instead of dict
        ensure_state_dir(temp_state_dir)
        state_path = get_state_path("test-task", temp_state_dir)
        state_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

        # Should raise StateError
        with pytest.raises(StateError, match="must be a JSON object"):
            load_state("test-task", temp_state_dir)

    def test_load_state_too_large(self, temp_state_dir):
        """Test loading state that exceeds size limit."""
        from clodputer.state import MAX_STATE_SIZE

        # Create state file larger than limit
        ensure_state_dir(temp_state_dir)
        state_path = get_state_path("test-task", temp_state_dir)
        large_data = {"data": "x" * (MAX_STATE_SIZE + 1)}
        state_path.write_text(json.dumps(large_data), encoding="utf-8")

        # Should raise StateError
        with pytest.raises(StateError, match="too large"):
            load_state("test-task", temp_state_dir)


class TestSaveState:
    """Tests for save_state function."""

    def test_save_state_creates_file(self, temp_state_dir):
        """Test that save_state creates state file."""
        state_data = {"key": "value", "count": 42}

        save_state("test-task", state_data, temp_state_dir)

        state_path = get_state_path("test-task", temp_state_dir)
        assert state_path.exists()

        # Verify content
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        assert loaded == state_data

    def test_save_state_overwrites_existing(self, temp_state_dir):
        """Test that save_state overwrites existing state."""
        # Save initial state
        save_state("test-task", {"old": "data"}, temp_state_dir)

        # Save new state
        new_state = {"new": "data"}
        save_state("test-task", new_state, temp_state_dir)

        # Verify new state
        loaded = load_state("test-task", temp_state_dir)
        assert loaded == new_state
        assert "old" not in loaded

    def test_save_state_not_dict(self, temp_state_dir):
        """Test that save_state rejects non-dict state."""
        with pytest.raises(StateError, match="State must be a dictionary"):
            save_state("test-task", ["not", "a", "dict"], temp_state_dir)

    def test_save_state_too_large(self, temp_state_dir):
        """Test that save_state rejects state exceeding size limit."""
        from clodputer.state import MAX_STATE_SIZE

        large_data = {"data": "x" * (MAX_STATE_SIZE + 1)}

        with pytest.raises(StateError, match="exceeds maximum size"):
            save_state("test-task", large_data, temp_state_dir)

    def test_save_state_atomic(self, temp_state_dir):
        """Test that save_state uses atomic writes."""
        state_data = {"key": "value"}

        save_state("test-task", state_data, temp_state_dir)

        # Temp file should not exist after successful save
        temp_files = list(temp_state_dir.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_save_state_creates_directory(self, temp_state_dir):
        """Test that save_state creates directory if needed."""
        assert not temp_state_dir.exists()

        save_state("test-task", {"key": "value"}, temp_state_dir)

        assert temp_state_dir.exists()


class TestUpdateState:
    """Tests for update_state function."""

    def test_update_state_new_task(self, temp_state_dir):
        """Test updating state for new task."""
        updates = {"key1": "value1", "key2": 42}

        result = update_state("test-task", updates, temp_state_dir)

        assert result == updates
        loaded = load_state("test-task", temp_state_dir)
        assert loaded == updates

    def test_update_state_existing_task(self, temp_state_dir):
        """Test updating state for existing task."""
        # Create initial state
        save_state("test-task", {"old_key": "old_value", "count": 1}, temp_state_dir)

        # Update state
        updates = {"new_key": "new_value", "count": 2}
        result = update_state("test-task", updates, temp_state_dir)

        # Should merge old and new
        assert result == {"old_key": "old_value", "new_key": "new_value", "count": 2}

        loaded = load_state("test-task", temp_state_dir)
        assert loaded == result

    def test_update_state_overwrites_keys(self, temp_state_dir):
        """Test that update_state overwrites existing keys."""
        save_state("test-task", {"key": "old_value"}, temp_state_dir)

        update_state("test-task", {"key": "new_value"}, temp_state_dir)

        loaded = load_state("test-task", temp_state_dir)
        assert loaded["key"] == "new_value"


class TestDeleteState:
    """Tests for delete_state function."""

    def test_delete_state_existing(self, temp_state_dir):
        """Test deleting existing state."""
        save_state("test-task", {"key": "value"}, temp_state_dir)

        result = delete_state("test-task", temp_state_dir)

        assert result is True
        state_path = get_state_path("test-task", temp_state_dir)
        assert not state_path.exists()

    def test_delete_state_not_exists(self, temp_state_dir):
        """Test deleting state that doesn't exist."""
        result = delete_state("test-task", temp_state_dir)

        assert result is False

    def test_delete_state_multiple_tasks(self, temp_state_dir):
        """Test deleting state doesn't affect other tasks."""
        save_state("task1", {"data": 1}, temp_state_dir)
        save_state("task2", {"data": 2}, temp_state_dir)

        delete_state("task1", temp_state_dir)

        # task1 should be deleted
        assert not get_state_path("task1", temp_state_dir).exists()

        # task2 should still exist
        task2_state = load_state("task2", temp_state_dir)
        assert task2_state == {"data": 2}


class TestListStates:
    """Tests for list_states function."""

    def test_list_states_empty(self, temp_state_dir):
        """Test listing states when none exist."""
        states = list_states(temp_state_dir)

        assert states == {}

    def test_list_states_multiple(self, temp_state_dir):
        """Test listing multiple states."""
        save_state("task1", {"data": 1}, temp_state_dir)
        save_state("task2", {"data": 2}, temp_state_dir)
        save_state("task3", {"data": 3}, temp_state_dir)

        states = list_states(temp_state_dir)

        assert len(states) == 3
        assert states["task1"] == {"data": 1}
        assert states["task2"] == {"data": 2}
        assert states["task3"] == {"data": 3}

    def test_list_states_skips_corrupted(self, temp_state_dir):
        """Test that list_states skips corrupted files."""
        save_state("task1", {"data": 1}, temp_state_dir)

        # Create corrupted state file
        ensure_state_dir(temp_state_dir)
        corrupted_path = get_state_path("task2", temp_state_dir)
        corrupted_path.write_text("{ invalid json", encoding="utf-8")

        save_state("task3", {"data": 3}, temp_state_dir)

        states = list_states(temp_state_dir)

        # Should have task1 and task3, skip corrupted task2
        assert len(states) == 2
        assert "task1" in states
        assert "task2" not in states  # Corrupted, skipped
        assert "task3" in states

    def test_list_states_creates_directory(self, temp_state_dir):
        """Test that list_states creates directory if needed."""
        assert not temp_state_dir.exists()

        states = list_states(temp_state_dir)

        assert temp_state_dir.exists()
        assert states == {}


class TestIntegration:
    """Integration tests for state module."""

    def test_full_lifecycle(self, temp_state_dir):
        """Test complete state lifecycle."""
        task_name = "lifecycle-task"

        # 1. Initial load (empty)
        state = load_state(task_name, temp_state_dir)
        assert state == {}

        # 2. Save state
        initial_state = {"count": 0, "status": "initialized"}
        save_state(task_name, initial_state, temp_state_dir)

        # 3. Load and verify
        state = load_state(task_name, temp_state_dir)
        assert state == initial_state

        # 4. Update state
        update_state(task_name, {"count": 1, "last_run": "2025-10-09"}, temp_state_dir)

        # 5. Verify update
        state = load_state(task_name, temp_state_dir)
        assert state["count"] == 1
        assert state["status"] == "initialized"  # Preserved
        assert state["last_run"] == "2025-10-09"  # Added

        # 6. List all states
        states = list_states(temp_state_dir)
        assert task_name in states

        # 7. Delete state
        result = delete_state(task_name, temp_state_dir)
        assert result is True

        # 8. Verify deletion
        state = load_state(task_name, temp_state_dir)
        assert state == {}

        states = list_states(temp_state_dir)
        assert task_name not in states

    def test_concurrent_task_states(self, temp_state_dir):
        """Test managing state for multiple tasks concurrently."""
        # Create states for 5 different tasks
        for i in range(5):
            task_name = f"task-{i}"
            save_state(task_name, {"id": i, "status": "running"}, temp_state_dir)

        # Update one task
        update_state("task-2", {"status": "completed"}, temp_state_dir)

        # Delete another task
        delete_state("task-4", temp_state_dir)

        # List all states
        states = list_states(temp_state_dir)

        # Should have 4 tasks (5 - 1 deleted)
        assert len(states) == 4
        assert "task-4" not in states

        # Verify updated task
        assert states["task-2"]["status"] == "completed"

        # Verify other tasks unchanged
        assert states["task-0"]["status"] == "running"
        assert states["task-1"]["status"] == "running"
        assert states["task-3"]["status"] == "running"
