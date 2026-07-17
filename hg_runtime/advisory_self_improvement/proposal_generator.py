"""Phase 25 advisory improvement proposal generator (advisory-only).

Emits improvement proposals derived from local proof summaries. Every proposal is
advice for an operator. A proposal is never patch permission, never
self-authorization, never an implementation. The generator also REFUSES forbidden
requests (direct patch, self-merge, provider/web, PDF/OCR, authority grant,
Phase 19 GREEN, Phase 24 full GREEN, automatic belief promotion) by emitting
refusal records instead of proposals.
"""

from __future__ import annotations

from hg_runtime.advisory_self_improvement.schemas import (
    PROPOSAL_CATEGORIES,
    REFUSAL_REASONS,
    Phase25BoundaryError,
    assert_neutral,
    neutral_flags,
    record_hash,
)

# Safe, advisory-only proposals. These never imply permission to act.
_PROPOSAL_SPECS = [
    {
        "proposal_id": "p25-prop-001",
        "category": "COVERAGE_EXPANSION",
        "title": "Expand local fixture corpus under explicit manifests",
        "rationale": "Extended soak is deterministic; more local fixtures would broaden regression coverage without new ingestion surface.",
        "depends_on_inputs": ["sle_rc_extended_soak_status"],
    },
    {
        "proposal_id": "p25-prop-002",
        "category": "OBSERVABILITY",
        "title": "Operator-facing advisory review dashboard",
        "rationale": "Surface SQP review hints and RC boundary matrix to operators; dashboard is not approval.",
        "depends_on_inputs": ["sle_rc_status"],
    },
    {
        "proposal_id": "p25-prop-003",
        "category": "GAP_RECONCILIATION",
        "title": "Scope a narrow P26 experience-ledger adapter",
        "rationale": "Existing receipt/ledger/provenance artifacts likely satisfy P26 prerequisites but do not complete P26; a scoped adapter phase is likely needed.",
        "depends_on_inputs": ["sle_rc_status"],
    },
    {
        "proposal_id": "p25-prop-004",
        "category": "TEST_HARDENING",
        "title": "Add mutation-probe coverage to extended soak regression matrix",
        "rationale": "Mutation detection is not repair; broader probes increase confidence without acting.",
        "depends_on_inputs": ["sle_rc_extended_soak_status"],
    },
    {
        "proposal_id": "p25-prop-005",
        "category": "DOCUMENTATION",
        "title": "Document Phase 19 YELLOW rationale in operator handoff",
        "rationale": "Phase 19 remains YELLOW due to recorded debug dispatch ledger pollution; documenting it prevents accidental laundering.",
        "depends_on_inputs": ["phase40_ledger_repair_status"],
    },
]

# Forbidden requests Phase 25 must refuse. (requested_action, refusal_reason).
_REFUSAL_SPECS = [
    ("apply_patch_to_runtime_directly", "DIRECT_PATCH_FORBIDDEN"),
    ("self_merge_proposal_into_main", "SELF_MERGE_FORBIDDEN"),
    ("enable_external_provider_or_web", "PROVIDER_OR_WEB_FORBIDDEN"),
    ("enable_pdf_or_ocr_ingestion", "PDF_OCR_FORBIDDEN"),
    ("grant_tool_or_authority", "AUTHORITY_GRANT_FORBIDDEN"),
    ("mark_phase19_green", "PHASE19_GREEN_FORBIDDEN"),
    ("mark_phase24_full_green", "PHASE24_FULL_GREEN_FORBIDDEN"),
    ("enable_automatic_belief_promotion", "AUTOMATIC_BELIEF_PROMOTION_FORBIDDEN"),
]


def build_improvement_proposal(*, proposal_id: str, category: str, title: str, rationale: str, depends_on_inputs: list[str]) -> dict:
    if category not in PROPOSAL_CATEGORIES:
        raise Phase25BoundaryError(f"unknown_proposal_category:{category}")
    record = {
        "schema_version": "1",
        "record_type": "advisory_improvement_proposal_v1",
        "proposal_id": proposal_id,
        "category": category,
        "title": title,
        "rationale": rationale,
        "depends_on_inputs": list(depends_on_inputs),
        "status": "ADVISORY_PROPOSED",
        "doctrine_note": "A proposal is not patch permission and is not self-authorization.",
        "proposal_is_patch_permission": False,
        "proposal_is_self_authorization": False,
        "requires_operator_review": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_refusal_record(*, refusal_id: str, requested_action: str, refusal_reason: str) -> dict:
    if refusal_reason not in REFUSAL_REASONS:
        raise Phase25BoundaryError(f"unknown_refusal_reason:{refusal_reason}")
    record = {
        "schema_version": "1",
        "record_type": "advisory_refusal_record_v1",
        "refusal_id": refusal_id,
        "requested_action": requested_action,
        "refusal_reason": refusal_reason,
        "status": "REFUSED",
        "doctrine_note": "Phase 25 is advisory-only; this action is refused, not performed.",
        "action_performed": False,
        "proposal_is_patch_permission": False,
        "proposal_is_self_authorization": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def generate_proposals() -> list[dict]:
    return [build_improvement_proposal(**spec) for spec in _PROPOSAL_SPECS]


def generate_refusals() -> list[dict]:
    return [
        build_refusal_record(refusal_id=f"p25-refusal-{i:03d}", requested_action=action, refusal_reason=reason)
        for i, (action, reason) in enumerate(_REFUSAL_SPECS, start=1)
    ]
