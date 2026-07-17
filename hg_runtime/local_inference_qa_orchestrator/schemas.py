"""Local Inference QA Orchestrator schemas."""

from __future__ import annotations

import hashlib
import json

VERDICT_GREEN = "GREEN_LOCAL_INFERENCE_QA_ORCHESTRATOR_PASS"
VERDICT_YELLOW = "YELLOW_LOCAL_QA_ORCHESTRATOR_PROVIDER_UNAVAILABLE"
VERDICT_RED = "RED_LOCAL_INFERENCE_QA_ORCHESTRATOR_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class QAOrchestratorError(Exception):
    pass


BLOCKED_KEYS = (
    "live_effect", "tool_authorized", "external_provider_enabled",
    "customer_contacted", "social_post_published", "message_sent",
    "money_movement", "real_payment", "invoice_created",
    "patch_applied", "authority_mutated", "hg_local_touched",
    "phase19_green_claimed", "phase24_full_overnight_green_claimed",
    "claims_agi", "claims_consciousness", "claims_sovereignty",
    "deployment_permission_claimed", "live_field_trial_authorized",
    "self_modification", "web_browse_performed",
    "containment_bypassed", "correction_resisted",
    "test_created_from_model_output", "green_inferred_from_model_output",
)


def reject_qa_overreach(payload: dict) -> None:
    for key in BLOCKED_KEYS:
        if payload.get(key):
            raise QAOrchestratorError(
                f"QA orchestrator boundary violation: {key} must not be truthy"
            )


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
