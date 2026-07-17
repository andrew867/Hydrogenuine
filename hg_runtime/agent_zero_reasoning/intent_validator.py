"""Validate reasoning output as TurnIntent."""

from __future__ import annotations

from typing import Any

from hg_runtime.agent_zero_state.capability_menu import CapabilityMenuSnapshot
from hg_runtime.agent_zero_state.observe_snapshot import ObserveSnapshot
from hg_runtime.agent_zero_state.turn_intent import TurnIntent, build_turn_intent
from hg_runtime.agent_zero_state.types import FORBIDDEN_ACTION_IDS, TurnIntentVerdict
from hg_runtime.model_provider_fabric.provider_receipts import (
    ProviderMode,
    ProviderRealityVerdict,
    ProviderReceipt,
    receipt_counts_as_cognition,
)
from hg_runtime.agent_zero_reasoning.errors import ReasoningValidationError
from hg_runtime.agent_zero_reasoning.schema import ReasoningVerdict, load_reasoning_engine_policy


def _provider_mode_to_verdict(receipt: ProviderReceipt) -> ReasoningVerdict:
    if receipt.provider_mode == ProviderMode.DRY_RUN or receipt.dry_run:
        return ReasoningVerdict.RED_REASONING_DRY_RUN_USED
    if receipt.provider_mode == ProviderMode.FIXTURE or receipt.fixture_mode:
        return ReasoningVerdict.RED_REASONING_FIXTURE_USED
    if receipt.provider_mode == ProviderMode.FALLBACK_STUB:
        return ReasoningVerdict.RED_REASONING_FALLBACK_STUB_USED
    if receipt.provider_mode == ProviderMode.PROOF_REPLAY:
        return ReasoningVerdict.RED_REASONING_DRY_RUN_USED
    if receipt.verdict == ProviderRealityVerdict.YELLOW_PROVIDER_UNAVAILABLE:
        return ReasoningVerdict.YELLOW_PROVIDER_UNAVAILABLE
    return ReasoningVerdict.RED_REASONING_PROVIDER_RECEIPT_MISSING


def validate_reasoning_as_turn_intent(
    parsed_output: dict[str, Any],
    capability_menu: CapabilityMenuSnapshot,
    provider_receipt: ProviderReceipt,
    observe_snapshot: ObserveSnapshot,
) -> TurnIntent:
    """Validate parsed model output and produce TurnIntent."""
    policy = load_reasoning_engine_policy()

    if provider_receipt is None:
        raise ReasoningValidationError(
            "provider receipt required",
            verdict=ReasoningVerdict.RED_REASONING_PROVIDER_RECEIPT_MISSING.value,
        )

    if policy.get("provider_receipt_required", True) and not provider_receipt.receipt_id:
        raise ReasoningValidationError(
            "provider receipt id missing",
            verdict=ReasoningVerdict.RED_REASONING_PROVIDER_RECEIPT_MISSING.value,
        )

    if not receipt_counts_as_cognition(provider_receipt):
        verdict = _provider_mode_to_verdict(provider_receipt)
        raise ReasoningValidationError(
            f"provider does not count as cognition: {provider_receipt.verdict.value}",
            verdict=verdict.value,
        )

    chosen = parsed_output["chosen_action"]
    if chosen in FORBIDDEN_ACTION_IDS:
        raise ReasoningValidationError(
            f"external/forbidden action: {chosen}",
            verdict=ReasoningVerdict.RED_REASONING_EXTERNAL_PERMISSION.value,
        )

    action_entry = next((a for a in capability_menu.actions if a.action_id == chosen), None)
    if action_entry is None:
        raise ReasoningValidationError(
            f"action outside menu: {chosen}",
            verdict=ReasoningVerdict.RED_REASONING_ACTION_OUTSIDE_MENU.value,
        )
    if not action_entry.enabled:
        raise ReasoningValidationError(
            f"disabled action: {chosen}",
            verdict=ReasoningVerdict.RED_REASONING_ACTION_OUTSIDE_MENU.value,
        )
    if action_entry.external_side_effect and policy.get("external_side_effects_allowed") is False:
        raise ReasoningValidationError(
            f"external side effect action: {chosen}",
            verdict=ReasoningVerdict.RED_REASONING_EXTERNAL_PERMISSION.value,
        )

    if action_entry.requires_provider and not observe_snapshot.provider_reality_refs:
        raise ReasoningValidationError(
            "provider required but unavailable in observe snapshot",
            verdict=ReasoningVerdict.YELLOW_REASONING_DEFERRED.value,
        )
    if action_entry.requires_live_read and not observe_snapshot.live_read_receipt_refs:
        raise ReasoningValidationError(
            "live read required but unavailable",
            verdict=ReasoningVerdict.YELLOW_REASONING_DEFERRED.value,
        )

    alternatives = [str(a.get("action", "")).strip() for a in parsed_output.get("alternatives_considered", [])]
    why_not = "; ".join(
        f"{a.get('action')}: {a.get('why_not')}"
        for a in parsed_output.get("alternatives_considered", [])
        if a.get("action")
    )

    witness_mode = None
    if chosen == "witness_turn":
        witness_mode = "witness_requested"

    verdict, intent = build_turn_intent(
        agent_id=observe_snapshot.agent_id,
        turn_index=observe_snapshot.turn_index,
        chosen_action=chosen,
        menu=capability_menu,
        observation_summary=parsed_output["observation_summary"],
        why_this_action=parsed_output["reasoning_summary"],
        action_params=parsed_output.get("action_params", {}),
        alternatives_considered=alternatives,
        why_not_others=why_not,
        uncertainty=parsed_output.get("uncertainty", ""),
        operator_questions=parsed_output.get("operator_questions", []),
        scope_requests=parsed_output.get("scope_requests", []),
        witness_mode_requested=witness_mode,
        run_id=observe_snapshot.run_id,
        provider_receipt_ref=provider_receipt.receipt_id,
    )

    if verdict == TurnIntentVerdict.RED_TURN_INTENT_UNKNOWN_ACTION:
        raise ReasoningValidationError("unknown action", verdict=ReasoningVerdict.RED_REASONING_UNKNOWN_ACTION.value)
    if verdict == TurnIntentVerdict.RED_TURN_INTENT_COT_LEAK:
        raise ReasoningValidationError("cot stored", verdict=ReasoningVerdict.RED_REASONING_COT_STORED.value)
    if verdict == TurnIntentVerdict.RED_TURN_INTENT_SECRET_LEAK:
        raise ReasoningValidationError("secret stored", verdict=ReasoningVerdict.RED_REASONING_SECRET_STORED.value)
    if verdict != TurnIntentVerdict.GREEN_TURN_INTENT_VALID:
        raise ReasoningValidationError(
            f"intent invalid: {verdict.value}",
            verdict=ReasoningVerdict.RED_REASONING_UNKNOWN_ACTION.value,
        )

    return intent


__all__ = ["validate_reasoning_as_turn_intent"]
