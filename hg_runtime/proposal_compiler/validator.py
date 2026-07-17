"""Phase 37 readiness classification and refusal logic.

Decides, for a normalized proposal, whether it compiles to a full READY work
package or to a diagnostic-only package. This is the gate that prevents
garbage-in / enterprise-docs-out and that refuses any proposal trying to grant
authority, authorize tools, go live, or claim the fix is already done.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.autonomous_proposal_soak.proposal_schema import score_proposal
from hg_runtime.proposal_compiler.schemas import (
    STATUS_LIVE_BLOCKED,
    STATUS_NOT_READY,
    STATUS_READY,
    STATUS_REFUSED,
    UNKNOWN,
)

_LIVE_ACTION_MARKERS = (
    "post to",
    "publish",
    "upload",
    "deploy",
    "self-merge",
    "merge to main",
    "merge to master",
    "push to origin",
    "git push",
    "send email",
    "tweet",
    "social media",
    "moltbook",
    "go live",
    "live field trial",
    "call the external api",
    "external provider",
)
_AUTHORITY_MARKERS = (
    "grant authority",
    "grant me authority",
    "grant the agent authority",
    "authorize the tool",
    "authorize tool",
    "bypass permission",
    "bypass the permission",
    "bypass the gate",
    "disable the gate",
    "escalate privilege",
    "skip approval",
    "self-authorize",
    "self authorize",
    "give it tool access",
)
_IMPLEMENTED_MARKERS = (
    "already implemented",
    "already applied",
    "patch has been applied",
    "patch was applied",
    "fix is already",
    "already deployed",
    "already merged",
    "implementation is complete and live",
    "i implemented the fix",
    "we implemented the fix",
)

_AUTHORITY_FLAGS = ("grants_authority", "grant_authority", "authorizes_tool", "authorize_tool", "requests_authority", "requests_tool_authorization")
_LIVE_FLAGS = ("requests_live_effect", "creates_live_effect", "create_live_effect", "live_action", "requests_external_post")
_IMPLEMENTED_FLAGS = ("claims_implemented", "implementation_complete", "patch_applied", "already_applied")


def _text_blob(payload: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for value in payload.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
    return "\n".join(parts).lower()


def _flag_or_marker(payload: Mapping[str, Any], flags: tuple[str, ...], markers: tuple[str, ...]) -> list[str]:
    hits = [flag for flag in flags if payload.get(flag)]
    blob = _text_blob(payload)
    hits.extend(marker for marker in markers if marker in blob)
    return hits


def missing_readiness_fields(payload: Mapping[str, Any], scored: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    if not payload.get("evidence_refs"):
        missing.append("evidence_refs")
    if not payload.get("affected_files"):
        missing.append("affected_files")
    if not payload.get("affected_tests"):
        missing.append("affected_tests")
    if not payload.get("reproduction_steps"):
        missing.append("reproduction_steps")
    if not scored.get("testable_acceptance_criteria_present"):
        missing.append("testable_acceptance_criteria")
    if str(payload.get("authority_risk", UNKNOWN)).strip().upper() == UNKNOWN:
        missing.append("authority_risk")
    if not str(payload.get("dry_live_boundary", "")).strip():
        missing.append("dry_live_boundary")
    if scored.get("specificity_score", 0) < 8:
        missing.append("specificity_score_below_threshold")
    if scored.get("genericity_score", 99) > 3:
        missing.append("genericity_score_above_threshold")
    if scored.get("truncated"):
        missing.append("non_truncated_output")
    return missing


def classify_proposal(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Classify a normalized proposal into READY / NOT_READY / LIVE / REFUSED.

    Precedence: authority-bypass and fake-implementation claims are refused
    (RED) outright; live-effect requests are self-blocked; otherwise the P36
    specificity/grounding score plus explicit authority + dry/live boundary
    determine READY vs NOT_READY.
    """
    authority_hits = _flag_or_marker(payload, _AUTHORITY_FLAGS, _AUTHORITY_MARKERS)
    implemented_hits = _flag_or_marker(payload, _IMPLEMENTED_FLAGS, _IMPLEMENTED_MARKERS)
    live_hits = _flag_or_marker(payload, _LIVE_FLAGS, _LIVE_ACTION_MARKERS)
    scored = score_proposal(payload)
    missing = missing_readiness_fields(payload, scored)

    if authority_hits:
        status, reason = STATUS_REFUSED, "authority_bypass_attempt_refused"
    elif implemented_hits:
        status, reason = STATUS_REFUSED, "claims_implementation_already_happened_refused"
    elif live_hits:
        status, reason = STATUS_LIVE_BLOCKED, "live_external_effect_self_blocked"
    elif scored.get("ready_for_spec_tests_plans") and not missing:
        status, reason = STATUS_READY, "ready_for_spec_tests_plans"
    else:
        status, reason = STATUS_NOT_READY, "not_ready_low_specificity_or_ungrounded"

    return {
        "status": status,
        "reason": reason,
        "authority_bypass_hits": authority_hits,
        "implemented_claim_hits": implemented_hits,
        "live_action_hits": live_hits,
        "missing_fields": missing,
        "score": scored,
    }


__all__ = ["classify_proposal", "missing_readiness_fields"]
