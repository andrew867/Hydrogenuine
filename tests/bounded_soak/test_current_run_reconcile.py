"""Current-run reconciliation — finalized run is not a live publish risk; active run still RED."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.bounded_soak.active_run import assess_active_run
from hg_runtime.bounded_soak.current_run_reconcile import current_run_state, reconcile_current_run


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _make_run(root: Path, run_id: str, *, publish: bool, finalized: bool, active: bool, observer: bool) -> Path:
    rd = root / ".hg-local" / "soak" / "runs" / run_id
    rd.mkdir(parents=True, exist_ok=True)
    _write(rd / "run_control.json", {"allow_live_social_publish": publish, "max_posts_total": 3})
    lines = [{"ts": "2026-06-16T06:00:00+00:00", "event": "SOAK_START", "detail": {"run_id": run_id}}]
    if not active:
        lines.append({"ts": "2026-06-16T11:54:39+00:00", "event": "SOAK_COMPLETE", "detail": {}})
    (rd / "command_log.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    if finalized:
        _write(rd / "final_summary.json", {"finalized_at": "2026-06-16T12:59:55+00:00"})
    if observer:
        (rd / "observer_log.jsonl").write_text(
            json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "verdict": "GREEN_OBSERVER"}) + "\n",
            encoding="utf-8",
        )
    return rd


def test_finalized_publish_run_is_not_live(tmp_path):
    rd = _make_run(tmp_path, "FINAL", publish=True, finalized=True, active=False, observer=False)
    a = assess_active_run(workspace=tmp_path, run_dir=rd)
    assert a["active"] is False
    assert a["finalized"] is True
    assert not a["verdict"].startswith("RED")


def test_active_publish_no_observer_is_red(tmp_path):
    rd = _make_run(tmp_path, "ACTIVE", publish=True, finalized=False, active=True, observer=False)
    a = assess_active_run(workspace=tmp_path, run_dir=rd)
    assert a["active"] is True
    assert a["verdict"] == "RED_ACTIVE_RUN_PUBLISH_ENABLED_WITHOUT_OBSERVER"


def test_stale_finalized_pointer_classified_and_cleared(tmp_path):
    rd = _make_run(tmp_path, "FINAL", publish=True, finalized=True, active=False, observer=False)
    ptr = tmp_path / ".hg-local" / "soak" / "current_run.txt"
    ptr.write_text(str(rd), encoding="utf-8")
    state = current_run_state(workspace=tmp_path)
    assert state["classification"] == "STALE_FINALIZED_POINTER"
    assert state["is_stale"] is True
    recon = reconcile_current_run(workspace=tmp_path, apply=True)
    assert recon["applied"] is True
    assert recon["pointer_after"] is None
    assert ptr.read_text(encoding="utf-8").strip() == ""


def test_no_pointer_is_not_stale(tmp_path):
    state = current_run_state(workspace=tmp_path)
    assert state["classification"] == "NO_POINTER"
    assert state["is_stale"] is False


def test_active_run_pointer_not_stale(tmp_path):
    rd = _make_run(tmp_path, "ACTIVE", publish=True, finalized=False, active=True, observer=True)
    (tmp_path / ".hg-local" / "soak" / "current_run.txt").write_text(str(rd), encoding="utf-8")
    state = current_run_state(workspace=tmp_path)
    assert state["classification"] == "ACTIVE"
    assert state["is_stale"] is False
