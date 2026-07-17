"""SIM typed schemas — simulation is not reality."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.runtime_context.errors import RuntimeContextValidationError

SIM_SCHEMA_VERSION = "1.0"

ForbiddenActionCheck = Literal["passed", "failed", "not_applicable", "unknown"]


@dataclass(frozen=True)
class SimulationScenario:
    scenario_id: str
    proposal_ref: str
    starting_event_head: str
    starting_world_state_hash: str
    assumptions: tuple[str, ...]
    simulated_steps: tuple[str, ...]
    predicted_outcomes: tuple[str, ...]
    predicted_residue_refs: tuple[str, ...]
    uncertainty: str
    confidence: str
    forbidden_action_check: ForbiddenActionCheck
    created_at: str
    expiry: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_scenario_fields(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sim-simulation-scenario",
            "schema_version": SIM_SCHEMA_VERSION,
            "scenario_id": self.scenario_id,
            "proposal_ref": self.proposal_ref,
            "starting_event_head": self.starting_event_head,
            "starting_world_state_hash": self.starting_world_state_hash,
            "assumptions": list(self.assumptions),
            "simulated_steps": list(self.simulated_steps),
            "predicted_outcomes": list(self.predicted_outcomes),
            "predicted_residue_refs": list(self.predicted_residue_refs),
            "uncertainty": self.uncertainty,
            "confidence": self.confidence,
            "forbidden_action_check": self.forbidden_action_check,
            "created_at": self.created_at,
            "expiry": self.expiry,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_scenario_fields(scenario: SimulationScenario) -> None:
    if not scenario.scenario_id.strip():
        raise RuntimeContextValidationError("sim.validation.scenario_id", "scenario_id required")
    if not scenario.starting_event_head.strip():
        raise RuntimeContextValidationError("sim.validation.event_head", "starting_event_head required")
    if not scenario.starting_world_state_hash.startswith("sha256:"):
        raise RuntimeContextValidationError(
            "sim.validation.world_state_hash",
            "starting_world_state_hash must be sha256-pinned",
        )
    if "password=" in scenario.starting_world_state_hash.lower():
        raise RuntimeContextValidationError("sim.validation.secret", "secrets forbidden in scenario refs")


def scenario_from_fixture(fixture: dict[str, str]) -> SimulationScenario:
    return SimulationScenario(
        scenario_id=fixture["scenario_id"],
        proposal_ref=fixture.get("proposal_ref", "proposal:fixture"),
        starting_event_head=fixture.get("starting_event_head", "sha256:event-head-fixture"),
        starting_world_state_hash=fixture.get("starting_world_state_hash", "sha256:world-state-fixture"),
        assumptions=tuple(fixture.get("assumptions", "bounded model").split("|")),
        simulated_steps=tuple(fixture.get("simulated_steps", "observe|propose").split("|")),
        predicted_outcomes=tuple(fixture.get("predicted_outcomes", "advisory residue").split("|")),
        predicted_residue_refs=tuple(
            fixture.get("predicted_residue_refs", "residue:fixture").split("|")
        ),
        uncertainty=fixture.get("uncertainty", "bounded"),
        confidence=fixture.get("confidence", "low"),
        forbidden_action_check=fixture.get("forbidden_action_check", "passed"),  # type: ignore[arg-type]
        created_at=fixture.get("created_at", "2026-06-12T20:00:00.000000Z"),
        expiry=fixture.get("expiry", "2026-06-13T20:00:00.000000Z"),
    )


__all__ = [
    "ForbiddenActionCheck",
    "SIM_SCHEMA_VERSION",
    "SimulationScenario",
    "scenario_from_fixture",
    "validate_scenario_fields",
]
