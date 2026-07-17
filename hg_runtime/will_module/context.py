"""WillContext — runtime attachment surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.will_module.envelope import WillEnvelope
from hg_runtime.will_module.policy import check_expiry, check_veto
from hg_runtime.will_module.receipts import WillReceipt, WillTrace


@dataclass
class WillContext:
    envelope: WillEnvelope
    receipt: WillReceipt | None = None
    trace: WillTrace | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "will-context",
            "envelope": self.envelope.to_payload(),
            "will_hash": self.envelope.hash,
            "allowed_domains": list(self.envelope.allowed_domains),
            "disallowed_domains": list(self.envelope.disallowed_domains),
            "veto_state": self.envelope.veto_state.value,
            "consent_posture": self.envelope.consent_posture.value,
            "persistence_budget": self.envelope.persistence_budget.to_payload(),
            "reaffirmation_required": self.envelope.reaffirmation_required or check_expiry(self.envelope).value == "REQUEST_REAFFIRMATION",
            "attention_target": self.envelope.attention_target.target,
            "meaning_anchor": self.envelope.meaning_anchor,
            "will_is_not_permission": True,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        if self.receipt:
            payload["receipt"] = self.receipt.to_payload()
        if self.trace:
            payload["trace_event_count"] = len(self.trace.events)
        return payload

    def veto_effect(self, domain: str) -> str:
        return check_veto(self.envelope, domain=domain).value


__all__ = ["WillContext"]
