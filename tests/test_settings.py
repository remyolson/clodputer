from __future__ import annotations

from pathlib import Path

from clodputer import settings as settings_module


def test_load_settings_defaults(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", config_path)
    monkeypatch.setattr(settings_module, "_CACHE", None)

    settings = settings_module.load_settings()
    assert settings.queue.max_parallel == 1
    assert settings.queue.cpu_percent == 85.0


def test_load_settings_custom(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
queue:
  max_parallel: 2
  cpu_percent: 70
  memory_percent: 75
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", config_path)
    monkeypatch.setattr(settings_module, "_CACHE", None)

    settings = settings_module.load_settings()
    assert settings.queue.max_parallel == 2
    assert settings.queue.cpu_percent == 70.0
    assert settings.queue.memory_percent == 75.0
