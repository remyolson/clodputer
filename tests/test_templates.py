from pathlib import Path

from clodputer import templates


def test_available_lists_builtin_templates() -> None:
    names = templates.available()
    assert "daily-email.yaml" in names
    assert "calendar-sync.yaml" in names
    assert "todo-triage.yaml" in names


def test_export_writes_selected_template(tmp_path: Path) -> None:
    destination = templates.export("daily-email.yaml", tmp_path)
    assert destination.exists()
    contents = destination.read_text(encoding="utf-8")
    assert "daily-email" in contents


def test_export_all_creates_each_template(tmp_path: Path) -> None:
    written = list(templates.export_all(tmp_path))
    expected = set(templates.available())
    assert {Path(path).name for path in written} == expected
    for name in expected:
        assert (tmp_path / name).exists()
