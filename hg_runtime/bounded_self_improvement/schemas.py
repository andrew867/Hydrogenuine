"""BSI-01 / CAGI-60 bounded self-improvement proposal schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "BSI-01"
LEGACY_PHASE_ID = "CAGI-60"
PARENT_PHASE_ID = "LHRE-06"
PRECURSOR_PHASE_ID = "PHASE-25"

VERDICT_GREEN = "GREEN_P60_BOUNDED_SELF_IMPROVEMENT_PROPOSAL_LOOP"
VERDICT_YELLOW = "YELLOW_P60_BOUNDED_SELF_IMPROVEMENT_PARTIAL"
VERDICT_RED = "RED_P60_BOUNDED_SELF_IMPROVEMENT_FAILED"
GATE_RESULT_SCHEMA = "bsi_01_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

PROPOSAL_STATUS_DRAFT = "PROPOSAL_DRAFT"
PROPOSAL_STATUS_QUEUED = "PROPOSAL_QUEUED"
PROPOSAL_STATUS_REVIEWED = "PROPOSAL_REVIEWED_NOT_APPLIED"

PROPOSAL_IS_NOT_PATCH = "A proposal is not a patch."
PROPOSAL_IS_NOT_PERMISSION = "A proposal is not permission."
PROPOSAL_CANNOT_SELF_APPLY = "A proposal cannot self-apply."
PROPOSAL_CANNOT_MUTATE_AUTHORITY = "A proposal cannot mutate authority."

PROPOSAL_CATEGORIES = frozenset({
    "COVERAGE_EXPANSION",
    "DOCUMENTATION",
    "OBSERVABILITY",
    "TEST_HARDENING",
    "GAP_RECONCILIATION",
    "OPERATOR_WORKFLOW",
    "PERFORMANCE",
    "SAFETY_HARDENING",
})


class BoundedSelfImprovementError(Exception):
    pass


def reject_proposal_authority(payload: dict) -> None:
    for key in (
        "self_apply",
        "apply_patch",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
        "mutates_authority",
        "mutates_policy",
        "mutates_gate",
        "mutates_permit",
        "bypasses_operator_review",
    ):
        if payload.get(key):
            raise BoundedSelfImprovementError(
                f"Proposal authority boundary violation: {key} must not be truthy"
            )
