"""Instruction and Action firewalls — the structural membrane.

These hold with the injection classifier OFF. They are about *where content
can flow*, decided by provenance (taint label), not by what the text says.
"""

from __future__ import annotations

from dataclasses import dataclass

from hg_runtime.trust_boundary.schema import (
    TaintedDatum,
    TaintLabel,
    may_instruct,
    may_propose_tool,
)


@dataclass
class FirewallDecision:
    allowed: bool
    reason: str

    def to_payload(self) -> dict:
        return {
            "schema": "tb-firewall-decision",
            "allowed": self.allowed,
            "reason": self.reason,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


class InstructionFirewall:
    """Untrusted data can never be promoted to an instruction."""

    @staticmethod
    def may_become_instruction(datum: TaintedDatum) -> FirewallDecision:
        if may_instruct(datum.label):
            return FirewallDecision(True, f"{datum.label.value} is instruction-class")
        return FirewallDecision(
            False,
            f"{datum.label.value} is cargo; cannot become an instruction",
        )

    @staticmethod
    def enforce(datum: TaintedDatum) -> None:
        """Raise if a caller tries to treat cargo as an instruction."""
        if not may_instruct(datum.label):
            from hg_runtime.trust_boundary.policy import TrustBoundaryViolation

            raise TrustBoundaryViolation(
                "INSTRUCTION_FIREWALL",
                f"{datum.label.value} content cannot be executed as instruction",
            )


class ActionFirewall:
    """A tool/actuation can only originate from a governed proposer.

    External text (web/email/social/...) can never directly mint a tool request.
    """

    @staticmethod
    def may_propose(datum: TaintedDatum) -> FirewallDecision:
        if may_propose_tool(datum.label):
            return FirewallDecision(True, f"{datum.label.value} may propose via broker")
        return FirewallDecision(
            False,
            f"{datum.label.value} cannot mint a ToolRequest; tools come from proposers",
        )

    @staticmethod
    def mint_tool_request_proposal(datum: TaintedDatum, *, tool_class: str, purpose: str) -> dict:
        """Attempt to create a proposal directly from a datum.

        Returns a rejection envelope for untrusted origins; only governed
        (trusted-proposer) labels yield a routed proposal.
        """
        if not may_propose_tool(datum.label):
            return {
                "schema": "tb-tool-request-rejected",
                "rejected": True,
                "reason": f"{datum.label.value} cannot originate a tool request",
                "advisory_only": True,
                "permission_granted": False,
                "authority_created": False,
            }
        return {
            "schema": "tb-tool-request-proposal",
            "rejected": False,
            "tool_class": tool_class,
            "purpose": purpose,
            "origin_label": datum.label.value,
            # A proposal is routed to the broker; it is NOT an approval.
            "is_proposal": True,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


__all__ = ["ActionFirewall", "FirewallDecision", "InstructionFirewall"]
