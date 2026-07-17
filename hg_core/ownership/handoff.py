"""Chapter2 handoff: receipt gating, claim validation, checkpoint proceed. Ref: .cursor/plans/autonomy/chapter2."""
from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Tuple

from .ownership_ledger import OwnershipLedger
from .ownership_models import HandoffOffer, HandoffReceipt
from .ownership_store import OwnershipStore


def validate_claim(claim: Dict[str, Any]) -> bool:
    """Validate claim per SPEC_OWNERSHIP_MODEL: claim_type lead|contributor; contributor must have scope."""
    claim_type = claim.get("claim_type")
    if claim_type not in ("lead", "contributor"):
        return False
    if claim_type == "contributor" and not claim.get("scope"):
        return False
    if not claim.get("agent_id") or not claim.get("work_item_id"):
        return False
    return True


def is_transfer_effective(store: OwnershipStore, ledger: OwnershipLedger, task_id: str) -> bool:
    """Transfer is effective only after an accepted receipt (accept_ownership or handoff_receipt with acceptance=accept)."""
    rec = store.get_task(task_id)
    if rec.state == "acknowledged" and rec.executor_id:
        return True
    events = ledger.list_events(task_id=task_id)
    last_offer_idx = -1
    for i, e in enumerate(events):
        if e.get("type") in ("offer_ownership", "handoff_offer"):
            last_offer_idx = i
    for i, e in enumerate(events):
        if i <= last_offer_idx:
            continue
        t = e.get("type", "")
        if t == "accept_ownership":
            return True
        if t == "handoff_receipt" and e.get("acceptance") in ("accept", "accept_with_changes"):
            return True
        if t == "decline_ownership" or (t == "handoff_receipt" and e.get("acceptance") == "reject"):
            return False
    return False


def can_proceed_from_checkpoint(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    checkpoint_id: str,
) -> bool:
    """Baton checkpoint: can proceed only if a handoff_receipt exists for this checkpoint_id with acceptance accept/accept_with_changes."""
    events = ledger.list_events(task_id=task_id)
    for e in events:
        if e.get("type") != "handoff_receipt":
            continue
        cid = e.get("checkpoint_id")
        acc = e.get("acceptance")
        if cid == checkpoint_id and acc in ("accept", "accept_with_changes"):
            return True
    return False


def record_handoff_offer(
    ledger: OwnershipLedger,
    task_id: str,
    offer: HandoffOffer,
    expected_version: Optional[int] = None,
) -> Dict[str, Any]:
    """Append handoff_offer event to ledger. work_item_id should equal task_id."""
    payload = {
        "work_item_id": offer.work_item_id,
        "from_agent_id": offer.from_agent_id,
        "to_agent_id": offer.to_agent_id,
        "claim_transfer": offer.claim_transfer,
        "current_state_summary": offer.current_state_summary,
        "artifacts": offer.artifacts,
        "known_risks_and_blockers": offer.known_risks_and_blockers,
        "suggested_next_actions": offer.suggested_next_actions,
        "required_checks_before_continuing": offer.required_checks_before_continuing,
        "timestamp": offer.timestamp or time.time(),
    }
    return ledger.append(task_id, "handoff_offer", offer.from_agent_id, payload, expected_version=expected_version)


def record_handoff_receipt(
    ledger: OwnershipLedger,
    task_id: str,
    receipt: HandoffReceipt,
    expected_version: Optional[int] = None,
) -> Dict[str, Any]:
    """Append handoff_receipt event to ledger."""
    payload = {
        "work_item_id": receipt.work_item_id,
        "receiver_agent_id": receipt.receiver_agent_id,
        "acceptance": receipt.acceptance,
        "receiver_state_understanding": receipt.receiver_state_understanding,
        "deltas": receipt.deltas,
        "updated_plan_for_next_actions": receipt.updated_plan_for_next_actions,
        "confirmation_artifacts_accessible": receipt.confirmation_artifacts_accessible,
        "confirmation_success_criteria_understood": receipt.confirmation_success_criteria_understood,
        "timestamp": receipt.timestamp or time.time(),
        "checkpoint_id": receipt.checkpoint_id,
    }
    return ledger.append(task_id, "handoff_receipt", receipt.receiver_agent_id, payload, expected_version=expected_version)
