from types import SimpleNamespace

from clodputer.cron import CronError


def _prepare_diagnostics(monkeypatch, tmp_path):
    import clodputer.config as config
    import clodputer.diagnostics as diag

    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(diag, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(diag, "ensure_tasks_dir", lambda: None)
    monkeypatch.setattr(
        diag,
        "lockfile_status",
        lambda: {"locked": False, "stale": False, "path": tmp_path / "lock"},
    )

    class DummyQueue:
        def __init__(self, *args, **kwargs):
            pass

        def validate_state(self):
            return True, []

    monkeypatch.setattr(diag, "QueueManager", DummyQueue)
    monkeypatch.setattr(diag, "validate_all_tasks", lambda: ([], []))
    monkeypatch.setattr(diag, "scheduled_tasks", lambda _: [])
    monkeypatch.setattr(diag, "file_watch_tasks", lambda _: [])
    monkeypatch.setattr(diag, "is_cron_daemon_running", lambda: True)
    monkeypatch.setattr(diag, "cron_section_present", lambda: True)
    monkeypatch.setattr(diag, "generate_cron_section", lambda entries: None)
    monkeypatch.setattr(diag, "preview_schedule", lambda entry, count=1: [])
    monkeypatch.setattr(diag, "watcher_is_running", lambda: True)

    watcher_log_dir = tmp_path / "watcher"
    watcher_log_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(diag, "WATCHER_LOG_FILE", watcher_log_dir / "watcher.log")
    monkeypatch.setattr(diag, "LOG_FILE", tmp_path / "log.json")


def test_gather_diagnostics_cli_path_missing(monkeypatch, tmp_path):
    import clodputer.diagnostics as diag

    _prepare_diagnostics(monkeypatch, tmp_path)
    monkeypatch.setattr(diag, "claude_cli_path", lambda *_: None)
    monkeypatch.setattr(diag, "onboarding_state", lambda: {})

    results = diag.gather_diagnostics()

    cli_check = next(result for result in results if result.name == "Claude CLI path configured")
    assert not cli_check.passed
    assert any("No stored Claude CLI path" in detail for detail in cli_check.details)

    onboarding_check = next(
        result for result in results if result.name == "Onboarding completion recorded"
    )
    assert not onboarding_check.passed
    assert any("not been completed" in detail for detail in onboarding_check.details)


def test_gather_diagnostics_onboarding_state(monkeypatch, tmp_path):
    import clodputer.diagnostics as diag

    _prepare_diagnostics(monkeypatch, tmp_path)
    cli_path = tmp_path / "bin" / "claude"
    cli_path.parent.mkdir(parents=True, exist_ok=True)
    cli_path.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(diag, "claude_cli_path", lambda *_: str(cli_path))
    monkeypatch.setattr(
        diag,
        "onboarding_state",
        lambda: {"onboarding_last_run": "2025-01-01T00:00:00Z", "onboarding_runs": 3},
    )

    results = diag.gather_diagnostics()

    cli_check = next(result for result in results if result.name == "Claude CLI path configured")
    assert cli_check.passed
    assert any(str(cli_path) in detail for detail in cli_check.details)

    onboarding_check = next(
        result for result in results if result.name == "Onboarding completion recorded"
    )
    assert onboarding_check.passed
    assert any("2025-01-01T00:00:00Z" in detail for detail in onboarding_check.details)


def test_gather_diagnostics_reports_cron_and_watcher_problems(monkeypatch, tmp_path):
    import clodputer.diagnostics as diag

    _prepare_diagnostics(monkeypatch, tmp_path)

    entry = SimpleNamespace(
        task=SimpleNamespace(name="cron-task"),
        expression="0 * * * *",
        timezone=None,
        note=None,
    )

    monkeypatch.setattr(diag, "scheduled_tasks", lambda _: [entry])
    monkeypatch.setattr(
        diag,
        "generate_cron_section",
        lambda *_: (_ for _ in ()).throw(CronError("bad cron")),
    )
    monkeypatch.setattr(
        diag,
        "preview_schedule",
        lambda *_, **__: (_ for _ in ()).throw(CronError("preview error")),
    )

    missing_path = tmp_path / "missing"
    trigger = SimpleNamespace(
        type="file_watch",
        path=str(missing_path),
        pattern="*",
        event="created",
        debounce=1000,
    )
    task = SimpleNamespace(name="watch-task", trigger=trigger)
    monkeypatch.setattr(diag, "file_watch_tasks", lambda _: [task])
    monkeypatch.setattr(diag, "watcher_is_running", lambda: False)

    log_parent = tmp_path / "nope"
    monkeypatch.setattr(diag, "WATCHER_LOG_FILE", log_parent / "watcher.log")

    cli_path = tmp_path / "bin" / "claude"
    cli_path.parent.mkdir(parents=True, exist_ok=True)
    cli_path.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(diag, "claude_cli_path", lambda *_: str(cli_path))
    monkeypatch.setattr(
        diag,
        "onboarding_state",
        lambda: {"onboarding_last_run": "2025-01-02T00:00:00Z", "onboarding_runs": 2},
    )

    results = diag.gather_diagnostics()

    cron_defs = next(r for r in results if r.name == "Cron job definitions valid")
    assert not cron_defs.passed
    assert any("bad cron" in detail for detail in cron_defs.details)

    cron_preview = next(r for r in results if r.name == "Cron schedule preview")
    assert not cron_preview.passed
    assert any("preview error" in detail for detail in cron_preview.details)

    watcher_running = next(r for r in results if r.name == "Watcher daemon running")
    assert not watcher_running.passed

    watch_paths = next(r for r in results if r.name == "Watch paths exist")
    assert not watch_paths.passed
    assert any("watch-task" in detail for detail in watch_paths.details)

    log_dir_check = next(r for r in results if r.name == "Watcher log directory available")
    assert not log_dir_check.passed
