"""Continuity audit tests."""
from __future__ import annotations

from hg_runtime.overnight_field_run.continuity_audit import run_continuity_audit
from hg_runtime.overnight_field_run.schema import OvernightFieldRunVerdict


def test_continuity_detects_missing_turn_receipt(tmp_path, monkeypatch):
    ho_root = tmp_path / "ho"
    field_root = tmp_path / "field"
    monkeypatch.setattr("hg_runtime.hands_off_session.schema.STORE_ROOT", ho_root)
    monkeypatch.setattr("hg_runtime.hands_off_session.session_receipts.session_dir", lambda sid, base=None: ho_root / sid)
    monkeypatch.setattr("hg_runtime.hands_off_session.heartbeat.session_dir", lambda sid, base=None: ho_root / sid)
    audit = run_continuity_audit(
        "audit-1",
        state_payload={"turn_count": 5, "external_side_effect_count": 0},
        session_id="audit-1",
        hands_off_base=ho_root,
        field_base=field_root,
    )
    assert audit.turn_receipts_complete is False
    assert audit.verdict == OvernightFieldRunVerdict.RED_TURN_WITHOUT_RECEIPT.value


def test_continuity_ok_with_receipts(tmp_path, monkeypatch):
    ho_root = tmp_path / "ho"
    field_root = tmp_path / "field"
    sid = "audit-2"
    rec_dir = ho_root / sid / "receipts"
    rec_dir.mkdir(parents=True)
    import json

    payload = {
        "continuous_turn_receipt_id": "cont-turn-audit-2-1",
        "session_id": sid,
        "turn_index": 1,
        "turn_receipt_ref": "tr1",
        "task_selection_receipt_ref": "ts1",
        "broker_decision_ref": "br1",
        "selected_task_type": "inspect_queue",
        "verdict": "GREEN",
        "external_side_effect": False,
        "governed_work_receipt_ref": "gw1",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    (rec_dir / "cont-turn-audit-2-1.json").write_text(json.dumps(payload), encoding="utf-8")
    hb_dir = ho_root / sid
    hb_dir.mkdir(parents=True, exist_ok=True)
    (hb_dir / "latest_heartbeat.json").write_text(
        json.dumps({"heartbeat_id": "hb1", "session_id": sid, "pid": 1, "turn_count": 1, "status": "running", "created_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("hg_runtime.hands_off_session.schema.STORE_ROOT", ho_root)
    monkeypatch.setattr("hg_runtime.hands_off_session.session_receipts.session_dir", lambda s, base=None: ho_root / s)
    monkeypatch.setattr("hg_runtime.hands_off_session.heartbeat.session_dir", lambda s, base=None: ho_root / s)
    cp_dir = field_root / sid / "receipts"
    cp_dir.mkdir(parents=True)
    (cp_dir / "checkpoint-cp1.json").write_text(
        json.dumps({"checkpoint_receipt_id": "checkpoint-cp1", "field_run_id": sid, "turn_count": 1, "task_selection_count": 1, "governed_work_count": 1, "heartbeat_ref": "hb1", "external_side_effect_count": 0, "created_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    audit = run_continuity_audit(
        sid,
        state_payload={"turn_count": 1, "external_side_effect_count": 0},
        session_id=sid,
        hands_off_base=ho_root,
        field_base=field_root,
    )
    assert audit.turn_receipts_complete is True
    assert audit.governed_work_receipts_complete is True
