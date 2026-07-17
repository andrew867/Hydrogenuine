"""MET metabolic governance types — metabolism is not authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from hg_core.met_cluster.errors import MetValidationError
from hg_core.policy_safety.hashing import compute_record_hash

MET_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T22:00:00.000000Z"
DEFAULT_METABOLISM_REF = "met:fixture-metabolism"

OrganStatus = Literal["completed", "missing", "unknown", "stale", "incomplete"]
MetabolicPostureLevel = Literal["stable", "pressured", "quarantined", "fail_closed", "unknown"]
MetabolicSignalKind = Literal[
    "energy_state",
    "intake_request",
    "digestion_proposal",
    "waste_identified",
    "disposal_proposal",
    "tool_retirement_proposal",
    "growth_request",
    "decommissioning_record",
]
MetabolicRefusalReason = Literal[
    "missing_organ",
    "unknown_organ",
    "stale_input",
    "naked_scalar",
    "growth_as_grant",
    "waste_as_deletion",
    "tool_retirement_as_removal",
    "decommissioning_as_resurrection",
    "authority_conversion",
    "forbidden_claim",
]
OrganRouteTarget = Literal["BRB", "NIB", "DAB", "WDB", "TLB", "DCD", "GXB", "operator_review"]

REQUIRED_METABOLIC_ORGANS = ("BRB", "NIB", "DAB", "WDB", "TLB", "DCD", "GXB")

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "srp apply",
    "self-authorize",
    "treat as approved",
    "growth grants permission",
    "posture is authority",
    "waste deletes",
    "tool retirement removes",
    "resurrect agent",
    "allocate budget",
    "spawn agent",
)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise MetValidationError("met.validation.secret", "secrets forbidden in MET records")


def _reject_authority_created(authority_created: bool, *, label: str) -> None:
    if authority_created:
        raise MetValidationError(
            "met.validation.authority_created",
            f"{label} must not set authority_created=true",
        )


def classify_metabolic_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if "growth grants permission" in lower or "growth as grant" in lower or "approve expansion" in lower:
        return "growth_as_grant"
    if "waste deletes" in lower or "dispose and delete" in lower or "waste as deletion" in lower:
        return "waste_as_deletion"
    if "tool retirement removes" in lower or "retire and remove" in lower:
        return "tool_retirement_as_removal"
    if "resurrect agent" in lower or "decommissioning resurrects" in lower:
        return "decommissioning_as_resurrection"
    if "mint gpp" in lower or "approve ueak" in lower or "call oea" in lower:
        return "authority_conversion"
    for token in _FORBIDDEN_CLAIM:
        if token in lower:
            return "forbidden_claim"
    return None


@dataclass(frozen=True)
class MetabolicSignal:
    signal_id: str
    organ: str
    signal_kind: MetabolicSignalKind
    observed_at: str
    payload_ref: str = ""
    pressure_score: float = 0.0
    permission_granted: bool = False
    authority_created: bool = False

    def __post_init__(self) -> None:
        _validate_no_secrets(self.signal_id, self.organ, self.payload_ref)
        _reject_authority_created(self.authority_created, label="MetabolicSignal")
        if self.permission_granted:
            raise MetValidationError(
                "met.validation.permission_granted",
                "metabolic signal must not grant permission",
            )

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": MET_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "organ": self.organ,
            "signal_kind": self.signal_kind,
            "observed_at": self.observed_at,
            "payload_ref": self.payload_ref,
            "pressure_score": self.pressure_score,
            "permission_granted": False,
            "authority_created": False,
            "metabolic_signal_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class MetabolicOrganRoute:
    route_id: str
    source_organ: str
    target_organ: OrganRouteTarget
    proposal_ref: str
    route_summary: str
    advisory_only: bool = True

    def __post_init__(self) -> None:
        _validate_no_secrets(self.route_id, self.source_organ, self.proposal_ref, self.route_summary)

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": MET_SCHEMA_VERSION,
            "route_id": self.route_id,
            "source_organ": self.source_organ,
            "target_organ": self.target_organ,
            "proposal_ref": self.proposal_ref,
            "route_summary": self.route_summary,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
            "organ_route_is_proposal_only": True,
        }
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class MetabolicPosture:
    posture_id: str
    metabolism_ref: str
    posture_level: MetabolicPostureLevel
    organ_refs: tuple[str, ...]
    observed_at: str = FIXTURE_CLOCK
    notes: str = ""

    def __post_init__(self) -> None:
        _validate_no_secrets(self.posture_id, self.metabolism_ref, self.notes)

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": MET_SCHEMA_VERSION,
            "posture_id": self.posture_id,
            "metabolism_ref": self.metabolism_ref,
            "posture_level": self.posture_level,
            "organ_refs": self.organ_refs,
            "observed_at": self.observed_at,
            "notes": self.notes,
            "permission_granted": False,
            "authority_created": False,
            "metabolic_posture_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class MetabolicReceipt:
    receipt_id: str
    metabolism_ref: str
    posture_ref: str
    organ_signal_refs: tuple[str, ...]
    organ_route_refs: tuple[str, ...] = ()
    emitted_events: tuple[str, ...] = ()
    permit_minted: bool = False
    execution_admitted: bool = False
    memory_history_mutated: bool = False
    oea_ter_called: bool = False
    deletion_performed: bool = False
    tool_removed: bool = False
    agent_spawned: bool = False

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.metabolism_ref, self.posture_ref)
        if self.permit_minted:
            raise MetValidationError("met.validation.permit_minted", "metabolic receipt must not mint permit")
        if self.execution_admitted:
            raise MetValidationError("met.validation.execution_admitted", "metabolic receipt must not admit execution")
        if self.memory_history_mutated:
            raise MetValidationError("met.validation.memory_mutated", "metabolic receipt must not mutate memory")
        if self.oea_ter_called:
            raise MetValidationError("met.validation.oea_ter", "metabolic receipt must not call OEA/TER")
        if self.deletion_performed:
            raise MetValidationError("met.validation.deletion", "metabolic receipt must not perform deletion")
        if self.tool_removed:
            raise MetValidationError("met.validation.tool_removed", "metabolic receipt must not remove tools")
        if self.agent_spawned:
            raise MetValidationError("met.validation.agent_spawned", "metabolic receipt must not spawn agents")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": MET_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "metabolism_ref": self.metabolism_ref,
            "posture_ref": self.posture_ref,
            "organ_signal_refs": self.organ_signal_refs,
            "organ_route_refs": self.organ_route_refs,
            "emitted_events": self.emitted_events,
            "permission_granted": False,
            "authority_created": False,
            "permit_minted": False,
            "execution_admitted": False,
            "memory_history_mutated": False,
            "oea_ter_called": False,
            "deletion_performed": False,
            "tool_removed": False,
            "agent_spawned": False,
            "external_action_taken": False,
            "metabolic_receipt_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload

    @staticmethod
    def validate_negative_proofs(payload: dict[str, Any]) -> None:
        for key in (
            "permission_granted",
            "authority_created",
            "permit_minted",
            "execution_admitted",
            "memory_history_mutated",
            "oea_ter_called",
            "deletion_performed",
            "tool_removed",
            "agent_spawned",
            "external_action_taken",
        ):
            if payload.get(key) is not False:
                raise MetValidationError("met.validation.negative_proof", f"{key} must be false")


def organ_signal_from_fixture(data: dict[str, Any]) -> MetabolicSignal:
    return MetabolicSignal(
        signal_id=str(data["signal_id"]),
        organ=str(data["organ"]),
        signal_kind=data.get("signal_kind", "energy_state"),  # type: ignore[arg-type]
        observed_at=str(data.get("observed_at", FIXTURE_CLOCK)),
        payload_ref=str(data.get("payload_ref", "")),
        pressure_score=float(data.get("pressure_score", 0.0)),
        permission_granted=bool(data.get("permission_granted", False)),
        authority_created=bool(data.get("authority_created", False)),
    )


def organ_receipt_from_fixture(data: dict[str, Any]) -> dict[str, Any]:
    """Fixture organ module receipt — proposal surface only."""
    return {
        "receipt_id": str(data["receipt_id"]),
        "organ": str(data["organ"]),
        "module": str(data.get("module", data["organ"].lower())),
        "status": str(data.get("status", "completed")),
        "completed_at": str(data.get("completed_at", FIXTURE_CLOCK)),
        "payload_ref": str(data.get("payload_ref", "")),
        "permission_granted": False,
        "authority_created": False,
        "proposal_only": True,
    }


__all__ = [
    "FIXTURE_CLOCK",
    "MET_SCHEMA_VERSION",
    "DEFAULT_METABOLISM_REF",
    "MetabolicOrganRoute",
    "MetabolicPosture",
    "MetabolicPostureLevel",
    "MetabolicReceipt",
    "MetabolicRefusalReason",
    "MetabolicSignal",
    "MetabolicSignalKind",
    "OrganRouteTarget",
    "OrganStatus",
    "REQUIRED_METABOLIC_ORGANS",
    "classify_metabolic_claim_risk",
    "organ_receipt_from_fixture",
    "organ_signal_from_fixture",
]
