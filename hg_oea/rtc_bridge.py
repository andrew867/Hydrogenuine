"""OEA RTC event draft builders."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from hg_oea.types import DryRunResult, EffectReceipt, OEABinding
from hg_runtime.contract import draft


def binding_created_draft(binding: OEABinding, *, parent: str) -> Dict[str, Any]:
    return draft("OEA_BINDING_CREATED", binding.to_payload(), causal_parents=[parent])


def binding_refused_draft(
    *,
    binding_id: str,
    capability_id: str,
    reason: str,
    parent: str,
    ueak_commit_ref: str = "",
) -> Dict[str, Any]:
    return draft(
        "OEA_BINDING_REFUSED",
        {
            "binding_id": binding_id,
            "capability_id": capability_id,
            "reason": reason,
            "ueak_commit_ref": ueak_commit_ref,
        },
        causal_parents=[parent],
    )


def dry_run_started_draft(binding: OEABinding, *, parent: str) -> Dict[str, Any]:
    return draft(
        "OEA_DRY_RUN_STARTED",
        {"binding_id": binding.binding_id, "capability_id": binding.capability_id},
        causal_parents=[parent],
    )


def dry_run_completed_draft(dry_run: DryRunResult, *, parent: str) -> Dict[str, Any]:
    return draft("OEA_DRY_RUN_COMPLETED", dry_run.to_payload(), causal_parents=[parent])


def execution_requested_draft(binding: OEABinding, *, parent: str) -> Dict[str, Any]:
    return draft(
        "OEA_EXECUTION_REQUESTED",
        {"binding_id": binding.binding_id, "capability_id": binding.capability_id},
        causal_parents=[parent],
    )


def execution_started_draft(binding: OEABinding, *, parent: str) -> Dict[str, Any]:
    return draft(
        "OEA_EXECUTION_STARTED",
        {"binding_id": binding.binding_id, "capability_id": binding.capability_id},
        causal_parents=[parent],
    )


def execution_completed_draft(receipt: EffectReceipt, *, parent: str) -> Dict[str, Any]:
    return draft(
        "OEA_EXECUTION_COMPLETED",
        {
            "binding_id": receipt.binding_id,
            "capability_id": receipt.capability_id,
            "result_status": receipt.result_status,
            "receipt_id": receipt.receipt_id,
        },
        causal_parents=[parent],
    )


def execution_refused_draft(
    *,
    binding_id: str,
    capability_id: str,
    reason: str,
    parent: str,
) -> Dict[str, Any]:
    return draft(
        "OEA_EXECUTION_REFUSED",
        {"binding_id": binding_id, "capability_id": capability_id, "reason": reason},
        causal_parents=[parent],
    )


def execution_failed_draft(
    *,
    binding_id: str,
    capability_id: str,
    reason: str,
    parent: str,
) -> Dict[str, Any]:
    return draft(
        "OEA_EXECUTION_FAILED",
        {"binding_id": binding_id, "capability_id": capability_id, "reason": reason},
        causal_parents=[parent],
    )


def effect_receipt_recorded_draft(receipt: EffectReceipt, *, parent: str) -> Dict[str, Any]:
    return draft("OEA_EFFECT_RECEIPT_RECORDED", receipt.to_payload(), causal_parents=[parent])


def effect_receipted_draft(receipt: EffectReceipt, *, parent: str) -> Dict[str, Any]:
    return draft(
        "EFFECT_RECEIPTED",
        {
            "receipt_id": receipt.receipt_id,
            "commit_ref": receipt.ueak_commit_ref,
            "request_id": receipt.binding_id,
            "effect_class": receipt.capability_id,
            "status": receipt.result_status,
            "executor_mode": receipt.executor_mode,
            "output_hash": receipt.output_hash,
        },
        causal_parents=[parent],
    )


def lockdown_entered_draft(*, reason: str, parent: str) -> Dict[str, Any]:
    return draft("OEA_LOCKDOWN_ENTERED", {"reason": reason}, causal_parents=[parent])


def compensation_started_draft(binding_id: str, *, parent: str) -> Dict[str, Any]:
    return draft("OEA_COMPENSATION_STARTED", {"binding_id": binding_id}, causal_parents=[parent])


def compensation_completed_draft(binding_id: str, *, parent: str) -> Dict[str, Any]:
    return draft("OEA_COMPENSATION_COMPLETED", {"binding_id": binding_id}, causal_parents=[parent])


def compensation_failed_draft(binding_id: str, *, reason: str, parent: str) -> Dict[str, Any]:
    return draft(
        "OEA_COMPENSATION_FAILED",
        {"binding_id": binding_id, "reason": reason},
        causal_parents=[parent],
    )


__all__ = [
    "binding_created_draft",
    "binding_refused_draft",
    "compensation_completed_draft",
    "compensation_failed_draft",
    "compensation_started_draft",
    "dry_run_completed_draft",
    "dry_run_started_draft",
    "effect_receipt_recorded_draft",
    "effect_receipted_draft",
    "execution_completed_draft",
    "execution_failed_draft",
    "execution_refused_draft",
    "execution_requested_draft",
    "execution_started_draft",
    "lockdown_entered_draft",
]
