"""OES-3 quarantine candidate stress from soak findings."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.schemas import assert_neutral, neutral_flags, record_hash


def build_soak_quarantine_candidate(*, candidate_id: str, finding: dict) -> dict:
    candidate = {
        "schema_version": "1",
        "record_type": "soak_quarantine_candidate_v1",
        "candidate_id": candidate_id,
        "source_finding_id": finding["finding_id"],
        "signal_type": finding["signal_type"],
        "severity": finding["severity"],
        "quarantine_candidate_is_deletion": False,
        "auto_quarantine_enforced": False,
        "deletion_performed": False,
        **neutral_flags(),
    }
    candidate["record_hash"] = record_hash(candidate)
    assert_neutral(candidate)
    return candidate


def build_soak_quarantine_candidates(health_findings: list[dict]) -> list[dict]:
    stressed = [f for f in health_findings if f["severity"] in {"YELLOW", "RED"}]
    return [
        build_soak_quarantine_candidate(candidate_id=f"oes-quarantine-{i:03d}", finding=finding)
        for i, finding in enumerate(stressed, start=1)
    ]
