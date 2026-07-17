"""LHRE-05 / CAGI-58 reliability audit schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "LHRE-05"
LEGACY_PHASE_ID = "CAGI-58"
PARENT_PHASE_ID = "LHRE-04"

VERDICT_GREEN = "GREEN_LHRE_05_RELIABILITY_AUDIT"
VERDICT_YELLOW = "YELLOW_LHRE_05_RELIABILITY_AUDIT_PARTIAL"
VERDICT_RED = "RED_LHRE_05_RELIABILITY_AUDIT_FAILED"
GATE_RESULT_SCHEMA = "lhre_05_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

AUDIT_STATUS_COMPLETE = "AUDIT_COMPLETE"
FINDING_SEVERITY_INFO = "INFO"
FINDING_SEVERITY_WARNING = "WARNING"
FINDING_SEVERITY_CRITICAL = "CRITICAL"

AUDIT_IS_NOT_CERTIFICATION = "An audit finding is not certification."
PASS_IS_NOT_DEPLOYMENT = "A reliability pass is not deployment readiness."
CONSISTENCY_IS_NOT_CORRECTNESS = "Gate consistency is not correctness."


class ReliabilityAuditError(Exception):
    pass


def reject_audit_authority(payload: dict) -> None:
    for key in (
        "certifies_deployment",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
        "auto_remediate",
    ):
        if payload.get(key):
            raise ReliabilityAuditError(
                f"Audit authority boundary violation: {key} must not be truthy"
            )
