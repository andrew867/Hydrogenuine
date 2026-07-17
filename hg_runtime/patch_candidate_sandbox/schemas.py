"""Phase 38 patch candidate sandbox and diff auditor schemas and safety boundaries.

This phase takes Phase 37 generated work packages and prepares isolated
*patch-candidate artifacts* for operator review. It is review-preparation only:

* It does not apply patches to the live codebase.
* It does not self-merge, push, or deploy.
* It does not grant authority or authorize tools.
* It does not create live external effects.

A patch candidate is not applied code. A diff audit is not approval. A
``SAFE_TO_REVIEW`` decision is not merge permission. These boundaries are
enforced structurally here and reused across the module.
"""

from __future__ import annotations

from typing import Any, Mapping

# --- schema ids -------------------------------------------------------------
PATCH_CANDIDATE_REQUEST_SCHEMA = "patch_candidate_request_v1"
PATCH_CANDIDATE_SCHEMA = "patch_candidate_v1"
SANDBOX_PLAN_SCHEMA = "sandbox_plan_v1"
SANDBOX_RECEIPT_SCHEMA = "sandbox_receipt_v1"
PARSED_DIFF_SCHEMA = "parsed_diff_v1"
DIFF_FILE_CHANGE_SCHEMA = "diff_file_change_v1"
DIFF_RISK_CLASSIFICATION_SCHEMA = "diff_risk_classification_v1"
AUTHORITY_BOUNDARY_DIFF_AUDIT_SCHEMA = "authority_boundary_diff_audit_v1"
DRY_LIVE_BOUNDARY_DIFF_AUDIT_SCHEMA = "dry_live_boundary_diff_audit_v1"
TEST_IMPACT_AUDIT_SCHEMA = "test_impact_audit_v1"
ROLLBACK_PLAN_SCHEMA = "rollback_plan_v1"
PATCH_CANDIDATE_DECISION_SCHEMA = "patch_candidate_decision_v1"
PATCH_CANDIDATE_REPLAY_RECORD_SCHEMA = "patch_candidate_replay_record_v1"
PATCH_CANDIDATE_SUMMARY_SCHEMA = "patch_candidate_summary_v1"

# --- verdicts ---------------------------------------------------------------
VERDICT_GREEN = "GREEN_PHASE38_PATCH_CANDIDATE_SANDBOX"
VERDICT_YELLOW = "YELLOW_PHASE38_PATCH_SANDBOX_PARTIAL"
VERDICT_RED = "RED_PHASE38_PATCH_SANDBOX_FAILED"

# --- per-candidate decisions ------------------------------------------------
DECISION_SAFE_TO_REVIEW = "SAFE_TO_REVIEW"
DECISION_NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
DECISION_REJECTED_NOT_READY = "REJECTED_NOT_READY"
DECISION_REJECTED_LIVE_ACTION = "REJECTED_LIVE_ACTION"
DECISION_REJECTED_AUTHORITY_BYPASS = "REJECTED_AUTHORITY_BYPASS"
DECISION_REJECTED_SECRET_RISK = "REJECTED_SECRET_RISK"
DECISION_REJECTED_UNSUPPORTED_PATCH = "REJECTED_UNSUPPORTED_PATCH"
DECISION_REJECTED_SANDBOX_ESCAPE = "REJECTED_SANDBOX_ESCAPE"

REJECTED_DECISIONS = frozenset(
    {
        DECISION_REJECTED_NOT_READY,
        DECISION_REJECTED_LIVE_ACTION,
        DECISION_REJECTED_AUTHORITY_BYPASS,
        DECISION_REJECTED_SECRET_RISK,
        DECISION_REJECTED_UNSUPPORTED_PATCH,
        DECISION_REJECTED_SANDBOX_ESCAPE,
    }
)
# Decisions for which a patch candidate artifact is actually produced.
CANDIDATE_PRODUCING_DECISIONS = frozenset({DECISION_SAFE_TO_REVIEW, DECISION_NEEDS_HUMAN_REVIEW})

# --- sandbox modes ----------------------------------------------------------
SANDBOX_ARTIFACT_ONLY = "ARTIFACT_ONLY"
SANDBOX_DISPOSABLE_COPY = "DISPOSABLE_COPY"

# --- diff risk classes ------------------------------------------------------
RISK_DOC_ONLY = "DOC_ONLY"
RISK_TEST_ONLY = "TEST_ONLY"
RISK_RUNTIME_LOW = "RUNTIME_LOW"
RISK_RUNTIME_MEDIUM = "RUNTIME_MEDIUM"
RISK_AUTHORITY_KERNEL = "AUTHORITY_KERNEL"
RISK_STOP_PANIC = "STOP_PANIC"
RISK_LIVE_EFFECT = "LIVE_EFFECT"
RISK_EXTERNAL_PROVIDER = "EXTERNAL_PROVIDER"
RISK_SECRET_OR_CONFIG = "SECRET_OR_CONFIG"
RISK_BUILD_OR_CI = "BUILD_OR_CI"
RISK_UNKNOWN = "UNKNOWN"

# Risk classes that may never be SAFE_TO_REVIEW without explicit human review.
AUTHORITY_SENSITIVE_RISK_CLASSES = frozenset(
    {
        RISK_AUTHORITY_KERNEL,
        RISK_STOP_PANIC,
        RISK_LIVE_EFFECT,
        RISK_EXTERNAL_PROVIDER,
        RISK_SECRET_OR_CONFIG,
        RISK_BUILD_OR_CI,
    }
)
# Risk classes a doc/test-only safe candidate may consist of.
SAFE_REVIEW_RISK_CLASSES = frozenset({RISK_DOC_ONLY, RISK_TEST_ONLY})

UNKNOWN = "UNKNOWN"

# Phase 37 -> Phase 38 refusal mapping for non-ready source packages.
NOT_READY_DECISION_BY_SOURCE_STATUS = {
    "NOT_READY": DECISION_REJECTED_NOT_READY,
    "LIVE_SELF_BLOCKED": DECISION_REJECTED_LIVE_ACTION,
    "RED_REFUSED": DECISION_REJECTED_AUTHORITY_BYPASS,
}


class SandboxError(ValueError):
    """Phase 38 validation or refusal."""


def neutral_flags() -> dict[str, bool]:
    """Flags every Phase 38 artifact carries to keep it review-prep-only."""
    return {
        "advisory_only": True,
        "sandbox_mode_is_review_preparation_only": True,
        "is_authority": False,
        "is_approval": False,
        "apply_allowed": False,
        "patch_applied_to_live_repo": False,
        "committed": False,
        "pushed": False,
        "deployed": False,
        "created_external_side_effects": False,
        "created_live_posts": False,
        "authority_granted": False,
        "tools_authorized": False,
        "claims_agi": False,
    }


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise SandboxError(f"schema_violation:missing:{','.join(missing)}")


# Fields whose truthiness in an *emitted* Phase 38 artifact would mean the
# sandbox itself applied a patch / went live / granted authority. Artifacts must
# never carry these truthy.
_FORBIDDEN_OUTPUT_FLAGS = {
    "apply_allowed": "sandbox_cannot_allow_apply",
    "patch_applied_to_live_repo": "sandbox_cannot_apply_patch_to_live",
    "patch_applied": "sandbox_cannot_apply_patch_to_live",
    "committed": "sandbox_cannot_commit_candidate_as_implementation",
    "pushed": "sandbox_cannot_push",
    "deployed": "sandbox_cannot_deploy",
    "created_external_side_effects": "sandbox_cannot_create_live_effects",
    "created_live_posts": "sandbox_cannot_create_live_posts",
    "authority_granted": "sandbox_cannot_grant_authority",
    "tools_authorized": "sandbox_cannot_authorize_tools",
    "claims_agi": "sandbox_cannot_claim_agi",
}


def assert_neutral_output(payload: Mapping[str, Any]) -> None:
    """Guard an artifact the sandbox is about to emit: it must stay neutral."""
    for key, value in payload.items():
        if value and str(key) in _FORBIDDEN_OUTPUT_FLAGS:
            raise SandboxError(_FORBIDDEN_OUTPUT_FLAGS[str(key)])
        if isinstance(value, Mapping):
            assert_neutral_output(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral_output(item)


__all__ = [
    "AUTHORITY_BOUNDARY_DIFF_AUDIT_SCHEMA",
    "AUTHORITY_SENSITIVE_RISK_CLASSES",
    "CANDIDATE_PRODUCING_DECISIONS",
    "DECISION_NEEDS_HUMAN_REVIEW",
    "DECISION_REJECTED_AUTHORITY_BYPASS",
    "DECISION_REJECTED_LIVE_ACTION",
    "DECISION_REJECTED_NOT_READY",
    "DECISION_REJECTED_SANDBOX_ESCAPE",
    "DECISION_REJECTED_SECRET_RISK",
    "DECISION_REJECTED_UNSUPPORTED_PATCH",
    "DECISION_SAFE_TO_REVIEW",
    "DIFF_FILE_CHANGE_SCHEMA",
    "DIFF_RISK_CLASSIFICATION_SCHEMA",
    "DRY_LIVE_BOUNDARY_DIFF_AUDIT_SCHEMA",
    "NOT_READY_DECISION_BY_SOURCE_STATUS",
    "PARSED_DIFF_SCHEMA",
    "PATCH_CANDIDATE_DECISION_SCHEMA",
    "PATCH_CANDIDATE_REPLAY_RECORD_SCHEMA",
    "PATCH_CANDIDATE_REQUEST_SCHEMA",
    "PATCH_CANDIDATE_SCHEMA",
    "PATCH_CANDIDATE_SUMMARY_SCHEMA",
    "REJECTED_DECISIONS",
    "RISK_AUTHORITY_KERNEL",
    "RISK_BUILD_OR_CI",
    "RISK_DOC_ONLY",
    "RISK_EXTERNAL_PROVIDER",
    "RISK_LIVE_EFFECT",
    "RISK_RUNTIME_LOW",
    "RISK_RUNTIME_MEDIUM",
    "RISK_SECRET_OR_CONFIG",
    "RISK_STOP_PANIC",
    "RISK_TEST_ONLY",
    "RISK_UNKNOWN",
    "ROLLBACK_PLAN_SCHEMA",
    "SAFE_REVIEW_RISK_CLASSES",
    "SANDBOX_ARTIFACT_ONLY",
    "SANDBOX_DISPOSABLE_COPY",
    "SANDBOX_PLAN_SCHEMA",
    "SANDBOX_RECEIPT_SCHEMA",
    "SandboxError",
    "TEST_IMPACT_AUDIT_SCHEMA",
    "UNKNOWN",
    "VERDICT_GREEN",
    "VERDICT_RED",
    "VERDICT_YELLOW",
    "assert_neutral_output",
    "neutral_flags",
    "require_fields",
]
