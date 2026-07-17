"""Provider adapter for turn decision reasoning."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.agent_zero_prompt.reasoning_prompt_builder import build_agent_turn_decision_prompt
from hg_runtime.model_provider_fabric.provider_receipts import (
    ProviderFallbackDenied,
    ProviderKind,
    ProviderMode,
    ProviderRealityVerdict,
    ProviderReceipt,
    ProviderStatus,
    ProviderUnavailable,
    build_provider_receipt,
    load_provider_reality_policy,
)
from hg_runtime.model_provider_fabric.provider_reality import evaluate_provider_output, probe_provider_reality
from hg_runtime.model_provider_fabric.routing import route_to_verdict
from hg_runtime.runtime_mode import RuntimeMode, resolve_runtime_mode
from hg_runtime.agent_zero_reasoning.errors import ReasoningProviderError
from hg_runtime.agent_zero_reasoning.schema import ReasoningContext, ReasoningRequest, ROLE_AGENT_TURN_DECISION

ProviderInvokeFn = Callable[[dict[str, Any], ProviderReceipt], str]


def _runtime_mode_from_name(name: str) -> RuntimeMode | None:
    try:
        return RuntimeMode(name)
    except ValueError:
        return None


def _build_prompt_payload(context: ReasoningContext) -> dict[str, Any]:
    menu_actions = [a.to_payload() for a in context.capability_menu.actions]
    return build_agent_turn_decision_prompt(
        observe_snapshot=context.observe_snapshot.to_payload(),
        capability_menu=menu_actions,
        outer_enforcement_summary=context.outer_enforcement_summary,
    )


def _completion_receipt(
    *,
    provider_id: str,
    provider_mode: ProviderMode,
    provider_kind: ProviderKind,
    verdict: ProviderRealityVerdict,
    request_hash: str,
    runtime_mode: str,
    dry_run: bool,
    fixture_mode: bool,
    response_hash: str | None,
    output_bytes: int,
    started_at: str,
    ended_at: str,
    model_id: str | None = None,
) -> ProviderReceipt:
    cfg_hash = compute_record_hash(load_provider_reality_policy())
    status = ProviderStatus.AVAILABLE if verdict == ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE else ProviderStatus.UNAVAILABLE
    if verdict in (
        ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION,
        ProviderRealityVerdict.RED_PROVIDER_FIXTURE_AS_COGNITION,
    ):
        status = ProviderStatus.REFUSED
    return build_provider_receipt(
        provider_id=provider_id,
        provider_kind=provider_kind,
        provider_mode=provider_mode,
        role=ROLE_AGENT_TURN_DECISION,
        request_hash=request_hash,
        config_hash=cfg_hash,
        runtime_mode=runtime_mode,
        cognitive_soak_active=False,
        dry_run=dry_run,
        fixture_mode=fixture_mode,
        status=status,
        verdict=verdict,
        started_at=started_at,
        ended_at=ended_at,
        latency_ms=max(0, int((datetime.fromisoformat(ended_at) - datetime.fromisoformat(started_at)).total_seconds() * 1000)),
        model_id=model_id,
        response_hash=response_hash,
        output_bytes=output_bytes,
    )


def request_turn_decision_from_provider(
    request: ReasoningRequest,
    context: ReasoningContext,
    *,
    provider_invoke: ProviderInvokeFn | None = None,
) -> tuple[ProviderReceipt, str]:
    """Request turn decision from provider with mandatory receipt."""
    started = datetime.now(timezone.utc).isoformat()
    prompt_payload = _build_prompt_payload(context)
    request_body = {
        "request_id": request.request_id,
        "role": ROLE_AGENT_TURN_DECISION,
        "prompt_hash": request.prompt_hash,
        "prompt_kind": prompt_payload.get("prompt_kind"),
    }
    req_hash = compute_record_hash(request_body)

    runtime_mode = _runtime_mode_from_name(request.runtime_mode)
    route_verdict, provider_id, provider_mode = route_to_verdict(
        ROLE_AGENT_TURN_DECISION,
        runtime_mode=runtime_mode,
        request_body=request_body,
    )

    mode_receipt = resolve_runtime_mode()
    runtime_name = request.runtime_mode or mode_receipt.runtime_mode.value
    fixture_mode = runtime_mode == RuntimeMode.FIXTURE if runtime_mode else mode_receipt.fixture_allowed
    dry_run = provider_mode == ProviderMode.DRY_RUN

    kind = ProviderKind.LOCAL_OPENVINO
    if provider_mode in (ProviderMode.FALLBACK_STUB, ProviderMode.FIXTURE):
        kind = ProviderKind.STUB
    elif provider_mode == ProviderMode.UNAVAILABLE:
        kind = ProviderKind.UNKNOWN

    if route_verdict != ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE:
        if provider_invoke is None:
            ended = datetime.now(timezone.utc).isoformat()
            receipt = _completion_receipt(
                provider_id=provider_id,
                provider_mode=provider_mode,
                provider_kind=kind,
                verdict=route_verdict,
                request_hash=req_hash,
                runtime_mode=runtime_name,
                dry_run=dry_run,
                fixture_mode=fixture_mode,
                response_hash=None,
                output_bytes=0,
                started_at=started,
                ended_at=ended,
            )
            if route_verdict == ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION:
                raise ProviderFallbackDenied(receipt)
            raise ProviderUnavailable(receipt)
        if route_verdict in (
            ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION,
            ProviderRealityVerdict.RED_PROVIDER_FIXTURE_AS_COGNITION,
        ):
            ended = datetime.now(timezone.utc).isoformat()
            receipt = _completion_receipt(
                provider_id=provider_id,
                provider_mode=provider_mode,
                provider_kind=kind,
                verdict=route_verdict,
                request_hash=req_hash,
                runtime_mode=runtime_name,
                dry_run=dry_run,
                fixture_mode=fixture_mode,
                response_hash=None,
                output_bytes=0,
                started_at=started,
                ended_at=ended,
            )
            if route_verdict == ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION:
                raise ProviderFallbackDenied(receipt)
            raise ProviderUnavailable(receipt)
        if provider_mode in (ProviderMode.DRY_RUN, ProviderMode.PROOF_REPLAY, ProviderMode.FIXTURE):
            ended = datetime.now(timezone.utc).isoformat()
            receipt = _completion_receipt(
                provider_id=provider_id,
                provider_mode=provider_mode,
                provider_kind=kind,
                verdict=route_verdict,
                request_hash=req_hash,
                runtime_mode=runtime_name,
                dry_run=dry_run,
                fixture_mode=fixture_mode,
                response_hash=None,
                output_bytes=0,
                started_at=started,
                ended_at=ended,
            )
            raise ProviderUnavailable(receipt)
        provider_id = provider_id or "test-double-live"
        provider_mode = ProviderMode.LIVE
        kind = ProviderKind.STUB
        route_verdict = ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE

    if provider_invoke is None:
        if route_verdict == ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE and kind == ProviderKind.LOCAL_OPENVINO:
            from hg_runtime.live_provider.openvino_invoke import invoke_openvino_turn_decision

            provider_invoke = invoke_openvino_turn_decision
        else:
            probe = probe_provider_reality(ROLE_AGENT_TURN_DECISION, runtime_mode=runtime_mode)
            raise ProviderUnavailable(probe)

    ended_before = datetime.now(timezone.utc).isoformat()
    model_id = "test-double-live" if provider_invoke.__name__ != "_builtin_live_invoke" else provider_id
    try:
        raw_text = provider_invoke(prompt_payload, _completion_receipt(
            provider_id=provider_id,
            provider_mode=ProviderMode.LIVE,
            provider_kind=kind,
            verdict=ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE,
            request_hash=req_hash,
            runtime_mode=runtime_name,
            dry_run=False,
            fixture_mode=False,
            response_hash=None,
            output_bytes=0,
            started_at=started,
            ended_at=ended_before,
            model_id="provider-invoke-pending",
        ))
    except Exception as exc:
        raise ReasoningProviderError(str(exc)) from exc

    if not raw_text or not str(raw_text).strip():
        ended = datetime.now(timezone.utc).isoformat()
        receipt = _completion_receipt(
            provider_id=provider_id,
            provider_mode=ProviderMode.LIVE,
            provider_kind=kind,
            verdict=ProviderRealityVerdict.RED_PROVIDER_EMPTY_OUTPUT,
            request_hash=req_hash,
            runtime_mode=runtime_name,
            dry_run=False,
            fixture_mode=False,
            response_hash=None,
            output_bytes=0,
            started_at=started,
            ended_at=ended,
            model_id=model_id,
        )
        raise ReasoningProviderError("empty provider output", receipt=receipt)

    ended = datetime.now(timezone.utc).isoformat()
    response_hash = compute_record_hash({"output": raw_text})
    receipt = _completion_receipt(
        provider_id=provider_id,
        provider_mode=ProviderMode.LIVE,
        provider_kind=kind,
        verdict=ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE,
        request_hash=req_hash,
        runtime_mode=runtime_name,
        dry_run=False,
        fixture_mode=False,
        response_hash=response_hash,
        output_bytes=len(raw_text.encode("utf-8")),
        started_at=started,
        ended_at=ended,
        model_id=model_id,
    )

    output_verdict = evaluate_provider_output(
        role=ROLE_AGENT_TURN_DECISION,
        output_text=raw_text,
        receipt=receipt,
    )
    if output_verdict.value.startswith("RED"):
        raise ReasoningProviderError(output_verdict.value, receipt=receipt)

    return receipt, str(raw_text)


__all__ = [
    "ProviderInvokeFn",
    "request_turn_decision_from_provider",
]
