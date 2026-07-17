"""LHRE-05 / CAGI-58 auditor — cross-phase reliability checking."""

from __future__ import annotations

from hg_runtime.reliability_audit.schemas import (
    FINDING_SEVERITY_CRITICAL,
    ReliabilityAuditError,
    reject_audit_authority,
)


def validate_phase_record(record: dict) -> list[str]:
    issues = []
    if not record.get("phase_id"):
        issues.append("missing_phase_id")
    if not record.get("gate_verdict"):
        issues.append("missing_gate_verdict")
    if not record.get("all_tests_passed"):
        issues.append("tests_not_passed")
    return issues


def validate_finding(finding: dict) -> list[str]:
    issues = []
    if not finding.get("finding_id"):
        issues.append("missing_finding_id")
    if finding.get("certifies_deployment"):
        issues.append("finding_must_not_certify")
    reject_audit_authority(finding)
    return issues


def check_cross_phase_consistency(records: list[dict]) -> dict:
    return {
        "phases_checked": len(records),
        "all_green": all("GREEN" in r.get("gate_verdict", "") for r in records),
        "all_replays_ok": all(r.get("replay_deterministic", False) for r in records),
        "all_safety_ok": all(r.get("safety_boundaries_intact", False) for r in records),
    }


def has_critical_findings(findings: list[dict]) -> bool:
    return any(f.get("severity") == FINDING_SEVERITY_CRITICAL for f in findings)
