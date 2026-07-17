"""EXCITON governed work loop monitor."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.governed_work_loop.postflight import load_postflight
from hg_runtime.governed_work_loop.schema import STORE_ROOT, load_governed_work_policy, now_iso
from hg_runtime.governed_work_loop.work_envelope import load_work_envelope
from hg_runtime.hands_off_session.manual_controls import check_panic, check_stop


def _latest_receipt() -> dict[str, Any] | None:
    rdir = STORE_ROOT / "receipts"
    if not rdir.is_dir():
        return None
    files = sorted(rdir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    import json

    return json.loads(files[0].read_text(encoding="utf-8"))


def build_governed_work_loop_monitor_snapshot(run_id: str | None = None) -> dict[str, Any]:
    policy = load_governed_work_policy()
    pf = load_postflight(run_id) if run_id else None
    latest = _latest_receipt()
    envelope = None
    if pf:
        ref_path = STORE_ROOT / "envelopes"
        if ref_path.is_dir():
            for p in sorted(ref_path.glob("*.json"), reverse=True):
                envelope = load_work_envelope(p.stem)
                if envelope:
                    break

    stop_active = check_stop(run_id) if run_id else False
    panic_active = check_panic(run_id) if run_id else False

    return {
        "panel_id": "agent_zero_governed_work_loop_monitor",
        "title": "Agent Zero Governed Work Loop Monitor",
        "envelope_id": envelope.envelope_id if envelope else None,
        "allowed_work_scopes": list(envelope.allowed_work_scopes) if envelope else [],
        "external_action_quota_ref": envelope.external_action_quota_ref if envelope else None,
        "live_dispatch_allowed": policy.get("zero_may_live_dispatch_by_default", False),
        "selected_task": latest.get("task_selection_ref") if latest else None,
        "work_item": latest.get("work_item_ref") if latest else None,
        "work_receipt": latest.get("governed_work_receipt_id") if latest else None,
        "broker_decision": latest.get("broker_decision_ref") if latest else None,
        "external_candidate_refs": [latest["external_candidate_ref"]] if latest and latest.get("external_candidate_ref") else [],
        "dry_dispatch_refs": [latest["dry_dispatch_ref"]] if latest and latest.get("dry_dispatch_ref") else [],
        "live_dispatch_refs": [],
        "refusal_reasons": [],
        "stop_status": "active" if stop_active else "clear",
        "panic_status": "active" if panic_active else "clear",
        "external_side_effect_count": pf.external_side_effect_count if pf else 0,
        "verdict": pf.verdict if pf else "YELLOW_NO_GOVERNED_WORK_YET",
        "external_action_autonomous_green": False,
        "dry_run_only": True,
        "exciton_is_approval": False,
        "policy_phase": policy.get("phase", 23),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
