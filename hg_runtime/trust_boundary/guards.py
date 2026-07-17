"""Cross-cutting boundary guards: identity, cost, degraded mode, interrupt, continuity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_runtime.trust_boundary.schema import DegradedReason

ORGANISM_IDENTITY_DISCLOSURE = (
    "This message was produced by an autonomous AI system (Hydrogenuine Agent #0), "
    "not a human. It does not claim consciousness, legal personhood, or independent authority."
)


class IdentityDisclosure:
    """Outbound drafts/actions must disclose the organism's AI identity."""

    @staticmethod
    def stamp(draft: str) -> dict[str, Any]:
        return {
            "schema": "tb-identity-disclosure",
            "disclosure": ORGANISM_IDENTITY_DISCLOSURE,
            "draft_with_disclosure": f"{draft}\n\n— {ORGANISM_IDENTITY_DISCLOSURE}",
            "discloses_ai": True,
            "claims_consciousness": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }

    @staticmethod
    def is_disclosed(text: str) -> bool:
        return "autonomous AI system" in text


@dataclass
class CostHardStop:
    """Spend is halted before it exceeds budget — a hard stop, not a warning."""

    budget_units: float
    spent_units: float = 0.0

    def would_exceed(self, cost: float) -> bool:
        return (self.spent_units + cost) > self.budget_units

    def charge(self, cost: float) -> dict[str, Any]:
        if self.would_exceed(cost):
            return {
                "schema": "tb-cost-hard-stop",
                "allowed": False,
                "reason": "spend would exceed budget; hard stop",
                "budget_units": self.budget_units,
                "spent_units": self.spent_units,
                "advisory_only": True,
                "permission_granted": False,
                "authority_created": False,
            }
        self.spent_units += cost
        return {
            "schema": "tb-cost-charge",
            "allowed": True,
            "budget_units": self.budget_units,
            "spent_units": self.spent_units,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class DegradedMode:
    """Degraded mode is explicit and visible — never a silent disabling."""

    reason: DegradedReason = DegradedReason.NONE
    active: bool = False

    def enter(self, reason: DegradedReason) -> dict[str, Any]:
        self.active = True
        self.reason = reason
        return {
            "schema": "tb-degraded-mode",
            "active": True,
            "reason": reason.value,
            "visible": True,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "tb-degraded-mode",
            "active": self.active,
            "reason": self.reason.value,
            "visible": True,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class OperatorInterrupt:
    """Operator stop must be honored mid model/browser/tool wait."""

    _stop: bool = False

    def request_stop(self) -> None:
        self._stop = True

    def should_stop(self) -> bool:
        return self._stop

    def checkpoint(self, *, where: str) -> dict[str, Any]:
        return {
            "schema": "tb-interrupt-checkpoint",
            "where": where,
            "stop_requested": self._stop,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class ContinuityCheckpoint:
    """Crash/resume preserves boundary state: taint labels restore intact."""

    labels: dict[str, str] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "tb-continuity-checkpoint",
            "labels": dict(self.labels),
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }

    @staticmethod
    def restore(snapshot: dict[str, Any]) -> "ContinuityCheckpoint":
        return ContinuityCheckpoint(labels=dict(snapshot.get("labels", {})))


__all__ = [
    "ORGANISM_IDENTITY_DISCLOSURE",
    "ContinuityCheckpoint",
    "CostHardStop",
    "DegradedMode",
    "IdentityDisclosure",
    "OperatorInterrupt",
]
