"""AID mode card — live runtime mode disclosure, read-only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.ai_interaction_disclosure.types import AID_SCHEMA_VERSION, RuntimeMode

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


@dataclass(frozen=True)
class ModeCard:
    mode_card_id: str
    interaction_id: str
    runtime_mode: RuntimeMode
    proposal_only_status: bool
    external_action_status: str
    model_or_provider_label: str
    derived_from_live_state: bool
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "aid-mode-card",
            "schema_version": AID_SCHEMA_VERSION,
            "mode_card_id": self.mode_card_id,
            "interaction_id": self.interaction_id,
            "runtime_mode": self.runtime_mode,
            "proposal_only_status": self.proposal_only_status,
            "external_action_status": self.external_action_status,
            "model_or_provider_label": self.model_or_provider_label,
            "derived_from_live_state": self.derived_from_live_state,
            "created_at": self.created_at,
            "card_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def build_mode_card(fixture: Mapping[str, str], *, observed_at: str | None = None) -> ModeCard:
    """Derive mode card from live fixture state — never from cached claims."""
    runtime_mode: RuntimeMode = fixture.get("runtime_mode", "proposal_only")  # type: ignore[assignment]
    proposal_only = runtime_mode == "proposal_only" or fixture.get("proposal_only", "true").lower() == "true"
    external_action = "disabled" if proposal_only else fixture.get("external_action_status", "disabled")
    return ModeCard(
        mode_card_id=fixture.get("mode_card_id", f"mode-{fixture['disclosure_id']}"),
        interaction_id=fixture["disclosure_id"],
        runtime_mode=runtime_mode,
        proposal_only_status=proposal_only,
        external_action_status=external_action,
        model_or_provider_label=fixture.get("model_or_provider_label", "unproven"),
        derived_from_live_state=fixture.get("derived_from_live_state", "true").lower() == "true",
        created_at=observed_at or FIXTURE_CLOCK,
    )


__all__ = ["FIXTURE_CLOCK", "ModeCard", "build_mode_card"]
