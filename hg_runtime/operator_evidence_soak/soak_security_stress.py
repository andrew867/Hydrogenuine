"""OES-3 defensive security findings from soak stress."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.schemas import assert_neutral, neutral_flags, record_hash


def build_soak_security_finding(*, finding_id: str, surface: str, finding_type: str) -> dict:
    finding = {
        "schema_version": "1",
        "record_type": "soak_security_finding_v1",
        "finding_id": finding_id,
        "surface": surface,
        "finding_type": finding_type,
        "security_finding_defensive_only": True,
        "tools_authorized": False,
        "authority_granted": False,
        **neutral_flags(),
    }
    finding["record_hash"] = record_hash(finding)
    assert_neutral(finding)
    return finding


def build_soak_security_findings(*, mismatch_records: list[dict]) -> list[dict]:
    findings = [
        build_soak_security_finding(
            finding_id="oes-sec-replay-boundary",
            surface="operator_evidence_soak",
            finding_type="replay_integrity_boundary_observed",
        )
    ]
    for i, mismatch in enumerate(mismatch_records, start=1):
        findings.append(
            build_soak_security_finding(
                finding_id=f"oes-sec-mismatch-{i:03d}",
                surface=mismatch.get("probe_type", "mutation_probe"),
                finding_type="mutation_mismatch_observed",
            )
        )
    return findings


def build_soak_patch_hygiene_task(*, task_id: str, security_finding: dict) -> dict:
    task = {
        "schema_version": "1",
        "record_type": "soak_patch_hygiene_task_v1",
        "task_id": task_id,
        "source_finding_id": security_finding["finding_id"],
        "finding_type": security_finding["finding_type"],
        "requested_scope": security_finding["surface"],
        "patch_hygiene_task_is_patch": False,
        "automatic_patching": False,
        "operator_approval_required": True,
        "patch_request_applied": False,
        **neutral_flags(),
    }
    task["record_hash"] = record_hash(task)
    assert_neutral(task)
    return task


def build_soak_patch_hygiene_tasks(security_findings: list[dict]) -> list[dict]:
    return [
        build_soak_patch_hygiene_task(task_id=f"oes-ph-{i:03d}", security_finding=finding)
        for i, finding in enumerate(security_findings, start=1)
    ]
