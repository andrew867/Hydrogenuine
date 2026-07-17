"""Organ WILL integration — advisory hints only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.will_module.context import WillContext

ORGAN_WILL_EFFECTS: dict[str, str] = {
    "organ:Agent0": "posture_and_task_direction",
    "organ:AIS": "advisory_inference_salience",
    "organ:IMS": "provider_selection_hints_only",
    "organ:MBS": "bus_labels_only",
    "organ:OEF": "critique_intent_drift",
    "organ:NRV": "routing_priority_hints_only",
    "organ:HRT": "heartbeat_reason_labels_only",
    "organ:RSP": "token_budget_requests_only",
    "organ:CIR": "resource_priority_hints_only",
    "organ:DBB": "retrieval_relevance_annotation",
    "organ:ISB": "salience_framing_only",
    "organ:OCF": "critique_context_only",
    "organ:OIR": "critique_context_only",
    "organ:MBR": "critique_context_only",
    "organ:StorageObserver": "metadata_only",
    "organ:AuthorityObserver": "verify_no_authorization",
    "organ:ToolBrokerObserver": "request_context_only",
}


@dataclass
class OrganWillContext:
    organ_id: str
    effect: str
    will_context: WillContext
    may_authorize: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "organ-will-context",
            "organ_id": self.organ_id,
            "effect": self.effect,
            "will_hash": self.will_context.envelope.hash,
            "attention_target": self.will_context.envelope.attention_target.target,
            "may_authorize": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def attach_will_to_organs(will_context: WillContext, organ_ids: list[str] | None = None) -> list[OrganWillContext]:
    contexts: list[OrganWillContext] = []
    ids = organ_ids or list(ORGAN_WILL_EFFECTS.keys())
    for organ_id in ids:
        effect = ORGAN_WILL_EFFECTS.get(organ_id, "advisory_metadata_only")
        contexts.append(OrganWillContext(organ_id=organ_id, effect=effect, will_context=will_context))
    return contexts


__all__ = ["ORGAN_WILL_EFFECTS", "OrganWillContext", "attach_will_to_organs"]
