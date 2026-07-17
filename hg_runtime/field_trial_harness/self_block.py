"""Live-effect detection and self-blocking for Phase 35."""

from __future__ import annotations

import re
from typing import Any, Mapping

from hg_runtime.field_trial_harness.schemas import (
    DRY_RUN_ALLOWED,
    INSUFFICIENT_EVIDENCE_REFUSED,
    LIVE_SELF_BLOCKED,
    OUT_OF_SCOPE_REFUSED,
    SAFETY_REFUSED,
    FIELD_TRIAL_SELF_BLOCK_RECORD_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

LIVE_MARKERS = (
    "moltbook",
    "social post",
    "social media",
    "publish",
    "upload",
    "send email",
    "external api",
    "external service",
    "git push",
    "deployment",
    "deploy",
    "browser post",
    "exfiltration",
    "live oea",
    "live ueak",
    "post to",
)

FORBIDDEN_30B = ("30b", "30-b", "qwen3-coder-30b")
FORBIDDEN_SECURITY = ("cybersecurity", "offensive", "security model", "pentest", "exploit")
FORBIDDEN_DEEPSEEK = ("deepseek", "deepseek-coder")

GENERIC_MARKERS = (
    "generic review",
    "check dependencies",
    "update software",
    "document findings",
    "without evidence",
    "generic advice",
)


def _text(candidate: Mapping[str, Any]) -> str:
    parts = [str(candidate.get("candidate_id", "")), str(candidate.get("description", ""))]
    if candidate.get("model_hint"):
        parts.append(str(candidate["model_hint"]))
    return " ".join(parts).lower()


def detect_live_effect(candidate: Mapping[str, Any]) -> bool:
    cid = str(candidate.get("candidate_id", "")).upper()
    if cid in {"MOCK_SOCIAL_POST", "MOCK_EXTERNAL_API_CALL", "GIT_PUSH_REQUEST", "MOCK_MOLTBOOK_POST"}:
        return True
    text = _text(candidate)
    return any(marker in text for marker in LIVE_MARKERS)


def detect_safety_refusal(candidate: Mapping[str, Any]) -> str | None:
    text = _text(candidate)
    cid = str(candidate.get("candidate_id", "")).upper()
    if cid == "LOAD_30B_MODEL" or any(m in text for m in FORBIDDEN_30B):
        return "forbidden_large_30b_model"
    if cid == "SECURITY_MODEL_TOOL_TASK" or any(m in text for m in FORBIDDEN_SECURITY):
        return "forbidden_security_offensive_model"
    if any(m in text for m in FORBIDDEN_DEEPSEEK):
        return "forbidden_deepseek_model"
    return None


def detect_insufficient_evidence(candidate: Mapping[str, Any]) -> bool:
    cid = str(candidate.get("candidate_id", "")).upper()
    if cid == "GENERIC_UNGROUNDED_REPAIR":
        return True
    refs = candidate.get("evidence_refs") or []
    text = _text(candidate)
    if not refs and any(m in text for m in GENERIC_MARKERS):
        return True
    if "without evidence" in text and not refs:
        return True
    return False


def detect_out_of_scope(candidate: Mapping[str, Any]) -> bool:
    scope = str(candidate.get("scope", "")).lower()
    return scope in {"forbidden", "out_of_scope"}


def classify_candidate(candidate: Mapping[str, Any]) -> tuple[str, str, bool, bool, bool]:
    """Return final_decision, reason, live_effect, self_blocked, operator_permit_required."""
    if detect_out_of_scope(candidate):
        return OUT_OF_SCOPE_REFUSED, "candidate_out_of_scope", False, True, False

    safety = detect_safety_refusal(candidate)
    if safety:
        return SAFETY_REFUSED, safety, False, True, False

    if detect_insufficient_evidence(candidate):
        return INSUFFICIENT_EVIDENCE_REFUSED, "insufficient_evidence_or_generic_ungrounded", False, True, False

    if detect_live_effect(candidate):
        return LIVE_SELF_BLOCKED, "live_external_effect_requires_operator_permit", True, True, True

    return DRY_RUN_ALLOWED, "local_dry_run_only_no_live_effects", False, False, False


def self_block_record(
    candidate: Mapping[str, Any],
    *,
    final_decision: str,
    reason: str,
    live_effect_detected: bool,
    self_blocked: bool,
    operator_permit_required: bool,
) -> dict[str, Any]:
    record = {
        "schema": FIELD_TRIAL_SELF_BLOCK_RECORD_SCHEMA,
        "candidate_id": candidate.get("candidate_id"),
        "candidate_hash": candidate.get("candidate_hash"),
        "final_decision": final_decision,
        "reason": reason,
        "live_effect_detected": live_effect_detected,
        "self_blocked": self_blocked,
        "operator_permit_required": operator_permit_required,
        **neutral_flags(),
    }
    record["live_effect_detected"] = live_effect_detected
    record["self_blocked"] = self_blocked
    record["operator_permit_required"] = operator_permit_required
    record["record_hash"] = canonical_hash(record)
    return record


def reject_fake_green_live_candidate(candidate: Mapping[str, Any]) -> None:
    if candidate.get("claim_live_green") or candidate.get("force_live_execution"):
        raise ValueError("fake_green_live_candidate_rejected")


__all__ = [
    "classify_candidate",
    "detect_insufficient_evidence",
    "detect_live_effect",
    "detect_safety_refusal",
    "reject_fake_green_live_candidate",
    "self_block_record",
]
