"""Domain pack activation receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.domain_packs.schemas import DomainPackError, validate_activation_receipt

PHASE26_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER"
PHASE27_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_27_SKILL_GRAPH_TRANSFER_ENGINE"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def activate_domain_pack(
    pack: Mapping[str, Any],
    *,
    phase26_verdict: str,
    phase27_verdict: str,
    receipt_refs: list[str],
    control: OperationControl | None = None,
    activated_at: str | None = None,
) -> dict[str, Any]:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=True)
    if reason:
        raise DomainPackError(reason)
    if phase26_verdict != PHASE26_GREEN or phase27_verdict != PHASE27_GREEN:
        raise DomainPackError("phase28_activation_requires_phase26_and_phase27_green")
    receipt = validate_activation_receipt(
        {
            "domain_id": pack["domain_id"],
            "version": pack["version"],
            "pack_hash": pack["pack_hash"],
            "phase26_verdict": phase26_verdict,
            "phase27_verdict": phase27_verdict,
            "receipt_refs": receipt_refs,
            "claim_boundary": "activation_is_advisory_only",
            "activated_at": activated_at or _utc_now(),
        }
    )
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


__all__ = ["PHASE26_GREEN", "PHASE27_GREEN", "activate_domain_pack"]
