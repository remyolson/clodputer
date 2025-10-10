"""Tests for task execution reports."""

from __future__ import annotations

import json

import pytest

from clodputer.cleanup import CleanupReport
from clodputer.executor import ExecutionResult
from clodputer.reports import (
    compare_reports,
    generate_markdown_report,
    list_reports,
    load_latest_report,
    save_execution_report,
)


@pytest.fixture
def temp_outputs_dir(tmp_path):
    """Create temporary outputs directory."""
    return tmp_path / "outputs"


@pytest.fixture
def sample_success_result():
    """Create a sample successful execution result."""
    return ExecutionResult(
        task_id="test-123",
        task_name="test-task",
        status="success",
        return_code=0,
        duration=1.5,
        stdout='{"test": "output"}',
        stderr="",
        cleanup=CleanupReport(terminated=[], killed=[], orphaned_mcps=[]),
        output_json={"test": "output"},
        output_parse_error=None,
        error=None,
    )


@pytest.fixture
def sample_failure_result():
    """Create a sample failed execution result."""
    return ExecutionResult(
        task_id="test-456",
        task_name="test-task",
        status="failure",
        return_code=1,
        duration=0.5,
        stdout="",
        stderr="Error: something went wrong",
        cleanup=CleanupReport(terminated=[], killed=[], orphaned_mcps=[]),
        output_json=None,
        output_parse_error="Invalid JSON",
        error="Task failed with code 1",
    )


class TestSaveExecutionReport:
    """Tests for save_execution_report function."""

    def test_save_success_report(self, sample_success_result, temp_outputs_dir):
        """Test saving a successful execution report."""
        json_path, md_path = save_execution_report(sample_success_result, temp_outputs_dir)

        # Verify files were created
        assert json_path.exists()
        assert md_path.exists()
        assert json_path.parent == temp_outputs_dir / "test-task"
        assert md_path.parent == temp_outputs_dir / "test-task"

        # Verify JSON content
        json_content = json.loads(json_path.read_text())
        assert json_content["task_id"] == "test-123"
        assert json_content["task_name"] == "test-task"
        assert json_content["status"] == "success"
        assert json_content["duration"] == 1.5

        # Verify markdown content
        md_content = md_path.read_text()
        assert "# ✅ Task Execution Report" in md_content
        assert "test-task" in md_content
        assert "SUCCESS" in md_content

    def test_save_failure_report(self, sample_failure_result, temp_outputs_dir):
        """Test saving a failed execution report."""
        json_path, md_path = save_execution_report(sample_failure_result, temp_outputs_dir)

        # Verify files were created
        assert json_path.exists()
        assert md_path.exists()

        # Verify JSON content
        json_content = json.loads(json_path.read_text())
        assert json_content["status"] == "failure"
        assert json_content["error"] == "Task failed with code 1"
        assert json_content["output_parse_error"] == "Invalid JSON"

        # Verify markdown content
        md_content = md_path.read_text()
        assert "# ❌ Task Execution Report" in md_content
        assert "FAILURE" in md_content
        assert "Task failed with code 1" in md_content

    def test_save_report_creates_directory(self, sample_success_result, temp_outputs_dir):
        """Test that save_execution_report creates output directory if needed."""
        # Directory doesn't exist initially
        assert not (temp_outputs_dir / "test-task").exists()

        save_execution_report(sample_success_result, temp_outputs_dir)

        # Directory should be created
        assert (temp_outputs_dir / "test-task").exists()

    def test_save_report_filename_format(self, sample_success_result, temp_outputs_dir):
        """Test that report filenames follow YYYY-MM-DD_HH-MM-SS format."""
        json_path, md_path = save_execution_report(sample_success_result, temp_outputs_dir)

        # Check filename format (YYYY-MM-DD_HH-MM-SS.json)
        import re
        pattern = r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.(json|md)"
        assert re.match(pattern, json_path.name)
        assert re.match(pattern, md_path.name)
        assert json_path.stem == md_path.stem  # Same timestamp

    def test_save_report_with_cleanup_details(self, temp_outputs_dir):
        """Test saving report with cleanup details."""
        # Create a cleanup object with __dict__ attribute (non-dataclass)
        class MockCleanup:
            def __init__(self):
                self.terminated_processes = [{"pid": 123, "status": "terminated"}]
                self.zombie_count = 1

        result = ExecutionResult(
            task_id="test-cleanup",
            task_name="test-task",
            status="success",
            return_code=0,
            duration=1.0,
            stdout="",
            stderr="",
            cleanup=MockCleanup(),
            output_json=None,
            error=None,
        )

        json_path, md_path = save_execution_report(result, temp_outputs_dir)

        # Verify JSON has cleanup converted to dict
        json_content = json.loads(json_path.read_text())
        assert "cleanup" in json_content
        assert isinstance(json_content["cleanup"], dict)

        # Verify markdown includes cleanup info
        md_content = md_path.read_text()
        assert "Cleanup Report" in md_content or "cleanup" in md_content.lower()


class TestGenerateMarkdownReport:
    """Tests for generate_markdown_report function."""

    def test_markdown_success_report(self, sample_success_result):
        """Test generating markdown for successful execution."""
        md = generate_markdown_report(sample_success_result, "2025-10-09_10-00-00")

        assert "# ✅ Task Execution Report" in md
        assert "**Status:** SUCCESS" in md
        assert "**Duration:** 1.50s" in md
        assert "## Output (Parsed JSON)" in md
        assert '"test": "output"' in md

    def test_markdown_failure_report(self, sample_failure_result):
        """Test generating markdown for failed execution."""
        md = generate_markdown_report(sample_failure_result, "2025-10-09_10-00-00")

        assert "# ❌ Task Execution Report" in md
        assert "**Status:** FAILURE" in md
        assert "## Standard Error" in md
        assert "Error: something went wrong" in md
        assert "## JSON Parse Error" in md

    def test_markdown_timeout_report(self):
        """Test generating markdown for timeout."""
        result = ExecutionResult(
            task_id="test-789",
            task_name="timeout-task",
            status="timeout",
            return_code=None,
            duration=30.0,
            stdout="",
            stderr="",
            cleanup=CleanupReport(terminated=[], killed=[], orphaned_mcps=[]),
            output_json=None,
            error="timeout",
        )

        md = generate_markdown_report(result, "2025-10-09_10-00-00")

        assert "# ⏱️ Task Execution Report" in md
        assert "**Status:** TIMEOUT" in md

    def test_markdown_report_with_cleanup(self):
        """Test generating markdown with cleanup details."""
        # Create cleanup with terminated processes
        class MockCleanup:
            def __init__(self):
                self.terminated_processes = [
                    {"pid": 123, "status": "terminated"},
                    {"pid": 456, "status": "killed"}
                ]
                self.zombie_count = 2

        result = ExecutionResult(
            task_id="test-cleanup",
            task_name="cleanup-task",
            status="success",
            return_code=0,
            duration=5.0,
            stdout="task output",
            stderr="",
            cleanup=MockCleanup(),
            output_json={"result": "done"},
            error=None,
        )

        md = generate_markdown_report(result, "2025-10-09_10-00-00")

        # Should include cleanup section
        assert "## Cleanup Report" in md
        assert "Terminated Processes" in md
        assert "123" in md
        assert "456" in md
        assert "Zombie Processes Found:" in md
        assert "2" in md


class TestLoadLatestReport:
    """Tests for load_latest_report function."""

    def test_load_latest_report_exists(self, sample_success_result, temp_outputs_dir):
        """Test loading the most recent report."""
        # Save two reports
        save_execution_report(sample_success_result, temp_outputs_dir)
        import time
        time.sleep(1.1)  # Ensure different timestamp
        save_execution_report(sample_success_result, temp_outputs_dir)

        # Load latest
        latest = load_latest_report("test-task", temp_outputs_dir)

        assert latest is not None
        assert latest["task_name"] == "test-task"
        assert latest["status"] == "success"

    def test_load_latest_report_not_found(self, temp_outputs_dir):
        """Test loading report when task has no reports."""
        result = load_latest_report("nonexistent", temp_outputs_dir)
        assert result is None

    def test_load_latest_report_no_directory(self, temp_outputs_dir):
        """Test loading report when outputs directory doesn't exist."""
        result = load_latest_report("test-task", temp_outputs_dir)
        assert result is None

    def test_load_latest_report_corrupted_json(self, temp_outputs_dir):
        """Test loading report with corrupted JSON."""
        task_dir = temp_outputs_dir / "test-task"
        task_dir.mkdir(parents=True)

        # Create a corrupted JSON file
        corrupted_file = task_dir / "2025-01-01_12-00-00.json"
        corrupted_file.write_text("{ invalid json", encoding="utf-8")

        # Should return None when JSON is corrupted
        result = load_latest_report("test-task", temp_outputs_dir)
        assert result is None


class TestListReports:
    """Tests for list_reports function."""

    def test_list_reports_multiple(self, sample_success_result, sample_failure_result, temp_outputs_dir):
        """Test listing multiple reports."""
        # Save success report
        save_execution_report(sample_success_result, temp_outputs_dir)

        # Save failure report for same task
        import time
        time.sleep(1.1)
        failure_result = sample_failure_result
        failure_result.task_name = "test-task"  # Same task
        save_execution_report(failure_result, temp_outputs_dir)

        # List reports
        reports = list_reports("test-task", temp_outputs_dir, limit=10)

        assert len(reports) == 2
        # Should be sorted newest first
        assert reports[0]["status"] == "failure"
        assert reports[1]["status"] == "success"

    def test_list_reports_with_limit(self, sample_success_result, temp_outputs_dir):
        """Test listing reports with limit."""
        # Save 3 reports
        for _ in range(3):
            save_execution_report(sample_success_result, temp_outputs_dir)
            import time
            time.sleep(1.1)

        # List with limit=2
        reports = list_reports("test-task", temp_outputs_dir, limit=2)

        assert len(reports) == 2

    def test_list_reports_empty(self, temp_outputs_dir):
        """Test listing reports when none exist."""
        reports = list_reports("test-task", temp_outputs_dir)
        assert reports == []

    def test_list_reports_includes_metadata(self, sample_success_result, temp_outputs_dir):
        """Test that listed reports include file metadata."""
        save_execution_report(sample_success_result, temp_outputs_dir)

        reports = list_reports("test-task", temp_outputs_dir)

        assert len(reports) == 1
        assert "report_file" in reports[0]
        assert "report_timestamp" in reports[0]
        assert reports[0]["report_file"].endswith(".json")


class TestCompareReports:
    """Tests for compare_reports function."""

    def test_compare_status_changed(self):
        """Test comparing reports with status change."""
        report1 = {"status": "failure", "duration": 1.0, "return_code": 1, "error": "failed"}
        report2 = {"status": "success", "duration": 1.5, "return_code": 0, "error": None}

        comparison = compare_reports(report1, report2)

        assert comparison["status_changed"] is True
        assert comparison["status_from"] == "success"
        assert comparison["status_to"] == "failure"

    def test_compare_duration_delta(self):
        """Test comparing reports with duration change."""
        report1 = {"status": "success", "duration": 2.5, "return_code": 0}
        report2 = {"status": "success", "duration": 1.0, "return_code": 0}

        comparison = compare_reports(report1, report2)

        assert comparison["duration_delta"] == 1.5  # 2.5 - 1.0

    def test_compare_error_changed(self):
        """Test comparing reports with error change."""
        report1 = {"status": "failure", "error": "new error", "return_code": 1}
        report2 = {"status": "failure", "error": "old error", "return_code": 1}

        comparison = compare_reports(report1, report2)

        assert comparison["error_changed"] is True
        assert comparison["error_from"] == "old error"
        assert comparison["error_to"] == "new error"

    def test_compare_output_changed(self):
        """Test comparing reports with output change."""
        report1 = {"status": "success", "output_json": {"result": "new"}}
        report2 = {"status": "success", "output_json": {"result": "old"}}

        comparison = compare_reports(report1, report2)

        assert comparison["output_changed"] is True

    def test_compare_no_changes(self):
        """Test comparing identical reports."""
        report1 = {"status": "success", "duration": 1.0, "return_code": 0, "output_json": {"a": 1}}
        report2 = {"status": "success", "duration": 1.0, "return_code": 0, "output_json": {"a": 1}}

        comparison = compare_reports(report1, report2)

        assert comparison["status_changed"] is False
        assert comparison["duration_delta"] == 0
        assert comparison["return_code_changed"] is False
        assert comparison["output_changed"] is False
