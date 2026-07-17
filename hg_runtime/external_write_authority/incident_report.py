"""Phase 19 external action incident report."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_write_authority.action_ledger import (
    Phase19Verdict,
    detect_duplicate_live_dispatch,
    load_ledger_entries,
    load_phase19_policy,
    phase18_live_proof_status,
)
from hg_runtime.external_write_authority.dispatch_classification import (
    analyze_ledger_pollution,
    load_dispatch_rows,
    phase19_verdict_for_pollution,
)
from hg_runtime.external_write_authority.platform_reverify import reverify_platform_proofs
from hg_runtime.external_write_authority.rollback import load_rollback_plans
from hg_runtime.external_write_authority.schema import STORE_ROOT, new_id, now_iso

INCIDENT_DIR = STORE_ROOT / "phase19" / "incident_reports"


@dataclass
class ExternalActionIncidentReport:
    incident_report_id: str
    phase18_live_proof_exists: bool
    live_action_count: int
    ledger_entry_refs: tuple[str, ...]
    platform_proof_status: str
    rollback_plan_refs: tuple[str, ...]
    incident_type: str
    duplicate_dispatch_detected: bool
    created_at: str
    verdict: str
    hash: str | None = None
    ledger_pollution: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "incident_report_id": self.incident_report_id,
            "phase18_live_proof_exists": self.phase18_live_proof_exists,
            "live_action_count": self.live_action_count,
            "ledger_entry_refs": list(self.ledger_entry_refs),
            "platform_proof_status": self.platform_proof_status,
            "rollback_plan_refs": list(self.rollback_plan_refs),
            "incident_type": self.incident_type,
            "duplicate_dispatch_detected": self.duplicate_dispatch_detected,
            "created_at": self.created_at,
            "verdict": self.verdict,
            "hash": self.hash,
        }
        if self.ledger_pollution is not None:
            payload["ledger_pollution"] = self.ledger_pollution
        return payload

    def with_hash(self) -> ExternalActionIncidentReport:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ExternalActionIncidentReport(**{**self.__dict__, "hash": compute_record_hash(body)})


def write_incident_report() -> ExternalActionIncidentReport:
    policy = load_phase19_policy()
    proof_status = phase18_live_proof_status()
    entries = load_ledger_entries()
    live_entries = [e for e in entries if e.external_side_effect]
    reverifications = reverify_platform_proofs()
    rollback_plans = load_rollback_plans()
    duplicate = detect_duplicate_live_dispatch(entries)
    pollution = analyze_ledger_pollution(
        load_dispatch_rows(),
        ledger_live_entry_count=sum(1 for e in entries if e.external_side_effect),
    )
    pollution_payload = pollution.to_payload()

    if not proof_status["live_proof_exists"]:
        verdict = Phase19Verdict.YELLOW_NO_PROOF
        incident_type = "readiness_no_live_proof"
        platform_status = "YELLOW_NO_LIVE_PLATFORM_PROOF_TO_AUDIT"
    elif pollution.duplicate_live_dispatch_detected or pollution.debug_unauthorized_live_count > 0 or (
        pollution.recorded_debug_incident_count > 0
        and pollution.ledger_live_entry_count > pollution.envelope_authorized_live_count
    ):
        verdict = phase19_verdict_for_pollution(pollution)
        if verdict.startswith("YELLOW_"):
            incident_type = "ledger_polluted_recorded_debug_incident"
            platform_status = "ledger_polluted_acknowledged"
        elif verdict.startswith("RED_"):
            incident_type = "duplicate_live_dispatch"
            platform_status = "duplicate"
        else:
            incident_type = "live_action_audited"
            platform_status = "verified"
    elif duplicate and not pollution.incident_report_doc_present:
        verdict = "RED_LEDGER_POLLUTED_UNACKNOWLEDGED"
        incident_type = "ledger_polluted_unacknowledged"
        platform_status = "duplicate"
    elif duplicate:
        verdict = "RED_DUPLICATE_LIVE_DISPATCH_DETECTED"
        incident_type = "duplicate_live_dispatch"
        platform_status = "duplicate"
    elif not live_entries:
        verdict = Phase19Verdict.YELLOW_NO_PROOF
        incident_type = "readiness_no_ledger_live_entries"
        platform_status = "missing"
    elif any(r.verdict == Phase19Verdict.RED_HASH_MISMATCH for r in reverifications):
        verdict = Phase19Verdict.RED_HASH_MISMATCH
        incident_type = "content_hash_mismatch"
        platform_status = "hash_mismatch"
    elif any(r.verdict == Phase19Verdict.YELLOW_VISIBILITY for r in reverifications):
        verdict = Phase19Verdict.YELLOW_VISIBILITY
        incident_type = "visibility_delayed"
        platform_status = "visibility_delayed"
    elif policy.get("rollback_plan_required") and not rollback_plans and live_entries:
        verdict = "RED_ROLLBACK_PLAN_MISSING"
        incident_type = "rollback_plan_missing"
        platform_status = "rollback_missing"
    elif proof_status["live_proof_exists"] and live_entries and reverifications:
        all_green = all(r.verdict == Phase19Verdict.GREEN for r in reverifications)
        if all_green and proof_status["has_platform_url"]:
            verdict = Phase19Verdict.GREEN
            incident_type = "live_action_audited"
            platform_status = "verified"
        else:
            verdict = Phase19Verdict.YELLOW_VISIBILITY
            incident_type = "proof_incomplete"
            platform_status = "incomplete"
    else:
        verdict = Phase19Verdict.YELLOW_NO_PROOF
        incident_type = "readiness"
        platform_status = "no_proof"

    report = ExternalActionIncidentReport(
        incident_report_id=new_id("p19-incident"),
        phase18_live_proof_exists=proof_status["live_proof_exists"],
        live_action_count=proof_status["live_action_count"],
        ledger_entry_refs=tuple(e.ledger_entry_id for e in entries),
        platform_proof_status=platform_status,
        rollback_plan_refs=tuple(p.rollback_plan_id for p in rollback_plans),
        incident_type=incident_type,
        duplicate_dispatch_detected=duplicate,
        created_at=now_iso(),
        verdict=verdict,
    ).with_hash()

    INCIDENT_DIR.mkdir(parents=True, exist_ok=True)
    (INCIDENT_DIR / f"{report.incident_report_id}.json").write_text(
        json.dumps(report.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return report


def load_latest_incident_report() -> ExternalActionIncidentReport | None:
    if not INCIDENT_DIR.is_dir():
        return None
    files = sorted(INCIDENT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    data = json.loads(files[0].read_text(encoding="utf-8"))
    return ExternalActionIncidentReport(
        incident_report_id=data["incident_report_id"],
        phase18_live_proof_exists=data["phase18_live_proof_exists"],
        live_action_count=data["live_action_count"],
        ledger_entry_refs=tuple(data.get("ledger_entry_refs") or ()),
        platform_proof_status=data["platform_proof_status"],
        rollback_plan_refs=tuple(data.get("rollback_plan_refs") or ()),
        incident_type=data["incident_type"],
        duplicate_dispatch_detected=data["duplicate_dispatch_detected"],
        created_at=data["created_at"],
        verdict=data["verdict"],
        hash=data.get("hash"),
        ledger_pollution=data.get("ledger_pollution"),
    )
