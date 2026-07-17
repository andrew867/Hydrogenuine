from __future__ import annotations

from pathlib import Path

from hg_realtime.reflection_worker import (
    REFLECTION_CYCLE_COMPLETED,
    REFLECTION_CYCLE_STARTED,
    ReflectionWorker,
)


def test_reflection_worker_tick_emits_start_and_completion(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "operator_console.server.app.services.reflection_cycle_service.run_reflection_cycles",
        lambda root, force=False: {
            "ok": True,
            "cycles": [{"cycle": "memory_consolidation", "artifact_id": "reflection:memory_consolidation:1", "title": "Memory consolidation cycle", "status": "completed"}],
            "errors": [],
            "state": {},
            "ts": "2026-03-24T00:00:00Z",
            "summary": {"ok": True, "cycles": []},
        },
    )

    worker = ReflectionWorker(workspace_root=workspace, bus=None)
    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(worker, "_emit", lambda *, kind, payload: events.append((kind, payload)))

    result = worker.tick_once(force=True)

    assert result["ok"] is True
    assert len(result["cycles"]) == 1
    assert [kind for kind, _ in events] == [REFLECTION_CYCLE_STARTED, REFLECTION_CYCLE_COMPLETED]
