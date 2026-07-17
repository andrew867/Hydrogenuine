"""TurnReceipt — record of what happened during a turn."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_zero_state.redaction import scan_payload
from hg_runtime.agent_zero_state.state import load_turn_state_policy
from hg_runtime.agent_zero_state.types import TurnReceiptVerdict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TurnReceipt:
    receipt_id: str
    agent_id: str
    turn_index: int
    turn_started_at: str
    turn_finished_at: str
    runtime_mode: str
    observe_snapshot_ref: str
    capability_menu_ref: str
    chosen_action: str
    action_status: str
    external_side_effect: bool
    published: bool
    sent: bool
    fixture_used: bool
    dry_run_used: bool
    proof_replay_used: bool
    hidden_cot_stored: bool
    secrets_stored: bool
    verdict: TurnReceiptVerdict
    hash: str = ""
    run_id: str | None = None
    turn_intent_ref: str | None = None
    action_result_ref: str | None = None
    provider_receipt_refs: list[str] = field(default_factory=list)
    live_read_receipt_refs: list[str] = field(default_factory=list)
    witness_receipt_ref: str | None = None
    failure_posture_ref: str | None = None
    scope_request_refs: list[str] = field(default_factory=list)
    operator_question_refs: list[str] = field(default_factory=list)
    broker_decision_ref: str | None = None
    output_quality_ref: str | None = None
    previous_turn_hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "turn_started_at": self.turn_started_at,
            "turn_finished_at": self.turn_finished_at,
            "runtime_mode": self.runtime_mode,
            "observe_snapshot_ref": self.observe_snapshot_ref,
            "capability_menu_ref": self.capability_menu_ref,
            "turn_intent_ref": self.turn_intent_ref,
            "chosen_action": self.chosen_action,
            "action_status": self.action_status,
            "action_result_ref": self.action_result_ref,
            "provider_receipt_refs": list(self.provider_receipt_refs),
            "live_read_receipt_refs": list(self.live_read_receipt_refs),
            "witness_receipt_ref": self.witness_receipt_ref,
            "failure_posture_ref": self.failure_posture_ref,
            "scope_request_refs": list(self.scope_request_refs),
            "operator_question_refs": list(self.operator_question_refs),
            "broker_decision_ref": self.broker_decision_ref,
            "output_quality_ref": self.output_quality_ref,
            "external_side_effect": self.external_side_effect,
            "published": self.published,
            "sent": self.sent,
            "fixture_used": self.fixture_used,
            "dry_run_used": self.dry_run_used,
            "proof_replay_used": self.proof_replay_used,
            "hidden_cot_stored": self.hidden_cot_stored,
            "secrets_stored": self.secrets_stored,
            "verdict": self.verdict.value,
            "hash": self.hash,
            "previous_turn_hash": self.previous_turn_hash,
        }

    def with_hash(self) -> TurnReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return TurnReceipt(**{**self.__dict__, "hash": hash_record(body)})


def build_turn_receipt(
    *,
    agent_id: str,
    turn_index: int,
    runtime_mode: str,
    observe_snapshot_ref: str,
    capability_menu_ref: str,
    chosen_action: str,
    action_status: str = "completed",
    provider_receipt_refs: list[str] | None = None,
    live_read_receipt_refs: list[str] | None = None,
    turn_intent_ref: str | None = None,
    witness_receipt_ref: str | None = None,
    failure_posture_ref: str | None = None,
    scope_request_refs: list[str] | None = None,
    operator_question_refs: list[str] | None = None,
    run_id: str | None = None,
    previous_turn_hash: str | None = None,
    turn_started_at: str | None = None,
    turn_finished_at: str | None = None,
    receipt_id: str | None = None,
) -> tuple[TurnReceiptVerdict, TurnReceipt]:
    """Build turn receipt with Phase 5 safety invariants."""
    started = turn_started_at or _now_iso()
    finished = turn_finished_at or _now_iso()
    prov_refs = list(provider_receipt_refs or [])
    live_refs = list(live_read_receipt_refs or [])

    verdict = TurnReceiptVerdict.GREEN_TURN_RECEIPT_VALID
    if chosen_action in ("rest_turn",):
        verdict = TurnReceiptVerdict.YELLOW_TURN_RESTED
    elif chosen_action in ("witness_turn",):
        verdict = TurnReceiptVerdict.YELLOW_TURN_WITNESS_ONLY
    if not observe_snapshot_ref:
        verdict = TurnReceiptVerdict.RED_TURN_WITHOUT_OBSERVE
    if not agent_id or not chosen_action:
        verdict = TurnReceiptVerdict.RED_TURN_EMPTY
    if prov_refs and not all(prov_refs):
        verdict = TurnReceiptVerdict.RED_TURN_WITHOUT_RECEIPT_REFS
    if live_refs and not all(live_refs):
        verdict = TurnReceiptVerdict.RED_TURN_WITHOUT_RECEIPT_REFS

    receipt = TurnReceipt(
        receipt_id=receipt_id or f"turn-rcpt-{uuid.uuid4().hex[:16]}",
        agent_id=agent_id,
        run_id=run_id,
        turn_index=turn_index,
        turn_started_at=started,
        turn_finished_at=finished,
        runtime_mode=runtime_mode,
        observe_snapshot_ref=observe_snapshot_ref,
        capability_menu_ref=capability_menu_ref,
        turn_intent_ref=turn_intent_ref,
        chosen_action=chosen_action,
        action_status=action_status,
        provider_receipt_refs=prov_refs,
        live_read_receipt_refs=live_refs,
        witness_receipt_ref=witness_receipt_ref,
        failure_posture_ref=failure_posture_ref,
        scope_request_refs=list(scope_request_refs or []),
        operator_question_refs=list(operator_question_refs or []),
        external_side_effect=False,
        published=False,
        sent=False,
        fixture_used=False,
        dry_run_used=False,
        proof_replay_used=False,
        hidden_cot_stored=False,
        secrets_stored=False,
        verdict=verdict,
        previous_turn_hash=previous_turn_hash,
    ).with_hash()
    return validate_turn_receipt(receipt)


def validate_turn_receipt(receipt: TurnReceipt) -> tuple[TurnReceiptVerdict, TurnReceipt]:
    payload = receipt.to_payload()
    has_secret, has_cot = scan_payload(payload)
    if has_secret or receipt.secrets_stored:
        return TurnReceiptVerdict.RED_TURN_SECRET_STORED, receipt
    if has_cot or receipt.hidden_cot_stored:
        return TurnReceiptVerdict.RED_TURN_COT_STORED, receipt
    if receipt.external_side_effect or receipt.published or receipt.sent:
        return TurnReceiptVerdict.RED_TURN_EXTERNAL_SIDE_EFFECT, receipt
    if not receipt.hash:
        return TurnReceiptVerdict.RED_TURN_HASH_MISSING, receipt
    if not verify_record_hash({k: v for k, v in payload.items() if k != "hash"}, receipt.hash):
        return TurnReceiptVerdict.RED_TURN_HASH_MISSING, receipt
    if not receipt.observe_snapshot_ref:
        return TurnReceiptVerdict.RED_TURN_WITHOUT_OBSERVE, receipt
    policy = load_turn_state_policy()
    # Enforce the chain-linkage promise (previously declared in
    # turn_state_policy.json but never read — morning hardening 2026-07-03).
    # Engine genesis semantics: the first turn of a run is turn_index 1 (initial
    # state 0 + 1) and legitimately carries a null previous_turn_hash; every turn
    # AFTER the first must chain.
    if policy.get("previous_turn_hash_required_after_first_turn") \
            and receipt.turn_index > 1 and receipt.previous_turn_hash is None:
        return TurnReceiptVerdict.RED_TURN_CHAIN_BROKEN, receipt
    if policy.get("fixture_runtime_state_allowed") is False and receipt.fixture_used:
        if receipt.runtime_mode != "fixture":
            return TurnReceiptVerdict.RED_TURN_FIXTURE_RUNTIME, receipt
    if receipt.verdict == TurnReceiptVerdict.GREEN_TURN_RECEIPT_VALID:
        if not receipt.agent_id or not receipt.chosen_action:
            return TurnReceiptVerdict.RED_TURN_EMPTY, receipt
    return receipt.verdict, receipt


__all__ = ["TurnReceipt", "build_turn_receipt", "validate_turn_receipt"]
