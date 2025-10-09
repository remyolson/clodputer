# Copyright (c) 2025 Rémy Olson
"""Tests for debug logging infrastructure."""

import json
from pathlib import Path

import pytest

from clodputer.debug import (
    debug_logger,
    disable_debug_logging,
    enable_debug_logging,
    is_debug_enabled,
)


@pytest.fixture
def isolated_debug_log(tmp_path, monkeypatch):
    """Provide an isolated debug log file for testing."""
    log_file = tmp_path / "debug.log"
    monkeypatch.setattr("clodputer.debug.DEBUG_LOG_FILE", log_file)
    monkeypatch.setattr("clodputer.debug.DEBUG_DIR", tmp_path)
    return log_file


def test_debug_enable_disable():
    """Test enabling and disabling debug mode."""
    # Initially disabled
    disable_debug_logging()
    assert not is_debug_enabled()

    # Enable it
    enable_debug_logging()
    assert is_debug_enabled()

    # Disable it
    disable_debug_logging()
    assert not is_debug_enabled()


def test_debug_logger_basic_logging(isolated_debug_log):
    """Test basic debug logging writes to file."""
    enable_debug_logging()

    try:
        debug_logger.info("test_event", key="value", number=42)

        # Read the log file
        assert isolated_debug_log.exists()
        content = isolated_debug_log.read_text()
        record = json.loads(content.strip())

        # Check structure
        assert record["level"] == "INFO"
        assert record["event"] == "test_event"
        assert record["data"]["key"] == "value"
        assert record["data"]["number"] == 42
        assert "timestamp" in record
        assert "module" in record
        assert "function" in record
    finally:
        disable_debug_logging()


def test_debug_logger_context_manager(isolated_debug_log):
    """Test context manager for operation tracking."""
    enable_debug_logging()

    try:
        with debug_logger.context("test_operation", param="test"):
            debug_logger.info("inside_context")

        # Read all log lines
        lines = isolated_debug_log.read_text().strip().split("\n")
        assert len(lines) >= 3  # started, inside, completed

        # Parse records
        records = [json.loads(line) for line in lines]

        # Check started event
        started = next(r for r in records if r["event"] == "test_operation_started")
        assert started["data"]["param"] == "test"

        # Check completed event
        completed = next(r for r in records if r["event"] == "test_operation_completed")
        assert "duration" in completed["data"]
    finally:
        disable_debug_logging()


def test_debug_logger_when_disabled(isolated_debug_log):
    """Test that logging doesn't write when debug is disabled."""
    disable_debug_logging()

    debug_logger.info("should_not_appear")

    # Log file should not exist or be empty
    if isolated_debug_log.exists():
        content = isolated_debug_log.read_text().strip()
        assert content == ""


def test_debug_logger_sanitization(isolated_debug_log):
    """Test that home paths are sanitized."""
    enable_debug_logging()

    try:
        home_path = str(Path.home() / "test" / "file.txt")
        debug_logger.info("test_sanitization", path=home_path)

        content = isolated_debug_log.read_text()
        record = json.loads(content.strip())

        # Check that home directory was replaced with tilde
        assert "~" in record["data"]["path"]
        assert str(Path.home()) not in record["data"]["path"]
    finally:
        disable_debug_logging()


def test_debug_logger_levels(isolated_debug_log):
    """Test different log levels."""
    enable_debug_logging()

    try:
        debug_logger.debug("debug_event")
        debug_logger.info("info_event")
        debug_logger.warning("warning_event")
        debug_logger.error("error_event")

        lines = isolated_debug_log.read_text().strip().split("\n")
        records = [json.loads(line) for line in lines]

        levels = [r["level"] for r in records]
        assert "DEBUG" in levels
        assert "INFO" in levels
        assert "WARNING" in levels
        assert "ERROR" in levels
    finally:
        disable_debug_logging()


def test_debug_logger_subprocess_logging(isolated_debug_log):
    """Test subprocess-specific logging."""
    enable_debug_logging()

    try:
        debug_logger.subprocess("process_started", command="test command", pid=12345)

        content = isolated_debug_log.read_text()
        record = json.loads(content.strip())

        assert record["event"] == "process_started"
        assert record["data"]["command"] == "test command"
        assert record["data"]["pid"] == 12345
    finally:
        disable_debug_logging()


def test_debug_logger_state_change_logging(isolated_debug_log):
    """Test state change logging."""
    enable_debug_logging()

    try:
        debug_logger.state_change("queue_enqueued", task_id="abc-123", priority="high")

        content = isolated_debug_log.read_text()
        record = json.loads(content.strip())

        assert record["event"] == "queue_enqueued"
        assert record["data"]["task_id"] == "abc-123"
        assert record["data"]["priority"] == "high"
    finally:
        disable_debug_logging()
