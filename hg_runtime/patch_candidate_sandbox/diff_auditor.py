"""Phase 38 diff auditor.

Given a parsed diff, produces the deterministic audits an operator needs to
review a patch candidate: risk classification, authority-boundary audit,
dry/live-boundary audit, test-impact audit, secret-leakage scan, and a rollback
plan; then derives a diff-level decision. It is pure analysis: nothing is
applied, committed, or executed.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.proposal_compiler.input_loader import contains_secret
from hg_runtime.patch_candidate_sandbox.risk_classifier import classify_changed_files
from hg_runtime.patch_candidate_sandbox.schemas import (
    AUTHORITY_BOUNDARY_DIFF_AUDIT_SCHEMA,
    DECISION_NEEDS_HUMAN_REVIEW,
    DECISION_REJECTED_AUTHORITY_BYPASS,
    DECISION_REJECTED_LIVE_ACTION,
    DECISION_REJECTED_SANDBOX_ESCAPE,
    DECISION_REJECTED_SECRET_RISK,
    DECISION_REJECTED_UNSUPPORTED_PATCH,
    DECISION_SAFE_TO_REVIEW,
    DRY_LIVE_BOUNDARY_DIFF_AUDIT_SCHEMA,
    RISK_AUTHORITY_KERNEL,
    RISK_DOC_ONLY,
    RISK_EXTERNAL_PROVIDER,
    RISK_LIVE_EFFECT,
    RISK_STOP_PANIC,
    ROLLBACK_PLAN_SCHEMA,
    SAFE_REVIEW_RISK_CLASSES,
    TEST_IMPACT_AUDIT_SCHEMA,
)


def _scan_secrets(files: list[Mapping[str, Any]]) -> dict[str, Any]:
    hits: list[str] = []
    for change in files:
        for line in change.get("added_content", []):
            if contains_secret(line):
                hits.append(change.get("path", ""))
                break
    return {"secret_leakage_detected": bool(hits), "files_with_secret_risk": sorted(set(hits))}


def _authority_boundary_audit(classification: Mapping[str, Any]) -> dict[str, Any]:
    risk_classes = classification["risk_classes"]
    markers = classification["authority_bypass_markers"]
    return {
        "schema": AUTHORITY_BOUNDARY_DIFF_AUDIT_SCHEMA,
        "touches_authority_paths": any(rc in (RISK_AUTHORITY_KERNEL, RISK_STOP_PANIC) for rc in risk_classes),
        "authority_bypass_markers": list(markers),
        "authority_bypass_detected": bool(markers),
        "authority_granted": False,
        "tools_authorized": False,
    }


def _dry_live_boundary_audit(classification: Mapping[str, Any]) -> dict[str, Any]:
    risk_classes = classification["risk_classes"]
    markers = classification["live_effect_markers"]
    return {
        "schema": DRY_LIVE_BOUNDARY_DIFF_AUDIT_SCHEMA,
        "touches_live_paths": any(rc in (RISK_LIVE_EFFECT, RISK_EXTERNAL_PROVIDER) for rc in risk_classes),
        "live_effect_markers": list(markers),
        "live_effect_enabled_by_default_detected": bool(markers),
        "created_external_side_effects": False,
        "created_live_posts": False,
    }


def _test_impact_audit(files: list[Mapping[str, Any]], per_file: list[Mapping[str, Any]]) -> dict[str, Any]:
    from hg_runtime.patch_candidate_sandbox.schemas import RISK_TEST_ONLY

    test_files = [f["path"] for f in per_file if f["risk_class"] == RISK_TEST_ONLY]
    runtime_files = [f["path"] for f in per_file if f["risk_class"] not in (RISK_DOC_ONLY, RISK_TEST_ONLY)]
    return {
        "schema": TEST_IMPACT_AUDIT_SCHEMA,
        "test_files_changed": test_files,
        "touches_tests": bool(test_files),
        "runtime_files_changed": runtime_files,
        "requires_test_run": bool(runtime_files) or bool(test_files),
    }


def _rollback_plan(sandbox_mode: str) -> dict[str, Any]:
    return {
        "schema": ROLLBACK_PLAN_SCHEMA,
        "strategy": "DISCARD_CANDIDATE_ARTIFACT_NO_LIVE_STATE_TO_REVERT",
        "steps": [
            "No live source path was modified; nothing to revert in the working tree.",
            "Delete the candidate artifact directory under the Phase 38 proof/artifact root.",
            "Re-run the Phase 38 gate to confirm a clean tree.",
        ],
        "reversible": True,
        "live_state_modified": False,
        "sandbox_mode": sandbox_mode,
    }


def audit_diff(parsed_diff: Mapping[str, Any], sandbox_mode: str) -> dict[str, Any]:
    """Audit a parsed diff and derive the diff-level decision (no application)."""
    files = list(parsed_diff.get("files", []))
    classification = classify_changed_files(files)
    per_file = classification["per_file"]
    risk_classes = classification["risk_classes"]

    secret = _scan_secrets(files)
    authority_audit = _authority_boundary_audit(classification)
    dry_live_audit = _dry_live_boundary_audit(classification)
    test_audit = _test_impact_audit(files, per_file)
    rollback = _rollback_plan(sandbox_mode)

    # Decision precedence: most severe boundary violation first.
    if not parsed_diff.get("parseable") or not files:
        decision = DECISION_REJECTED_UNSUPPORTED_PATCH
    elif classification["sandbox_escape_reasons"]:
        decision = DECISION_REJECTED_SANDBOX_ESCAPE
    elif secret["secret_leakage_detected"]:
        decision = DECISION_REJECTED_SECRET_RISK
    elif classification["authority_bypass_markers"]:
        decision = DECISION_REJECTED_AUTHORITY_BYPASS
    elif classification["live_effect_markers"]:
        decision = DECISION_REJECTED_LIVE_ACTION
    elif risk_classes and all(rc in SAFE_REVIEW_RISK_CLASSES for rc in risk_classes):
        decision = DECISION_SAFE_TO_REVIEW
    else:
        # Includes authority-sensitive paths touched without explicit bypass intent:
        # never SAFE_TO_REVIEW, always escalated to a human.
        decision = DECISION_NEEDS_HUMAN_REVIEW

    operator_review_required = any(rc != RISK_DOC_ONLY for rc in risk_classes) or decision != DECISION_SAFE_TO_REVIEW

    return {
        "decision": decision,
        "operator_review_required": operator_review_required,
        "classification": classification,
        "risk_classes": risk_classes,
        "changed_files": parsed_diff.get("changed_paths", []),
        "secret_leakage": secret,
        "authority_boundary_audit": authority_audit,
        "dry_live_boundary_audit": dry_live_audit,
        "test_impact_audit": test_audit,
        "rollback_plan": rollback,
    }


__all__ = ["audit_diff"]
