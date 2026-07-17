"""Reasoning receipts — durable reasoning audit trail."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_zero_state.redaction import scan_payload
from hg_runtime.agent_zero_reasoning.schema import ReasoningFailure, ReasoningResult, ReasoningVerdict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ReasoningReceipt:
    reasoning_receipt_id: str
    request_id: str
    observe_snapshot_ref: str
    capability_menu_ref: str
    agent_state_ref: str
    prompt_hash: str
    verdict: ReasoningVerdict
    created_at: str
    hash: str = ""
    provider_receipt_ref: str | None = None
    turn_intent_ref: str | None = None
    reasoning_failure_ref: str | None = None
    raw_output_hash: str | None = None
    parsed_output_hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "reasoning_receipt_id": self.reasoning_receipt_id,
            "request_id": self.request_id,
            "provider_receipt_ref": self.provider_receipt_ref,
            "observe_snapshot_ref": self.observe_snapshot_ref,
            "capability_menu_ref": self.capability_menu_ref,
            "agent_state_ref": self.agent_state_ref,
            "turn_intent_ref": self.turn_intent_ref,
            "reasoning_failure_ref": self.reasoning_failure_ref,
            "prompt_hash": self.prompt_hash,
            "raw_output_hash": self.raw_output_hash,
            "parsed_output_hash": self.parsed_output_hash,
            "verdict": self.verdict.value,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ReasoningReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ReasoningReceipt(**{**self.__dict__, "hash": hash_record(body)})


def build_reasoning_receipt_from_result(
    *,
    request_id: str,
    observe_snapshot_ref: str,
    capability_menu_ref: str,
    agent_state_ref: str,
    prompt_hash: str,
    result: ReasoningResult,
) -> ReasoningReceipt:
    rid = f"reason-rcpt-{hash_record({'request_id': request_id, 'result': result.result_id})[7:19]}"
    receipt = ReasoningReceipt(
        reasoning_receipt_id=rid,
        request_id=request_id,
        provider_receipt_ref=result.provider_receipt_ref,
        observe_snapshot_ref=observe_snapshot_ref,
        capability_menu_ref=capability_menu_ref,
        agent_state_ref=agent_state_ref,
        turn_intent_ref=result.turn_intent.intent_id,
        prompt_hash=prompt_hash,
        raw_output_hash=result.raw_model_output_hash,
        parsed_output_hash=result.parsed_output_hash,
        verdict=result.verdict,
        created_at=result.created_at,
    ).with_hash()
    return validate_reasoning_receipt(receipt)


def build_reasoning_receipt_from_failure(
    *,
    request_id: str,
    observe_snapshot_ref: str,
    capability_menu_ref: str,
    agent_state_ref: str,
    prompt_hash: str,
    failure: ReasoningFailure,
) -> ReasoningReceipt:
    rid = f"reason-rcpt-{hash_record({'request_id': request_id, 'failure': failure.failure_id})[7:19]}"
    receipt = ReasoningReceipt(
        reasoning_receipt_id=rid,
        request_id=request_id,
        provider_receipt_ref=failure.provider_receipt_ref,
        observe_snapshot_ref=observe_snapshot_ref,
        capability_menu_ref=capability_menu_ref,
        agent_state_ref=agent_state_ref,
        reasoning_failure_ref=failure.failure_id,
        prompt_hash=prompt_hash,
        verdict=failure.verdict,
        created_at=failure.created_at,
    ).with_hash()
    return validate_reasoning_receipt(receipt)


def validate_reasoning_receipt(receipt: ReasoningReceipt) -> ReasoningReceipt:
    payload = receipt.to_payload()
    has_secret, has_cot = scan_payload(payload)
    if has_secret or has_cot:
        raise ValueError("reasoning receipt contains secret or hidden cot")
    if not receipt.hash or not verify_record_hash({k: v for k, v in payload.items() if k != "hash"}, receipt.hash):
        raise ValueError("reasoning receipt hash invalid")
    if receipt.verdict == ReasoningVerdict.GREEN_REASONING_INTENT_VALID:
        if not receipt.provider_receipt_ref or not receipt.turn_intent_ref:
            raise ValueError("green reasoning receipt requires provider and intent refs")
    return receipt


__all__ = [
    "ReasoningReceipt",
    "build_reasoning_receipt_from_failure",
    "build_reasoning_receipt_from_result",
    "validate_reasoning_receipt",
]
