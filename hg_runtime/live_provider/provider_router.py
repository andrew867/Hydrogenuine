"""Provider routing — health, completion, dry turn."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import AgentTurnResult, build_agent_turn_request
from hg_runtime.live_provider.errors import LiveProviderNonCognitiveDenied, LiveProviderOutputError, LiveProviderUnavailable
from hg_runtime.live_provider.json_contracts import evaluate_json_output
from hg_runtime.live_provider.local_provider_clients import complete_openai_compatible, unavailable_stub_response
from hg_runtime.live_provider.provider_health import probe_provider_health
from hg_runtime.live_provider.provider_identity import (
    build_model_identity,
    build_provider_identity,
    provider_configured,
    unavailable_verdict_for_kind,
)
from hg_runtime.live_provider.provider_receipts import (
    build_output_receipt,
    output_receipt_counts_as_cognition,
    store_output_receipt,
)
from hg_runtime.live_provider.schema import (
    LiveProviderVerdict,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderRouteDecision,
    ProviderRuntimeMode,
    load_live_provider_policy,
    new_id,
    now_iso,
    validate_policy_constraints,
)

WORKSPACE = Path(__file__).resolve().parents[2]


def route_provider(*, runtime_mode: ProviderRuntimeMode = ProviderRuntimeMode.DRY_AUTONOMY) -> ProviderRouteDecision:
    validate_policy_constraints()
    provider = build_provider_identity(runtime_mode=runtime_mode)
    model = build_model_identity(provider)
    if not provider_configured(provider):
        verdict = unavailable_verdict_for_kind(provider.provider_kind)
        return ProviderRouteDecision(
            route_id=new_id("route"),
            provider_ref=provider.provider_id,
            model_ref=model.model_id,
            provider_kind=provider.provider_kind,
            verdict=verdict,
            reason="provider not configured or unreachable",
        ).with_hash()
    health = probe_provider_health(runtime_mode=runtime_mode)
    if not health.available:
        return ProviderRouteDecision(
            route_id=new_id("route"),
            provider_ref=provider.provider_id,
            model_ref=model.model_id,
            provider_kind=provider.provider_kind,
            verdict=health.verdict,
            reason=health.failure_reason or health.verdict.value,
        ).with_hash()
    return ProviderRouteDecision(
        route_id=new_id("route"),
        provider_ref=provider.provider_id,
        model_ref=model.model_id,
        provider_kind=provider.provider_kind,
        verdict=LiveProviderVerdict.GREEN_LIVE_PROVIDER_AVAILABLE,
        reason="provider configured and health probe passed",
    ).with_hash()


def complete_json(
    payload: dict[str, Any] | str,
    *,
    http_complete: Callable[..., dict[str, Any]] | None = None,
    runtime_mode: ProviderRuntimeMode = ProviderRuntimeMode.DRY_AUTONOMY,
) -> ProviderResponse | ProviderFailure:
    validate_policy_constraints()
    if isinstance(payload, str):
        payload = json.loads(payload)
    request = ProviderRequest(
        request_id=new_id("prov-req"),
        prompt_hash=compute_record_hash(payload),
        role="LIVE_PROVIDER_JSON",
        json_required=True,
    )
    route = route_provider(runtime_mode=runtime_mode)
    provider = build_provider_identity(runtime_mode=runtime_mode)
    model = build_model_identity(provider)

    if route.verdict != LiveProviderVerdict.GREEN_LIVE_PROVIDER_AVAILABLE:
        return ProviderFailure(
            failure_id=new_id("prov-fail"),
            request_ref=request.request_id,
            verdict=route.verdict,
            reason=route.reason,
        )

    prompt = json.dumps(payload)
    started = time.monotonic()
    complete_fn = http_complete or complete_openai_compatible
    result = complete_fn(
        provider.endpoint_ref or "",
        model_id=model.model_id,
        prompt=prompt,
        json_mode=True,
    )
    latency = int((time.monotonic() - started) * 1000)

    if result.get("unavailable") or not result.get("ok"):
        return ProviderFailure(
            failure_id=new_id("prov-fail"),
            request_ref=request.request_id,
            verdict=unavailable_verdict_for_kind(provider.provider_kind),
            reason=result.get("failure_reason") or "provider call failed",
        )

    output_text = str(result.get("output_text") or "")
    json_valid, schema_valid, _verdict = evaluate_json_output(output_text, require_turn_schema=False)
    receipt = build_output_receipt(
        request_ref=request.request_id,
        provider=provider,
        model=model,
        prompt_hash=request.prompt_hash,
        output_text=output_text,
        json_valid=json_valid,
        schema_valid=schema_valid,
        latency_ms=latency,
        token_counts=result.get("token_counts"),
        finish_reason=result.get("finish_reason"),
    )
    store_output_receipt(receipt, output_text=output_text)

    if receipt.verdict == LiveProviderVerdict.YELLOW_PROVIDER_OUTPUT_EMPTY_DEFERRED:
        return ProviderFailure(
            failure_id=new_id("prov-fail"),
            request_ref=request.request_id,
            verdict=receipt.verdict,
            reason="empty provider output",
            output_receipt_ref=receipt.provider_output_receipt_id,
        )
    if receipt.verdict == LiveProviderVerdict.YELLOW_PROVIDER_JSON_INVALID_DEFERRED:
        return ProviderFailure(
            failure_id=new_id("prov-fail"),
            request_ref=request.request_id,
            verdict=receipt.verdict,
            reason="invalid provider json",
            output_receipt_ref=receipt.provider_output_receipt_id,
        )

    return ProviderResponse(
        request_ref=request.request_id,
        output_text=output_text,
        output_receipt=receipt,
        provider_identity=provider,
        model_identity=model,
    )


def run_dry_provider_turn(
    *,
    run_id: str,
    agent_id: str = "zero",
    turn_base: Path | None = None,
    provider_invoke: Callable | None = None,
) -> dict[str, Any]:
    """Run one governed dry agent turn with provider enabled."""
    validate_policy_constraints()
    route = route_provider()
    health = probe_provider_health()
    tbase = turn_base or (WORKSPACE / ".hg-local/agent_zero/turns" / run_id)
    tbase.mkdir(parents=True, exist_ok=True)

    req = build_agent_turn_request(agent_id=agent_id, run_id=run_id, allow_provider=True)
    invoke = provider_invoke
    if invoke is None and route.verdict == LiveProviderVerdict.GREEN_LIVE_PROVIDER_AVAILABLE:
        provider = build_provider_identity()
        model = build_model_identity(provider)

        def _live_invoke(_prompt, _receipt):
            prompt_json = json.dumps({"task": "agent_turn_decision", "format": "json"})
            res = complete_openai_compatible(
                provider.endpoint_ref or "",
                model_id=model.model_id,
                prompt=prompt_json,
                json_mode=True,
            )
            if not res.get("ok"):
                raise LiveProviderUnavailable(res.get("failure_reason") or "provider unavailable")
            return res.get("output_text") or ""

        invoke = _live_invoke

    out = run_single_agent_turn(req, provider_invoke=invoke, base=tbase)
    result = {
        "run_id": run_id,
        "agent_id": agent_id,
        "route_verdict": route.verdict.value,
        "health_receipt": health.health_receipt_id,
        "health_available": health.available,
        "turn_type": type(out).__name__,
        "created_at": now_iso(),
    }
    if isinstance(out, AgentTurnResult):
        result["turn_verdict"] = out.verdict.value
        result["turn_receipt_ref"] = out.turn_receipt_ref
        result["reasoning_result_ref"] = out.reasoning_result_ref
        result["reasoning_failure_ref"] = out.reasoning_failure_ref
    else:
        result["turn_verdict"] = getattr(out, "verdict", None)
        if hasattr(out, "verdict") and out.verdict:
            result["turn_verdict"] = out.verdict.value
    return result


def reject_non_cognitive_text(text: str, *, source_label: str) -> None:
    policy = load_live_provider_policy()
    key_map = {
        "fallback": "fallback_as_cognition_allowed",
        "fixture": "fixture_as_cognition_allowed",
        "mock": "mock_as_cognition_allowed",
    }
    if source_label not in key_map:
        return
    if policy.get(key_map[source_label]) is False and text.strip():
        raise LiveProviderNonCognitiveDenied(f"RED_{source_label.upper()}_TEXT_TREATED_AS_COGNITION")
