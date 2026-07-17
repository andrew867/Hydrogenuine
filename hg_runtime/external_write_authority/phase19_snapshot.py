"""Phase 19 EXCITON incident monitor snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.external_write_authority.action_ledger import (
    Phase19Verdict,
    detect_duplicate_live_dispatch,
    load_ledger_entries,
    phase18_live_proof_status,
)
from hg_runtime.external_write_authority.dispatch_classification import (
    analyze_ledger_pollution,
    load_dispatch_rows,
    phase19_verdict_for_pollution,
)
from hg_runtime.external_write_authority.incident_report import load_latest_incident_report
from hg_runtime.external_write_authority.incident_audit import DRILL_DIR
from hg_runtime.external_write_authority.rollback import load_rollback_plans
from hg_runtime.external_write_authority.schema import STORE_ROOT, now_iso


@dataclass
class Phase19IncidentMonitorSnapshot:
    phase18_live_proof_exists: bool
    live_action_count: int
    ledger_entry_count: int
    platform_proof_status: str
    reverification_status: str
    rollback_plan_count: int
    incident_report_ref: str | None
    duplicate_dispatch_detected: bool
    bypass_drill_passed: bool
    verdict: str
    freshness: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "phase18_live_proof_exists": self.phase18_live_proof_exists,
            "live_action_count": self.live_action_count,
            "ledger_entry_count": self.ledger_entry_count,
            "platform_proof_status": self.platform_proof_status,
            "reverification_status": self.reverification_status,
            "rollback_plan_count": self.rollback_plan_count,
            "incident_report_ref": self.incident_report_ref,
            "duplicate_dispatch_detected": self.duplicate_dispatch_detected,
            "bypass_drill_passed": self.bypass_drill_passed,
            "freshness": self.freshness,
            "verdict": self.verdict,
            "exciton_is_approval": False,
            "live_rollback_buttons": False,
        }


def build_phase19_monitor_snapshot() -> Phase19IncidentMonitorSnapshot:
    proof = phase18_live_proof_status()
    entries = load_ledger_entries()
    report = load_latest_incident_report()
    rollback_plans = load_rollback_plans()
    duplicate = detect_duplicate_live_dispatch(entries)
    pollution = analyze_ledger_pollution(
        load_dispatch_rows(),
        ledger_live_entry_count=sum(1 for e in entries if e.external_side_effect),
    )

    reverify_dir = STORE_ROOT / "phase19" / "reverifications"
    reverify_status = "none"
    if reverify_dir.is_dir() and list(reverify_dir.glob("*.json")):
        reverify_status = "completed"

    drill_passed = True
    if DRILL_DIR.is_dir():
        for p in DRILL_DIR.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            if not data.get("passed"):
                drill_passed = False
                break

    if pollution.duplicate_live_dispatch_detected or pollution.debug_unauthorized_live_count > 0 or (
        pollution.recorded_debug_incident_count > 0
        and pollution.ledger_live_entry_count > pollution.envelope_authorized_live_count
    ):
        verdict = phase19_verdict_for_pollution(pollution)
    elif duplicate:
        verdict = "RED_DUPLICATE_LIVE_DISPATCH_DETECTED"
    elif report:
        verdict = report.verdict
    elif not proof["live_proof_exists"]:
        verdict = Phase19Verdict.YELLOW_NO_PROOF
    else:
        verdict = Phase19Verdict.YELLOW_NO_PROOF

    platform_status = report.platform_proof_status if report else "no_report"
    return Phase19IncidentMonitorSnapshot(
        phase18_live_proof_exists=proof["live_proof_exists"],
        live_action_count=proof["live_action_count"],
        ledger_entry_count=len(entries),
        platform_proof_status=platform_status,
        reverification_status=reverify_status,
        rollback_plan_count=len(rollback_plans),
        incident_report_ref=report.incident_report_id if report else None,
        duplicate_dispatch_detected=duplicate,
        bypass_drill_passed=drill_passed,
        freshness=now_iso(),
        verdict=verdict,
    )
