"""Phase 24 no fake overnight GREEN."""
from __future__ import annotations

from hg_runtime.overnight_field_run.exciton_snapshot import build_overnight_field_run_monitor_snapshot
from hg_runtime.overnight_field_run.schema import OvernightFieldRunVerdict
from hg_runtime.overnight_field_run.wake_report import build_wake_report
from hg_runtime.overnight_field_run.schema import FieldRunMode


def test_smoke_wake_report_not_overnight_complete(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.overnight_field_run.wake_report.field_run_dir", lambda fid, base=None: tmp_path / fid)
    report = build_wake_report(
        "fake-1",
        mode=FieldRunMode.INFRASTRUCTURE_SMOKE.value,
        started_at="2026-01-01T00:00:00+00:00",
        stopped_at="2026-01-01T00:00:01+00:00",
        elapsed_seconds=1.0,
        state_payload={"turn_count": 2},
        stop_reason="stop",
        task_types=[],
        refusals=[],
        incidents=[],
        receipt_hashes=[],
        continuity_verdict="GREEN_CONTINUITY_OK",
        postflight_verdict=OvernightFieldRunVerdict.GREEN_INFRASTRUCTURE_READY.value,
        base=tmp_path,
    )
    assert report.verdict != OvernightFieldRunVerdict.GREEN_FIELD_RUN_COMPLETE.value


def test_monitor_not_started_yellow():
    snap = build_overnight_field_run_monitor_snapshot("missing-id-xyz")
    assert snap["verdict"] == OvernightFieldRunVerdict.YELLOW_FIELD_RUN_NOT_STARTED.value
    assert snap["overnight_green_eligible"] is False
