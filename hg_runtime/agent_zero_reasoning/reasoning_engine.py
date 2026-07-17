"""Reasoning engine — produce validated TurnIntent, no execution."""

from __future__ import annotations

from typing import Any

from hg_runtime.agent_zero_prompt.charter import compute_prompt_hash, load_zero_charter, load_zero_witness_extension
from hg_runtime.agent_zero_prompt.reasoning_prompt_builder import build_agent_turn_decision_prompt
from hg_runtime.agent_zero_state.capability_menu import CapabilityMenuSnapshot
from hg_runtime.agent_zero_state.observe_snapshot import ObserveSnapshot, validate_observe_snapshot
from hg_runtime.agent_zero_state.state import AgentState, validate_agent_state
from hg_runtime.agent_zero_state.types import AgentStateVerdict, ObserveSnapshotVerdict
from hg_runtime.model_provider_fabric.provider_receipts import (
    ProviderFallbackDenied,
    ProviderMode,
    ProviderRealityVerdict,
    ProviderUnavailable,
)
from hg_runtime.agent_zero_reasoning.errors import (
    ReasoningParseError,
    ReasoningProviderError,
    ReasoningValidationError,
)
from hg_runtime.agent_zero_reasoning.intent_validator import validate_reasoning_as_turn_intent
from hg_runtime.agent_zero_reasoning.output_parser import hash_parsed_output, hash_raw_output, parse_reasoning_output
from hg_runtime.agent_zero_reasoning.provider_adapter import ProviderInvokeFn, request_turn_decision_from_provider
from hg_runtime.agent_zero_reasoning.reasoning_receipts import (
    ReasoningReceipt,
    build_reasoning_receipt_from_failure,
    build_reasoning_receipt_from_result,
)
from hg_runtime.agent_zero_reasoning.schema import (
    ReasoningContext,
    ReasoningFailure,
    ReasoningRequest,
    ReasoningResult,
    ReasoningVerdict,
    build_reasoning_request,
    new_failure_id,
    new_result_id,
)


def _agent_state_ref(state: AgentState) -> str:
    return state.state_hash or f"agent-state-{state.agent_id}"


def _build_context(
    *,
    agent_state: AgentState,
    observe_snapshot: ObserveSnapshot,
    capability_menu: CapabilityMenuSnapshot,
    prompt_assets: dict[str, Any] | None,
) -> tuple[ReasoningContext, str]:
    charter = load_zero_charter()
    witness = load_zero_witness_extension()
    prompt_payload = build_agent_turn_decision_prompt(
        observe_snapshot=observe_snapshot.to_payload(),
        capability_menu=[a.to_payload() for a in capability_menu.actions],
        outer_enforcement_summary=(prompt_assets or {}).get("outer_enforcement_summary"),
    )
    prompt_hash = prompt_payload.get("prompt_hash") or compute_prompt_hash(charter.text)
    context = ReasoningContext(
        charter_text_hash=compute_prompt_hash(charter.text),
        witness_extension_hash=compute_prompt_hash(witness.text),
        observe_snapshot=observe_snapshot,
        capability_menu=capability_menu,
        agent_state_summary={
            "agent_id": agent_state.agent_id,
            "turn_index": agent_state.turn_index,
            "runtime_mode": agent_state.runtime_mode,
            "operator_presence_state": agent_state.operator_presence_state,
        },
        provider_reality_refs=list(observe_snapshot.provider_reality_refs),
        live_read_receipt_refs=list(observe_snapshot.live_read_receipt_refs),
        witness_receipt_refs=[observe_snapshot.witness_state_ref] if observe_snapshot.witness_state_ref else [],
        failure_posture_refs=list(observe_snapshot.failure_posture_refs),
        scope_request_refs=list(observe_snapshot.scope_request_refs),
        outer_enforcement_summary=prompt_payload.get("context_sections", {}).get("outer_enforcement_summary", {}),
    )
    return context, prompt_hash


def _failure_from_provider(
    request: ReasoningRequest,
    *,
    receipt,
    kind: str,
    verdict: ReasoningVerdict,
    reason: str,
) -> ReasoningFailure:
    return ReasoningFailure(
        failure_id=new_failure_id(),
        request_id=request.request_id,
        provider_receipt_ref=receipt.receipt_id if receipt else None,
        failure_kind=kind,
        verdict=verdict,
        reason=reason,
        created_at=request.created_at,
    ).with_hash()


def _result_verdict_for_action(chosen_action: str) -> ReasoningVerdict:
    if chosen_action in ("rest_turn", "witness_turn"):
        return ReasoningVerdict.YELLOW_WITNESS_OR_REST_CHOSEN
    if chosen_action == "request_more_scope":
        return ReasoningVerdict.YELLOW_SCOPE_REQUEST_CHOSEN
    return ReasoningVerdict.GREEN_REASONING_INTENT_VALID


def produce_turn_intent(
    *,
    agent_state: AgentState,
    observe_snapshot: ObserveSnapshot,
    capability_menu: CapabilityMenuSnapshot,
    prompt_assets: dict[str, Any] | None = None,
    provider_invoke: ProviderInvokeFn | None = None,
    store_receipt: bool = False,
) -> ReasoningResult | ReasoningFailure:
    """Produce validated TurnIntent from observe state — no execution."""
    state_verdict, _ = validate_agent_state(agent_state)
    if state_verdict.value.startswith("RED_"):
        return ReasoningFailure(
            failure_id=new_failure_id(),
            request_id="invalid",
            failure_kind="invalid_agent_state",
            verdict=ReasoningVerdict.RED_REASONING_PROVIDER_RECEIPT_MISSING,
            reason=state_verdict.value,
            created_at=agent_state.updated_at,
        ).with_hash()

    snap_verdict, validated_snap = validate_observe_snapshot(observe_snapshot)
    if snap_verdict == ObserveSnapshotVerdict.RED_OBSERVE_EMPTY_SUCCESS:
        return ReasoningFailure(
            failure_id=new_failure_id(),
            request_id="invalid",
            failure_kind="empty_observe",
            verdict=ReasoningVerdict.RED_REASONING_EMPTY_OUTPUT,
            reason=snap_verdict.value,
            created_at=validated_snap.observed_at,
        ).with_hash()

    context, prompt_hash = _build_context(
        agent_state=agent_state,
        observe_snapshot=validated_snap,
        capability_menu=capability_menu,
        prompt_assets=prompt_assets,
    )

    request = build_reasoning_request(
        agent_id=agent_state.agent_id,
        turn_index=agent_state.turn_index + 1,
        agent_state_ref=_agent_state_ref(agent_state),
        observe_snapshot_ref=validated_snap.snapshot_id,
        capability_menu_ref=capability_menu.menu_id,
        prompt_hash=prompt_hash,
        runtime_mode=agent_state.runtime_mode,
        run_id=agent_state.run_id,
    )

    try:
        provider_receipt, raw_text = request_turn_decision_from_provider(
            request,
            context,
            provider_invoke=provider_invoke,
        )
    except ProviderFallbackDenied as exc:
        failure = _failure_from_provider(
            request,
            receipt=exc.receipt,
            kind="fallback_stub",
            verdict=ReasoningVerdict.RED_REASONING_FALLBACK_STUB_USED,
            reason=exc.receipt.verdict.value,
        )
        if store_receipt:
            build_reasoning_receipt_from_failure(
                request_id=request.request_id,
                observe_snapshot_ref=validated_snap.snapshot_id,
                capability_menu_ref=capability_menu.menu_id,
                agent_state_ref=_agent_state_ref(agent_state),
                prompt_hash=prompt_hash,
                failure=failure,
            )
        return failure
    except ProviderUnavailable as exc:
        failure = _failure_from_provider(
            request,
            receipt=exc.receipt,
            kind="provider_unavailable",
            verdict=ReasoningVerdict.YELLOW_PROVIDER_UNAVAILABLE,
            reason=exc.receipt.verdict.value,
        )
        if store_receipt:
            build_reasoning_receipt_from_failure(
                request_id=request.request_id,
                observe_snapshot_ref=validated_snap.snapshot_id,
                capability_menu_ref=capability_menu.menu_id,
                agent_state_ref=_agent_state_ref(agent_state),
                prompt_hash=prompt_hash,
                failure=failure,
            )
        return failure
    except ReasoningProviderError as exc:
        verdict = ReasoningVerdict.RED_REASONING_EMPTY_OUTPUT
        if exc.receipt and exc.receipt.verdict == ProviderRealityVerdict.RED_PROVIDER_EMPTY_OUTPUT:
            verdict = ReasoningVerdict.RED_REASONING_EMPTY_OUTPUT
        failure = _failure_from_provider(
            request,
            receipt=exc.receipt,
            kind="provider_error",
            verdict=verdict,
            reason=str(exc),
        )
        return failure

    try:
        parsed = parse_reasoning_output(raw_text)
        intent = validate_reasoning_as_turn_intent(
            parsed,
            capability_menu,
            provider_receipt,
            validated_snap,
        )
    except ReasoningParseError as exc:
        kind = exc.kind
        verdict = ReasoningVerdict.RED_REASONING_INVALID_JSON
        if kind == "empty":
            verdict = ReasoningVerdict.RED_REASONING_EMPTY_OUTPUT
        elif kind == "cot":
            verdict = ReasoningVerdict.RED_REASONING_COT_STORED
        elif kind == "secret":
            verdict = ReasoningVerdict.RED_REASONING_SECRET_STORED
        return ReasoningFailure(
            failure_id=new_failure_id(),
            request_id=request.request_id,
            provider_receipt_ref=provider_receipt.receipt_id,
            failure_kind=kind,
            verdict=verdict,
            reason=str(exc),
            created_at=request.created_at,
        ).with_hash()
    except ReasoningValidationError as exc:
        return ReasoningFailure(
            failure_id=new_failure_id(),
            request_id=request.request_id,
            provider_receipt_ref=provider_receipt.receipt_id,
            failure_kind="validation",
            verdict=ReasoningVerdict(exc.verdict),
            reason=str(exc),
            created_at=request.created_at,
        ).with_hash()

    result = ReasoningResult(
        result_id=new_result_id(),
        request_id=request.request_id,
        provider_receipt_ref=provider_receipt.receipt_id,
        turn_intent=intent,
        reasoning_summary=parsed["reasoning_summary"],
        raw_model_output_hash=hash_raw_output(raw_text),
        parsed_output_hash=hash_parsed_output(parsed),
        verdict=_result_verdict_for_action(intent.chosen_action),
        created_at=request.created_at,
    ).with_hash()

    if store_receipt:
        build_reasoning_receipt_from_result(
            request_id=request.request_id,
            observe_snapshot_ref=validated_snap.snapshot_id,
            capability_menu_ref=capability_menu.menu_id,
            agent_state_ref=_agent_state_ref(agent_state),
            prompt_hash=prompt_hash,
            result=result,
        )

    return result


__all__ = ["ReasoningReceipt", "produce_turn_intent"]
