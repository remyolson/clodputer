# Testing Guide

Clodputer ships with a growing suite of unit tests that validate configuration parsing, queue behaviour, cron integration, watcher helpers, and CLI utilities.

## Running Tests

Activate the virtual environment and run:

```bash
pytest
```

To run a subset:

```bash
pytest tests/test_queue.py
```

## Linting & Formatting

Use Ruff and Black to enforce style:

```bash
ruff check src tests
black src tests
```

The CI workflow runs `ruff`, `black --check`, and `pytest` on every push.

## Writing Tests

- Place new tests under `tests/` using `pytest` conventions (`test_*.py`).
- Prefer small, focused unit tests; integration scenarios can use temporary directories and monkeypatches (see `tests/test_cron.py` and `tests/test_watcher.py`).
- Use fixtures like `tmp_path` and `monkeypatch` for filesystem/process isolation.

## Manual Smoke Tests

End-to-end scenarios worth exercising manually:

1. **Manual run**: `clodputer run <task>`.
2. **Cron**: `clodputer install`, wait for the scheduled job, inspect `cron.log`.
3. **Watcher**: `clodputer watch --daemon`, create a matching file, confirm queue entry.
4. **Menu bar**: `clodputer menu`, inspect icon/menus.
5. **Doctor**: `clodputer doctor`, verify all checks pass.

Record manual test results in `docs/implementation/PROGRESS.md` during development.

## Coverage

While coverage enforcement is not yet part of CI, aim for broad test coverage of:

- Config validation edge cases.
- Queue persistence and recovery.
- Executor success/failure paths.
- Cron section generation/install stubs.
- Watcher event handling.

Add tests whenever you fix a bug or introduce a new feature.
