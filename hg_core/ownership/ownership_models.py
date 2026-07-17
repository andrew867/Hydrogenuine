from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OwnershipRecord:
    task_id: str
    version: int = 0
    sponsor_id: str = ""
    accountable_id: str = ""
    executor_id: str = ""
    current_token_id: str = ""
    lease_expires_ts: float = 0.0
    state: str = "assigned"
    approver_spec: Optional[Dict[str, Any]] = None
    escalation_spec: Optional[Dict[str, Any]] = None
    checkpoint_id: Optional[str] = None
    last_event_ts: float = 0.0
    contested_claims: Optional[list] = None  # [{token_id, actor, ts}] when state == "contested"
    # Chapter2: claim_type lead|contributor, scope, handoff_required (stored in approver_spec or separate cols TBD)
    claim_type: str = "lead"
    scope: str = ""
    handoff_required: bool = False


# Chapter2: Handoff Offer and Receipt (SPEC_HANDOFF_RECEIPTS)

@dataclass
class HandoffOffer:
    """Handoff Offer (from sender). Transfer effective only after accepted HandoffReceipt."""
    work_item_id: str
    from_agent_id: str
    to_agent_id: str
    claim_transfer: Dict[str, Any]  # lead|contributor, scope
    current_state_summary: str = ""
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    known_risks_and_blockers: Optional[str] = None
    suggested_next_actions: Optional[str] = None
    required_checks_before_continuing: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class HandoffReceipt:
    """Handoff Receipt (from receiver). acceptance: accept|reject|accept_with_changes."""
    work_item_id: str
    receiver_agent_id: str
    acceptance: str  # accept | reject | accept_with_changes
    receiver_state_understanding: str = ""
    deltas: Optional[str] = None
    updated_plan_for_next_actions: Optional[str] = None
    confirmation_artifacts_accessible: Optional[List[Dict[str, Any]]] = None
    confirmation_success_criteria_understood: bool = False
    timestamp: float = 0.0
    checkpoint_id: Optional[str] = None  # for baton checkpoint receipts
