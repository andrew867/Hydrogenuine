from __future__ import annotations

from pathlib import Path

from hg_core.metacognition import write_reflection_artifact as real_write_reflection_artifact
from operator_console.server.app.services.reflection_cycle_service import (
    DEFAULT_COOLDOWN_SECONDS,
    get_reflection_cycle_summary,
    run_reflection_cycles,
)


def test_reflection_cycles_run_and_cooldown(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True, exist_ok=True)

    first = run_reflection_cycles(workspace, force=True)
    assert first["ok"] is True
    assert {row["cycle"] for row in first["cycles"]} == {
        "memory_consolidation",
        "timeline_reconciliation",
        "identity_review",
    }
    assert not first["errors"]

    summary = get_reflection_cycle_summary(workspace)
    cycle_map = {row["cycle"]: row for row in summary["cycles"]}
    for cycle_name in ("memory_consolidation", "timeline_reconciliation", "identity_review"):
        assert cycle_map[cycle_name]["due"] is False
        assert cycle_map[cycle_name]["last_run_at"]
        assert cycle_map[cycle_name]["cooldown_seconds"] == DEFAULT_COOLDOWN_SECONDS[cycle_name]

    second = run_reflection_cycles(workspace)
    assert second["cycles"] == []
    assert second["errors"] == []


def test_reflection_counterfactual_cycle_is_feature_flagged(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HG_REFLECTION_COUNTERFACTUAL", "1")

    out = run_reflection_cycles(workspace, force=True)
    cycle_names = {row["cycle"] for row in out["cycles"]}
    assert "counterfactual_rehearsal" in cycle_names


def test_reflection_cycle_failure_telemetry_is_captured(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True, exist_ok=True)

    def failing_write_reflection_artifact(*args, **kwargs):
        title = str(kwargs.get("title") or "")
        if title == "Timeline reconciliation cycle":
            raise RuntimeError("timeline cycle failed")
        return real_write_reflection_artifact(*args, **kwargs)

    monkeypatch.setattr(
        "operator_console.server.app.services.reflection_cycle_service.write_reflection_artifact",
        failing_write_reflection_artifact,
    )

    out = run_reflection_cycles(workspace, force=True)
    assert any(err["cycle"] == "timeline_reconciliation" for err in out["errors"])
    assert out["state"]["timeline_reconciliation"]["last_status"] == "failed"
    assert any(row["cycle"] == "memory_consolidation" for row in out["cycles"])
