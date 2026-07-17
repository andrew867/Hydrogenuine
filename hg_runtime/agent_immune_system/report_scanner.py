"""Scan reports for proof disagreement and phase boundary violations."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hg_runtime.agent_immune_system.finding import build_finding
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS

PHASE19_GREEN_PATTERN = re.compile(r"phase\s*19.*green", re.I)
PHASE24_FULL_GREEN_PATTERN = re.compile(r"phase\s*24.*(full\s+)?overnight.*green", re.I)


def scan_report(bundle_dir: Path) -> list[dict]:
    findings: list[dict] = []
    bundle_dir = Path(bundle_dir)
    label = bundle_dir.name
    gate_path = bundle_dir / "gate_result.json"
    report_path = bundle_dir / "report_snapshot.md"

    if not gate_path.exists():
        return findings

    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""

    gate_verdict = gate.get("verdict", "")
    if report_text and gate_verdict:
        report_verdict_match = re.search(r"`([^`]+)`\s*$", report_text, re.M)
        if report_verdict_match:
            report_verdict = report_verdict_match.group(1)
            if report_verdict != gate_verdict and not gate.get("report_verdict_mismatch_expected"):
                findings.append(
                    build_finding(
                        record_type="record_health_finding_v1",
                        finding_id=f"rh-{label}-report-proof-mismatch",
                        finding_type="report_proof_mismatch",
                        severity="RED",
                        safe_action="REQUEST_OPERATOR_REVIEW",
                        surface=str(report_path),
                        blocks_green=True,
                        extra={"gate_verdict": gate_verdict, "report_verdict": report_verdict},
                    )
                )

    if gate.get("gate_result_mismatch"):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-gate-result-mismatch",
                finding_type="gate_result_mismatch",
                severity="RED",
                safe_action="REQUEST_OPERATOR_REVIEW",
                surface=str(gate_path),
                blocks_green=True,
            )
        )

    phase19 = gate.get("phase19_verdict", "")
    if gate.get("phase19_marked_green") or (
        phase19 and not str(phase19).startswith("YELLOW") and "phase19" in str(phase19).lower()
    ):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-phase19-launder",
                finding_type="phase19_yellow_laundering",
                severity="PANIC",
                safe_action="RESTRICT",
                surface=str(gate_path),
                blocks_green=True,
            )
        )
    elif gate.get("stale_phase19_yellow"):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-stale-phase19-yellow",
                finding_type="stale_yellow_requires_review",
                severity="YELLOW",
                safe_action="REQUEST_OPERATOR_REVIEW",
                surface=str(gate_path),
                extra={"phase_ref": "Phase 19"},
            )
        )

    if gate.get("phase24_full_overnight_green") or (
        report_text and PHASE24_FULL_GREEN_PATTERN.search(report_text)
    ):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-phase24-launder",
                finding_type="phase24_infrastructure_laundering",
                severity="RED",
                safe_action="RESTRICT",
                surface=str(gate_path),
                blocks_green=True,
            )
        )

    if gate.get("dirty_report_churn"):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-dirty-report-churn",
                finding_type="dirty_report_churn",
                severity="YELLOW",
                safe_action="REQUEST_OPERATOR_REVIEW",
                surface=str(report_path),
            )
        )

    if not gate.get("phase19_yellow_preserved", True) and PHASE19_VERDICT.startswith("YELLOW"):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-phase19-not-preserved",
                finding_type="phase19_yellow_not_preserved",
                severity="RED",
                safe_action="RESTRICT",
                surface=str(gate_path),
                blocks_green=True,
            )
        )

    if not gate.get("phase24_infrastructure_only_preserved", True):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-phase24-not-preserved",
                finding_type="phase24_infrastructure_not_preserved",
                severity="RED",
                safe_action="RESTRICT",
                surface=str(gate_path),
                blocks_green=True,
            )
        )

    return findings
