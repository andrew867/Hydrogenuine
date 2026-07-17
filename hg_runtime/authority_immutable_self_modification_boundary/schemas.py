"""BSI-03 / CAGI-62 authority-immutable self-modification boundary schemas.

THIS IS LOAD-BEARING.

Protected components are registered here. Forbidden mutation classes are
defined here. If a mutation attempt targets a protected component with
a forbidden mutation class, it MUST be rejected and quarantined.
"""

from __future__ import annotations

PHASE_ID = "BSI-03"
LEGACY_PHASE_ID = "CAGI-62"
PARENT_PHASE_ID = "BSI-02"

VERDICT_GREEN = "GREEN_P62_AUTHORITY_IMMUTABLE_SELF_MODIFICATION_BOUNDARY"
VERDICT_YELLOW = "YELLOW_P62_AUTHORITY_BOUNDARY_PARTIAL"
VERDICT_RED = "RED_P62_AUTHORITY_BOUNDARY_FAILED"
GATE_RESULT_SCHEMA = "bsi_03_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

PROTECTED_COMPONENTS = frozenset({
    "authority_kernel",
    "permit_policy",
    "gate_policy",
    "stop_panic_handling",
    "phase19_incident_record",
    "phase24_status",
    "proof_bundle_validators",
    "tool_authorization_policy",
    "provider_enablement_policy",
    "hg_local_boundary",
    "deployment_live_effect_policy",
})

FORBIDDEN_MUTATION_CLASSES = frozenset({
    "AUTHORITY_GRANT",
    "AUTHORITY_ESCALATION",
    "PERMIT_POLICY_CHANGE",
    "GATE_POLICY_CHANGE",
    "STOP_PANIC_OVERRIDE",
    "INCIDENT_RECORD_ERASURE",
    "INFRASTRUCTURE_STATUS_OVERRIDE",
    "PROOF_VALIDATOR_BYPASS",
    "TOOL_AUTHORIZATION",
    "PROVIDER_ENABLEMENT",
    "BOUNDARY_ESCAPE",
    "LIVE_EFFECT_ENABLEMENT",
    "SELF_MARKING_SAFE",
    "OPERATOR_REVIEW_BYPASS",
})

QUARANTINE_STATUS_QUARANTINED = "QUARANTINED"
QUARANTINE_STATUS_ESCALATED = "ESCALATED_TO_OPERATOR"
REJECTION_REASON_PROTECTED_COMPONENT = "MUTATION_TARGETS_PROTECTED_COMPONENT"
REJECTION_REASON_FORBIDDEN_CLASS = "MUTATION_IS_FORBIDDEN_CLASS"


class AuthorityBoundaryViolation(Exception):
    pass


def reject_authority_mutation(payload: dict) -> None:
    for key in (
        "grants_authority",
        "escalates_authority",
        "changes_permit_policy",
        "changes_gate_policy",
        "overrides_stop_panic",
        "erases_incident_record",
        "overrides_infrastructure_status",
        "bypasses_proof_validator",
        "authorizes_tool",
        "enables_provider",
        "escapes_boundary",
        "enables_live_effect",
        "marks_self_safe",
        "bypasses_operator_review",
        "claims_agi",
        "claims_consciousness",
        "claims_sovereignty",
        "self_authorizes",
    ):
        if payload.get(key):
            raise AuthorityBoundaryViolation(
                f"Authority boundary violation: {key} must not be truthy"
            )
