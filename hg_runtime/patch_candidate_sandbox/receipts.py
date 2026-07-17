"""Phase 38 patch-candidate decision records and deterministic hashing.

A decision record is the operator-facing verdict for one candidate. It records
every required boundary flag as ``false`` and is guarded so the sandbox can never
emit a record that claims it applied, committed, pushed, deployed, or authorized
anything.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.patch_candidate_sandbox.schemas import (
    CANDIDATE_PRODUCING_DECISIONS,
    PATCH_CANDIDATE_DECISION_SCHEMA,
    assert_neutral_output,
    neutral_flags,
    require_fields,
)

_REQUIRED_DECISION_FIELDS = (
    "patch_candidate_id",
    "source_work_package_id",
    "source_work_package_hash",
    "candidate_status",
    "sandbox_mode",
)


def patch_candidate_decision(
    *,
    patch_candidate_id: str,
    source: Mapping[str, Any],
    candidate_hash: str,
    decision: str,
    sandbox_mode: str,
    audit: Mapping[str, Any] | None,
    sandbox_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build the decision receipt for one patch candidate."""
    audit = dict(audit or {})
    authority_audit = audit.get("authority_boundary_audit", {})
    dry_live_audit = audit.get("dry_live_boundary_audit", {})
    secret = audit.get("secret_leakage", {})

    record = {
        "schema": PATCH_CANDIDATE_DECISION_SCHEMA,
        "patch_candidate_id": patch_candidate_id,
        "source_work_package_id": source["source_work_package_id"],
        "source_work_package_hash": source["source_work_package_hash"],
        "source_status": source["source_status"],
        "candidate_hash": candidate_hash,
        "candidate_status": decision,
        "sandbox_mode": sandbox_mode,
        "candidate_artifact_produced": decision in CANDIDATE_PRODUCING_DECISIONS,
        "changed_files": list(audit.get("changed_files", [])),
        "risk_classes": list(audit.get("risk_classes", [])),
        "authority_boundary_risk": bool(
            authority_audit.get("touches_authority_paths") or authority_audit.get("authority_bypass_detected")
        ),
        "dry_live_boundary_risk": bool(
            dry_live_audit.get("touches_live_paths") or dry_live_audit.get("live_effect_enabled_by_default_detected")
        ),
        "secret_leakage_risk": bool(secret.get("secret_leakage_detected")),
        "test_impact": audit.get("test_impact_audit", {}),
        "rollback_plan": audit.get("rollback_plan", {}),
        "operator_review_required": bool(audit.get("operator_review_required", True)),
        "authority_boundary_audit": authority_audit,
        "dry_live_boundary_audit": dry_live_audit,
        "sandbox_receipt": dict(sandbox_receipt or {}),
        # Hard boundary flags — always false for a Phase 38 candidate.
        "apply_allowed": False,
        "committed": False,
        "pushed": False,
        "deployed": False,
        "patch_applied_to_live_repo": False,
        "created_external_side_effects": False,
        "created_live_posts": False,
        "authority_granted": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    require_fields(record, _REQUIRED_DECISION_FIELDS)
    assert_neutral_output(record)
    record["decision_hash"] = canonical_hash(record)
    return record


__all__ = ["patch_candidate_decision"]
