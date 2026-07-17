"""Audit component status for SLE-RC."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.safe_local_evidence_rc.gate_status_reader import latest_gate_result
from hg_runtime.safe_local_evidence_rc.rc_component_status import build_rc_component_status
from hg_runtime.safe_local_evidence_rc.report_indexer import COMPONENT_REPORTS
from hg_runtime.safe_local_evidence_rc.schemas import COMPONENT_CONSOLIDATION, PHASE19_VERDICT, PHASE24_STATUS


def audit_component_statuses(root: Path, *, base_head: str) -> dict:
    statuses = []
    failures = []
    for i, (family, (proof_root, expected)) in enumerate(COMPONENT_CONSOLIDATION.items(), start=1):
        verdict, proof_bundle, gate_data = latest_gate_result(root, proof_root)
        report_path = COMPONENT_REPORTS.get(family, "")
        if not proof_bundle:
            failures.append(f"{family}_proof_missing")
        if verdict != expected or not verdict.startswith("GREEN"):
            failures.append(f"{family}_not_green")
        statuses.append(
            build_rc_component_status(
                status_id=f"rc-status-{i:03d}",
                component_family=family,
                proof_bundle=proof_bundle or "MISSING",
                gate_verdict=verdict,
                expected_verdict=expected,
                report_path=report_path,
                base_head=gate_data.get("base_head", base_head) if gate_data else base_head,
            )
        )
    return {
        "rc_component_statuses": statuses,
        "failures": failures,
        "all_green": not failures,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
    }
