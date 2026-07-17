"""Wake report tests."""
from __future__ import annotations

from hg_runtime.overnight_field_run.schema import FieldRunMode, OvernightFieldRunVerdict
from hg_runtime.overnight_field_run.wake_report import WakeReport, build_wake_report


def test_wake_report_smoke_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.overnight_field_run.wake_report.field_run_dir", lambda fid, base=None: tmp_path / fid)
    report = build_wake_report(
        "wake-1",
        mode=FieldRunMode.INFRASTRUCTURE_SMOKE.value,
        started_at="2026-01-01T00:00:00+00:00",
        stopped_at="2026-01-01T00:01:00+00:00",
        elapsed_seconds=60.0,
        state_payload={"turn_count": 3, "task_selection_count": 3, "governed_work_count": 3},
        stop_reason="stop",
        task_types=["inspect_queue", "review_local_artifacts"],
        refusals=[],
        incidents=[],
        receipt_hashes=["abc"],
        continuity_verdict="GREEN_CONTINUITY_OK",
        postflight_verdict=OvernightFieldRunVerdict.GREEN_INFRASTRUCTURE_READY.value,
        base=tmp_path,
    )
    assert report.verdict == OvernightFieldRunVerdict.YELLOW_FIELD_RUN_SHORT_SMOKE_ONLY.value
    assert "inspect_queue" in report.top_selected_task_types
    assert report.operator_summary


def test_wake_report_hash():
    r = WakeReport(
        wake_report_id="w1",
        field_run_id="f1",
        started_at="t0",
        stopped_at="t1",
        elapsed_seconds=1.0,
        turn_count=1,
        task_selection_count=1,
        governed_work_count=1,
        internal_work_count=0,
        external_candidate_count=0,
        dry_dispatch_count=0,
        live_dispatch_count=0,
        refusal_count=0,
        idle_count=0,
        panic_count=0,
        stop_reason="stop",
        verdict="YELLOW",
    ).with_hash()
    assert r.hash
