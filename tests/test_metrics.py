from __future__ import annotations

from pathlib import Path

from clodputer import metrics as metrics_module


def test_metrics_record_success_failure(tmp_path: Path, monkeypatch) -> None:
    metrics_file = tmp_path / "metrics.json"
    monkeypatch.setattr(metrics_module, "METRICS_FILE", metrics_file)

    metrics_module.record_success("alpha", duration=1.5)
    metrics_module.record_failure("alpha")
    metrics_module.record_success("alpha", duration=2.5)
    metrics_module.record_success("beta", duration=3.0)

    summary = metrics_module.metrics_summary()
    assert summary["alpha"]["success"] == 2
    assert summary["alpha"]["failure"] == 1
    assert abs(summary["alpha"]["avg_duration"] - 2.0) < 1e-6
    assert summary["beta"]["total"] == 1
