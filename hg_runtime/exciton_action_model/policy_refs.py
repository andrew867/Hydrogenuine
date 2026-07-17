"""Policy, proof, capability, and rate-limit references for action requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _frozen() -> dict[str, Any]:
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


@dataclass
class AgentActionPolicyRef:
    policy_id: str
    policy_kind: str = "unknown"
    label: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_kind": self.policy_kind,
            "label": self.label,
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "AgentActionPolicyRef":
        return cls(
            policy_id=data["policy_id"],
            policy_kind=data.get("policy_kind", "unknown"),
            label=data.get("label", ""),
        )


@dataclass
class AgentActionProofRef:
    proof_id: str
    path: str
    kind: str = "proof"

    def to_payload(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "path": self.path,
            "kind": self.kind,
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "AgentActionProofRef":
        return cls(
            proof_id=data["proof_id"],
            path=data.get("path", ""),
            kind=data.get("kind", "proof"),
        )


@dataclass
class AgentActionCapabilityRef:
    capability_id: str
    fabric_ref: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "fabric_ref": self.fabric_ref,
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "AgentActionCapabilityRef":
        return cls(
            capability_id=data["capability_id"],
            fabric_ref=data.get("fabric_ref", ""),
        )


@dataclass
class AgentActionRateLimitRef:
    bucket_id: str
    status: str = "OK"

    def to_payload(self) -> dict[str, Any]:
        return {
            "bucket_id": self.bucket_id,
            "status": self.status,
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "AgentActionRateLimitRef":
        return cls(
            bucket_id=data["bucket_id"],
            status=data.get("status", "OK"),
        )


@dataclass
class OperatorDecisionRef:
    decision_id: str
    operator_ref: str
    decision_kind: str
    created_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "operator_ref": self.operator_ref,
            "decision_kind": self.decision_kind,
            "created_at": self.created_at,
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "OperatorDecisionRef":
        return cls(
            decision_id=data["decision_id"],
            operator_ref=data["operator_ref"],
            decision_kind=data.get("decision_kind", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class ActionExecutionRef:
    execution_id: str
    receipt_ref: str
    executed_at: str
    outcome: str = "unknown"

    def to_payload(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "receipt_ref": self.receipt_ref,
            "executed_at": self.executed_at,
            "outcome": self.outcome,
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "ActionExecutionRef":
        return cls(
            execution_id=data["execution_id"],
            receipt_ref=data.get("receipt_ref", ""),
            executed_at=data.get("executed_at", ""),
            outcome=data.get("outcome", "unknown"),
        )


__all__ = [
    "ActionExecutionRef",
    "AgentActionCapabilityRef",
    "AgentActionPolicyRef",
    "AgentActionProofRef",
    "AgentActionRateLimitRef",
    "OperatorDecisionRef",
]
