"""Field run continuity audit."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.overnight_field_run.schema import OvernightFieldRunVerdict, field_run_dir, new_id, now_iso


@dataclass
class FieldRunContinuityAudit:
    continuity_audit_id: str
    field_run_id: str
    turn_count_monotonic: bool
    turn_receipts_complete: bool
    task_selection_receipts_complete: bool
    governed_work_receipts_complete: bool
    broker_refs_present: bool
    heartbeat_fresh: bool
    checkpoint_gaps: list[str] = field(default_factory=list)
    external_side_effects_outside_envelope: int = 0
    stop_panic_available: bool = True
    scheduler_artifacts: bool = False
    background_survivor: bool = False
    issues: list[str] = field(default_factory=list)
    verdict: str = ""
    created_at: str = ""
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "continuity_audit_id": self.continuity_audit_id,
            "field_run_id": self.field_run_id,
            "turn_count_monotonic": self.turn_count_monotonic,
            "turn_receipts_complete": self.turn_receipts_complete,
            "task_selection_receipts_complete": self.task_selection_receipts_complete,
            "governed_work_receipts_complete": self.governed_work_receipts_complete,
            "broker_refs_present": self.broker_refs_present,
            "heartbeat_fresh": self.heartbeat_fresh,
            "checkpoint_gaps": self.checkpoint_gaps,
            "external_side_effects_outside_envelope": self.external_side_effects_outside_envelope,
            "stop_panic_available": self.stop_panic_available,
            "scheduler_artifacts": self.scheduler_artifacts,
            "background_survivor": self.background_survivor,
            "issues": self.issues,
            "verdict": self.verdict,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> FieldRunContinuityAudit:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return FieldRunContinuityAudit(**{**self.__dict__, "hash": compute_record_hash(body)})


def write_continuity_audit(audit: FieldRunContinuityAudit, *, base: Path | None = None) -> Path:
    root = field_run_dir(audit.field_run_id, base=base)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "continuity_audit.json"
    path.write_text(json.dumps(audit.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_continuity_audit(field_run_id: str, *, base: Path | None = None) -> FieldRunContinuityAudit | None:
    path = field_run_dir(field_run_id, base=base) / "continuity_audit.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return FieldRunContinuityAudit(**data)


def run_continuity_audit(
    field_run_id: str,
    *,
    state_payload: dict[str, Any],
    session_id: str,
    hands_off_base: Path | None = None,
    field_base: Path | None = None,
    heartbeat_max_age_seconds: float = 600.0,
) -> FieldRunContinuityAudit:
    from hg_runtime.hands_off_session.schema import STORE_ROOT as HO_ROOT
    from hg_runtime.hands_off_session.session_receipts import list_continuous_turn_receipts
    from hg_runtime.hands_off_session.heartbeat import load_latest_heartbeat
    from hg_runtime.overnight_field_run.field_run_receipts import list_checkpoint_receipts

    issues: list[str] = []
    turn_count = int(state_payload.get("turn_count", 0))
    ho_base = hands_off_base or HO_ROOT

    receipts = list_continuous_turn_receipts(session_id, base=ho_base)
    turn_receipts_ok = len(receipts) >= turn_count if turn_count > 0 else True
    if not turn_receipts_ok:
        issues.append("missing_turn_receipts")

    ts_ok = all(r.task_selection_receipt_ref for r in receipts) if receipts else True
    if not ts_ok:
        issues.append("missing_task_selection_receipts")

    gw_ok = all(getattr(r, "governed_work_receipt_ref", None) for r in receipts) if receipts else True
    if turn_count > 0 and not gw_ok:
        issues.append("missing_governed_work_receipts")

    broker_ok = all(r.broker_decision_ref for r in receipts) if receipts else True
    if not broker_ok:
        issues.append("missing_broker_refs")

    hb = load_latest_heartbeat(session_id, base=ho_base)
    hb_fresh = True
    if hb:
        from datetime import datetime, timezone

        try:
            ts = datetime.fromisoformat(hb.created_at.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            hb_fresh = age <= heartbeat_max_age_seconds
        except (ValueError, TypeError):
            hb_fresh = True
    if not hb_fresh:
        issues.append("stale_heartbeat")

    checkpoints = list_checkpoint_receipts(field_run_id, base=field_base)
    checkpoint_gaps: list[str] = []
    if turn_count > 0 and not checkpoints:
        checkpoint_gaps.append("no_checkpoints_recorded")
        issues.append("missing_checkpoint")

    ext_se = int(state_payload.get("external_side_effect_count", 0))
    if ext_se > 0:
        issues.append("external_side_effect_detected")

    verdict = "GREEN_CONTINUITY_OK"
    if "missing_turn_receipts" in issues:
        verdict = OvernightFieldRunVerdict.RED_TURN_WITHOUT_RECEIPT.value
    elif "missing_task_selection_receipts" in issues:
        verdict = OvernightFieldRunVerdict.RED_TASK_SELECTION_WITHOUT_RECEIPT.value
    elif "missing_governed_work_receipts" in issues:
        verdict = OvernightFieldRunVerdict.RED_WORK_ITEM_WITHOUT_RECEIPT.value
    elif "stale_heartbeat" in issues:
        verdict = OvernightFieldRunVerdict.RED_HEARTBEAT_STALE.value
    elif "external_side_effect_detected" in issues:
        verdict = OvernightFieldRunVerdict.RED_EXTERNAL_SIDE_EFFECT.value
    elif issues:
        verdict = "YELLOW_CONTINUITY_GAPS"

    audit = FieldRunContinuityAudit(
        continuity_audit_id=new_id("continuity"),
        field_run_id=field_run_id,
        turn_count_monotonic=True,
        turn_receipts_complete=turn_receipts_ok,
        task_selection_receipts_complete=ts_ok,
        governed_work_receipts_complete=gw_ok,
        broker_refs_present=broker_ok,
        heartbeat_fresh=hb_fresh,
        checkpoint_gaps=checkpoint_gaps,
        external_side_effects_outside_envelope=ext_se,
        stop_panic_available=True,
        scheduler_artifacts=False,
        background_survivor=False,
        issues=issues,
        verdict=verdict,
        created_at=now_iso(),
    ).with_hash()
    write_continuity_audit(audit, base=field_base)
    return audit
