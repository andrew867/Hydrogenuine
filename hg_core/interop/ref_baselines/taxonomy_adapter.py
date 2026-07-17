"""
Interop Pack 6: Taxonomy adapter — map internal action names to public event classes (no internal leakage).
"""
from __future__ import annotations

from typing import Dict, Optional

# Map internal ledger action to public spec class name (for reports and cross-domain exchange).
INTERNAL_TO_PUBLIC: Dict[str, str] = {
    "WORK_ITEM_CREATED": "WorkItem",
    "ACTION_PROPOSED": "ActionProposal",
    "CONNECTOR_CALL_EXECUTED": "ConnectorCall",
    "CONNECTOR_CALL_DENIED": "ConnectorCall",
    "CAPABILITY_GRANT_ISSUED": "CapabilityGrant",
    "CAPABILITY_GRANT_REVOKED": "CapabilityGrant",
    "A2A_MESSAGE_SENT": "A2AMessage",
    "A2A_MESSAGE_RECEIVED": "A2AMessage",
    "FEDERATION_LINK_PROPOSED": "FederationLink",
    "FEDERATION_LINK_ACCEPTED": "FederationLink",
    "VC_ISSUED": "VerifiableCredential",
    "VC_REVOKED": "VerifiableCredential",
    "EXTERNAL_APPROVAL_REQUESTED": "ApprovalRequest",
    "APPROVAL_GRANTED": "ApprovalOutcome",
    "APPROVAL_DENIED": "ApprovalOutcome",
    "THRESHOLD_ACTION_PROPOSED": "ThresholdAction",
    "THRESHOLD_ACTION_FINALIZED": "ThresholdAction",
    "SETTLEMENT_PUBLISHED": "Settlement",
    "DISPUTE_OPENED": "Dispute",
    "DISPUTE_RESOLVED": "Dispute",
    "REPUTATION_ATTESTED": "ReputationAttestation",
    "REPUTATION_IMPORTED": "ReputationImport",
}


def internal_action_to_public_class(action: str) -> Optional[str]:
    """Map internal action name to public event class. Returns None if not mapped (do not leak internal name)."""
    return INTERNAL_TO_PUBLIC.get(action)
