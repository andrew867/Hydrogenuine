"""Internal dispatch — safe read-only and local content handlers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_zero_state.redaction import scan_payload
from hg_runtime.agent_zero_state.turn_intent import TurnIntent
from hg_runtime.capability_broker.schema import BrokerDecision
from hg_runtime.agent_turn_engine.errors import AgentTurnDispatchError
from hg_runtime.agent_turn_engine.schema import PHASE_9_CONTENT_ACTIONS, PHASE_9_IMPLEMENTED_ACTIONS
from hg_runtime.agent_turn_engine.turn_storage import dispatch_dir, write_json
from hg_runtime.output_artifacts.artifact_store import ArtifactStore
from hg_runtime.output_artifacts.artifacts import (
    build_draft_artifact,
    build_notes_artifact,
    build_thread_continuation_artifact,
)
from hg_runtime.output_artifacts.output_quality import evaluate_output_quality
from hg_runtime.output_artifacts.review_candidates import create_review_candidate, should_queue_for_review
from hg_runtime.output_artifacts.schema import ArtifactKind, ArtifactStatus
from hg_runtime.output_artifacts.source_binding import bind_sources

FORBIDDEN_DISPATCH_ACTIONS = frozenset({
    "publish",
    "send",
    "reply_live",
    "comment_live",
    "browser_submit",
    "login",
    "purchase",
    "hardware_actuate",
    "shell_exec",
    "external_execute",
})

PHASE_9_CONTENT_ACTION_IDS = PHASE_9_CONTENT_ACTIONS


class InternalDispatchVerdict(str, Enum):
    GREEN_INTERNAL_DISPATCH_COMPLETE = "GREEN_INTERNAL_DISPATCH_COMPLETE"
    YELLOW_INTERNAL_DISPATCH_READ_ONLY = "YELLOW_INTERNAL_DISPATCH_READ_ONLY"
    YELLOW_INTERNAL_DISPATCH_CONTENT_DEFERRED = "YELLOW_INTERNAL_DISPATCH_CONTENT_DEFERRED"
    YELLOW_INTERNAL_DISPATCH_BODY_MISSING = "YELLOW_INTERNAL_DISPATCH_BODY_MISSING"
    RED_INTERNAL_DISPATCH_UNSUPPORTED = "RED_INTERNAL_DISPATCH_UNSUPPORTED"
    RED_INTERNAL_DISPATCH_EXTERNAL_SIDE_EFFECT = "RED_INTERNAL_DISPATCH_EXTERNAL_SIDE_EFFECT"
    RED_INTERNAL_DISPATCH_QUALITY_FAILED = "RED_INTERNAL_DISPATCH_QUALITY_FAILED"
    RED_INTERNAL_DISPATCH_SECRET_LEAK = "RED_INTERNAL_DISPATCH_SECRET_LEAK"
    RED_INTERNAL_DISPATCH_COT_LEAK = "RED_INTERNAL_DISPATCH_COT_LEAK"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class InternalDispatchResult:
    dispatch_result_id: str
    dispatch_id: str
    action_id: str
    verdict: InternalDispatchVerdict
    artifact_ref: str | None
    external_side_effect: bool
    created_at: str
    hash: str = ""
    witness_receipt_ref: str | None = None
    scope_request_refs: list[str] = field(default_factory=list)
    operator_question_refs: list[str] = field(default_factory=list)
    output_artifact_ref: str | None = None
    quality_receipt_ref: str | None = None
    review_candidate_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "dispatch_result_id": self.dispatch_result_id,
            "dispatch_id": self.dispatch_id,
            "action_id": self.action_id,
            "verdict": self.verdict.value,
            "artifact_ref": self.artifact_ref,
            "output_artifact_ref": self.output_artifact_ref,
            "quality_receipt_ref": self.quality_receipt_ref,
            "review_candidate_ref": self.review_candidate_ref,
            "witness_receipt_ref": self.witness_receipt_ref,
            "scope_request_refs": list(self.scope_request_refs),
            "operator_question_refs": list(self.operator_question_refs),
            "external_side_effect": self.external_side_effect,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> InternalDispatchResult:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return InternalDispatchResult(**{**self.__dict__, "hash": hash_record(body)})


def _validate_payload(payload: dict[str, Any]) -> None:
    has_secret, has_cot = scan_payload(payload)
    if has_secret:
        raise AgentTurnDispatchError(InternalDispatchVerdict.RED_INTERNAL_DISPATCH_SECRET_LEAK.value)
    if has_cot:
        raise AgentTurnDispatchError(InternalDispatchVerdict.RED_INTERNAL_DISPATCH_COT_LEAK.value)


def _extract_body(turn_intent: TurnIntent) -> str | None:
    params = turn_intent.action_params or {}
    for key in ("body", "draft_body", "notes_body", "content"):
        val = params.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _dispatch_content_action(
    *,
    run_id: str,
    turn_index: int,
    action_id: str,
    decision: BrokerDecision,
    turn_intent: TurnIntent,
    observe_snapshot_ref: str,
    capability_menu_ref: str | None,
    reasoning_receipt_ref: str | None,
    base: Path | None,
) -> tuple[str, str | None, str | None]:
    body = _extract_body(turn_intent)
    provider_ref = turn_intent.provider_receipt_ref
    if not provider_ref:
        raise AgentTurnDispatchError(InternalDispatchVerdict.YELLOW_INTERNAL_DISPATCH_CONTENT_DEFERRED.value)
    if not body:
        raise AgentTurnDispatchError(InternalDispatchVerdict.YELLOW_INTERNAL_DISPATCH_BODY_MISSING.value)

    binding = bind_sources(
        observe_snapshot_ref=observe_snapshot_ref,
        capability_menu_ref=capability_menu_ref,
        turn_intent_ref=turn_intent.intent_id,
        reasoning_receipt_ref=reasoning_receipt_ref,
    )
    provider_refs = [provider_ref]
    store = ArtifactStore(run_id)
    review_ref = None

    if action_id == "synthesize_notes":
        artifact = build_notes_artifact(
            body=body,
            source_binding=binding,
            provider_receipt_refs=provider_refs,
            broker_decision_ref=decision.decision_id,
            title=turn_intent.action_params.get("title") if turn_intent.action_params else None,
        )
    elif action_id == "propose_draft":
        artifact = build_draft_artifact(
            body=body,
            source_binding=binding,
            provider_receipt_refs=provider_refs,
            broker_decision_ref=decision.decision_id,
            surface=(turn_intent.action_params or {}).get("surface"),
            title=(turn_intent.action_params or {}).get("title"),
            reasoning_receipt_ref=reasoning_receipt_ref,
        )
    elif action_id == "continue_prior_thread":
        thread_ref = str((turn_intent.action_params or {}).get("thread_ref", f"thread-{turn_index}"))
        artifact = build_thread_continuation_artifact(
            body=body,
            thread_ref=thread_ref,
            source_binding=binding,
            provider_receipt_refs=provider_refs,
            broker_decision_ref=decision.decision_id,
        )
    else:
        raise AgentTurnDispatchError(InternalDispatchVerdict.RED_INTERNAL_DISPATCH_UNSUPPORTED.value)

    quality = evaluate_output_quality(artifact)
    store.store_artifact(artifact)
    store.store_quality_receipt(quality)
    if not quality.verdict.startswith("GREEN_"):
        raise AgentTurnDispatchError(InternalDispatchVerdict.RED_INTERNAL_DISPATCH_QUALITY_FAILED.value)

    artifact = type(artifact)(**{**artifact.__dict__, "status": ArtifactStatus.QUALITY_PASSED})
    if action_id == "propose_draft" and should_queue_for_review(ArtifactKind.DRAFT):
        from hg_runtime.output_artifacts.schema import DraftArtifact

        assert isinstance(artifact, DraftArtifact)
        candidate = create_review_candidate(artifact=artifact, quality_receipt=quality)
        store.store_review_candidate(candidate)
        artifact = DraftArtifact(**{**artifact.__dict__, "status": ArtifactStatus.QUEUED_FOR_REVIEW})
        review_ref = candidate.candidate_id

    return artifact.artifact_id, quality.quality_receipt_id, review_ref


def dispatch_internal_action(
    *,
    run_id: str,
    turn_index: int,
    decision: BrokerDecision,
    turn_intent: TurnIntent,
    observe_snapshot_ref: str,
    live_read_receipt_refs: list[str] | None = None,
    capability_menu_ref: str | None = None,
    reasoning_receipt_ref: str | None = None,
    base: Path | None = None,
) -> InternalDispatchResult:
    """Dispatch safe internal actions and local content artifacts."""
    action_id = decision.chosen_action
    if action_id in FORBIDDEN_DISPATCH_ACTIONS:
        raise AgentTurnDispatchError(InternalDispatchVerdict.RED_INTERNAL_DISPATCH_EXTERNAL_SIDE_EFFECT.value)
    if action_id not in PHASE_9_IMPLEMENTED_ACTIONS:
        raise AgentTurnDispatchError(InternalDispatchVerdict.RED_INTERNAL_DISPATCH_UNSUPPORTED.value)
    if not decision.admitted and decision.status.value not in ("request_scope", "request_operator"):
        raise AgentTurnDispatchError(InternalDispatchVerdict.RED_INTERNAL_DISPATCH_UNSUPPORTED.value)

    dispatch_id = f"dispatch-{uuid.uuid4().hex[:12]}"
    created = _now_iso()
    out_dir = dispatch_dir(run_id, base=base)
    artifact_ref = None
    output_artifact_ref = None
    quality_receipt_ref = None
    review_candidate_ref = None
    witness_ref = None
    scope_refs: list[str] = []
    operator_refs: list[str] = []
    verdict = InternalDispatchVerdict.GREEN_INTERNAL_DISPATCH_COMPLETE

    if action_id in PHASE_9_CONTENT_ACTION_IDS:
        try:
            output_artifact_ref, quality_receipt_ref, review_candidate_ref = _dispatch_content_action(
                run_id=run_id,
                turn_index=turn_index,
                action_id=action_id,
                decision=decision,
                turn_intent=turn_intent,
                observe_snapshot_ref=observe_snapshot_ref,
                capability_menu_ref=capability_menu_ref,
                reasoning_receipt_ref=reasoning_receipt_ref,
                base=base,
            )
            artifact_ref = output_artifact_ref
            verdict = InternalDispatchVerdict.GREEN_INTERNAL_DISPATCH_COMPLETE
        except AgentTurnDispatchError:
            raise

    elif action_id == "rest_turn":
        payload = {"kind": "rest_turn", "turn_index": turn_index, "created_at": created}
        _validate_payload(payload)
        artifact_ref = str(write_json(out_dir / f"rest-{turn_index}.json", payload))

    elif action_id == "witness_turn":
        witness_ref = f"witness-{uuid.uuid4().hex[:12]}"
        payload = {"kind": "witness_turn", "witness_receipt_ref": witness_ref, "turn_index": turn_index, "created_at": created}
        _validate_payload(payload)
        artifact_ref = str(write_json(out_dir / f"witness-{turn_index}.json", payload))

    elif action_id == "request_more_scope":
        scope_refs = list(turn_intent.scope_requests) or [f"scope-{uuid.uuid4().hex[:8]}"]
        payload = {"kind": "request_more_scope", "scope_request_refs": scope_refs, "turn_index": turn_index, "created_at": created}
        _validate_payload(payload)
        artifact_ref = str(write_json(out_dir / f"scope-{turn_index}.json", payload))

    elif action_id == "propose_operator_question":
        operator_refs = list(turn_intent.operator_questions) or ["operator-question-pending"]
        payload = {"kind": "propose_operator_question", "operator_question_refs": operator_refs, "turn_index": turn_index, "created_at": created, "external_send": False}
        _validate_payload(payload)
        artifact_ref = str(write_json(out_dir / f"operator-q-{turn_index}.json", payload))

    elif action_id == "observe_social":
        refs = list(live_read_receipt_refs or [])
        if not refs:
            raise AgentTurnDispatchError(InternalDispatchVerdict.RED_INTERNAL_DISPATCH_UNSUPPORTED.value)
        payload = {"kind": "observe_social", "read_only": True, "live_read_receipt_refs": refs, "turn_index": turn_index, "created_at": created, "network_write": False}
        _validate_payload(payload)
        artifact_ref = str(write_json(out_dir / f"observe-{turn_index}.json", payload))
        verdict = InternalDispatchVerdict.YELLOW_INTERNAL_DISPATCH_READ_ONLY

    result = InternalDispatchResult(
        dispatch_result_id=f"dispatch-res-{uuid.uuid4().hex[:12]}",
        dispatch_id=dispatch_id,
        action_id=action_id,
        verdict=verdict,
        artifact_ref=artifact_ref,
        external_side_effect=False,
        created_at=created,
        witness_receipt_ref=witness_ref,
        scope_request_refs=scope_refs,
        operator_question_refs=operator_refs,
        output_artifact_ref=output_artifact_ref,
        quality_receipt_ref=quality_receipt_ref,
        review_candidate_ref=review_candidate_ref,
    ).with_hash()

    body = {k: v for k, v in result.to_payload().items() if k != "hash"}
    if not verify_record_hash(body, result.hash):
        raise AgentTurnDispatchError("dispatch result hash invalid")
    write_json(out_dir / f"{result.dispatch_result_id}.json", result.to_payload())
    return result


__all__ = [
    "FORBIDDEN_DISPATCH_ACTIONS",
    "InternalDispatchResult",
    "InternalDispatchVerdict",
    "dispatch_internal_action",
]
