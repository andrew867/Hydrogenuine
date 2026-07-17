"""Evidence policy receipts.

An evidence policy receipt declares what evidence would be required *later* to
verify a claim of a given kind. It explicitly states that model output, model
consensus, model refusal, and queued tasks are NOT evidence, and that tool
authorization is required before any execution.
"""

from __future__ import annotations

from hg_runtime.belief_verification_queue.schemas import (
    EVIDENCE_POLICY_RECEIPT_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

_ACCEPTABLE = {
    "FACTUAL": ["PRIMARY_SOURCE", "OFFICIAL_RECORD", "DIRECT_MEASUREMENT", "PEER_REVIEWED"],
    "HISTORICAL": ["PRIMARY_SOURCE", "ARCHIVAL_RECORD", "PEER_REVIEWED"],
    "MORAL": ["EXPLICIT_OPERATOR_VALUE_DECISION", "DOCUMENTED_POLICY"],
    "POLICY": ["OFFICIAL_POLICY_DOCUMENT", "PRIMARY_SOURCE"],
    "TECHNICAL": ["REPRODUCIBLE_TEST", "PRIMARY_SOURCE", "SPECIFICATION"],
    "UNCERTAIN": ["PRIMARY_SOURCE", "CROSS_REFERENCED_SOURCES"],
}

_UNACCEPTABLE = [
    "MODEL_OUTPUT",
    "MODEL_CONSENSUS",
    "MODEL_REFUSAL",
    "MODEL_WILLINGNESS",
    "QUEUE_TASK",
    "SOCIAL_MEDIA_RUMOR",
    "UNSOURCED_ASSERTION",
]


def build_evidence_policy_receipts(claim_kinds: list[str]) -> list[dict]:
    receipts: list[dict] = []
    for kind in sorted(set(claim_kinds)):
        receipt = {
            "schema": EVIDENCE_POLICY_RECEIPT_SCHEMA,
            "policy_id": f"evpolicy-{kind.lower()}",
            "claim_kind": kind,
            "acceptable_evidence_types": _ACCEPTABLE.get(kind, ["PRIMARY_SOURCE"]),
            "unacceptable_evidence_types": list(_UNACCEPTABLE),
            "model_output_is_evidence": False,
            "model_consensus_is_evidence": False,
            "model_refusal_is_evidence": False,
            "queue_task_is_evidence": False,
            "tool_authorization_required_for_execution": True,
            **neutral_flags(),
        }
        receipt["receipt_hash"] = canonical_hash(receipt)
        receipts.append(receipt)
    return receipts
