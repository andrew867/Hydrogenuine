"""Build queued verification tasks from belief conflicts.

A verification task REQUESTS future evidence acquisition. It is QUEUED and NOT
authorized: it is not an action, it authorizes no tools, and it authorizes no
external calls. A source request is not an external call.
"""

from __future__ import annotations

from hg_runtime.belief_verification_queue.priority import compute_priority
from hg_runtime.belief_verification_queue.schemas import (
    TASK_STATUS_QUEUED,
    VERIFICATION_TASK_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

CONFLICT_TO_TASK_TYPE = {
    "UNSOURCED_CONSENSUS": "PRIMARY_SOURCE_REQUEST",
    "FACTUAL_DIVERGENCE": "SOURCE_CHECK",
    "FRAMING_DIVERGENCE": "POLICY_CONTEXT_CHECK",
    "REFUSAL_DIVERGENCE": "CROSS_REFERENCE_REQUEST",
    "OMISSION_DIVERGENCE": "CROSS_REFERENCE_REQUEST",
    "MORAL_CONFLICT": "POLICY_CONTEXT_CHECK",
}

_RATIONALE = {
    "UNSOURCED_CONSENSUS": "Request a primary source; shared model claims are not truth.",
    "FACTUAL_DIVERGENCE": "Check sources for divergent factual claims; divergence is not evidence.",
    "FRAMING_DIVERGENCE": "Acquire context to compare framings; framing is descriptive only.",
    "REFUSAL_DIVERGENCE": "Cross-reference independent of model refusal; refusal is not authority.",
    "OMISSION_DIVERGENCE": "Cross-reference whether the omitted claim holds; omission is not proof.",
    "MORAL_CONFLICT": "Gather policy/value context; moral consensus is not authority.",
}


def _claim_ids_for_conflict(conflict: dict, claims: list[dict]) -> list[str]:
    receipt_ids = set(conflict.get("source_receipt_ids", []))
    claim_ref = conflict.get("claim_text_or_hash", "")
    matched: list[str] = []
    for claim in claims:
        if claim["source_receipt_id"] in receipt_ids:
            matched.append(claim["claim_id"])
        elif claim_ref.startswith("claim_tag:") and claim["claim_tag"] == claim_ref.split("claim_tag:", 1)[1]:
            matched.append(claim["claim_id"])
        elif claim_ref.startswith("prompt:") and claim["source_prompt_id"] == claim_ref.split("prompt:", 1)[1].split("|")[0]:
            matched.append(claim["claim_id"])
    return sorted(set(matched))


def build_verification_task(conflict: dict, claims: list[dict]) -> dict:
    conflict_type = conflict["conflict_type"]
    task = {
        "schema": VERIFICATION_TASK_SCHEMA,
        "task_id": f"vtask-{conflict['conflict_id']}",
        "source_conflict_id": conflict["conflict_id"],
        "source_claim_ids": _claim_ids_for_conflict(conflict, claims),
        "task_type": CONFLICT_TO_TASK_TYPE.get(conflict_type, "SOURCE_CHECK"),
        "task_status": TASK_STATUS_QUEUED,
        "priority": compute_priority(conflict),
        "rationale": _RATIONALE.get(conflict_type, "Request evidence; model output is not evidence."),
        # Hard boundaries — a queued task is not permission to do anything.
        "tool_authorized": False,
        "action_authorized": False,
        "external_call_authorized": False,
        "verification_task_treated_as_action": False,
        "source_request_treated_as_external_call": False,
        **neutral_flags(),
    }
    task["task_hash"] = canonical_hash(task)
    return task


def build_verification_tasks(conflicts: list[dict], claims: list[dict]) -> list[dict]:
    tasks = [build_verification_task(c, claims) for c in conflicts]
    return sorted(tasks, key=lambda t: (-t["priority"], t["task_id"]))
