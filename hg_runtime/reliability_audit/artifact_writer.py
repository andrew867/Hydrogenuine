"""LHRE-05 / CAGI-58 artifact writer — builds reliability audit receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.reliability_audit.auditor import (
    check_cross_phase_consistency,
    has_critical_findings,
    validate_finding,
    validate_phase_record,
)
from hg_runtime.reliability_audit.schemas import (
    AUDIT_IS_NOT_CERTIFICATION,
    CONSISTENCY_IS_NOT_CORRECTNESS,
    PASS_IS_NOT_DEPLOYMENT,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_audit_artifacts(
    phase_records: list[dict],
    findings: list[dict],
) -> dict:
    validated_records = []
    for r in phase_records:
        issues = validate_phase_record(r)
        validated_records.append({"record": r, "valid": not issues, "issues": issues})

    validated_findings = []
    for f in findings:
        issues = validate_finding(f)
        validated_findings.append({"finding": f, "valid": not issues, "issues": issues})

    consistency = check_cross_phase_consistency(phase_records)

    artifacts = {
        "phase_records": validated_records,
        "record_count": len(validated_records),
        "findings": validated_findings,
        "finding_count": len(validated_findings),
        "consistency": consistency,
        "all_records_valid": all(v["valid"] for v in validated_records),
        "all_findings_valid": all(v["valid"] for v in validated_findings),
        "has_critical": has_critical_findings(findings),
        "boundary_assertions": {
            "audit_is_not_certification": AUDIT_IS_NOT_CERTIFICATION,
            "pass_is_not_deployment": PASS_IS_NOT_DEPLOYMENT,
            "consistency_is_not_correctness": CONSISTENCY_IS_NOT_CORRECTNESS,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    return [p for p in ("sk-", "api_key=", "Bearer ", "token=", "password=") if p.lower() in text.lower()]
