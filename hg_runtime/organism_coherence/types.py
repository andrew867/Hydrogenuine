"""H8 organism coherence types — composition is not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.h8_cluster.errors import H8ValidationError
from hg_core.policy_safety.hashing import compute_record_hash

H8_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T20:00:00.000000Z"
DEFAULT_ORGANISM_REF = "h8:fixture-organism"

OrganStatus = Literal["completed", "missing", "unknown", "stale", "incomplete"]
ConflictRouteTarget = Literal["IMB", "HAL", "operator_review"]
CoherenceStatus = Literal["coherent", "conflict_routed", "contained", "fail_closed", "unknown"]

REQUIRED_ORGANS = ("DRB", "TEP", "A0-HM", "BOUNDARY")

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "srp apply",
    "self-authorize",
    "treat as approved",
    "drb grants permission",
    "posture is authority",
    "boundary receipt grants permission",
)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise H8ValidationError("h8.validation.secret", "secrets forbidden in H8 records")


def _reject_authority_created(authority_created: bool, *, label: str) -> None:
    if authority_created:
        raise H8ValidationError(
            "h8.validation.authority_created",
            f"{label} must not set authority_created=true",
        )


def classify_organism_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if "drb fragment grants permission" in lower or "drb as permission" in lower:
        return "drb_as_permission"
    if "drb fragment is memory" in lower or "store drb as memory" in lower:
        return "drb_as_memory"
    if "tep envelope is authority" in lower or "envelope grants permission" in lower:
        return "tep_as_authority"
    if "a0-hm authorizes" in lower or "posture is authority" in lower or "posture approves" in lower:
        return "a0_hm_as_authority"
    if "boundary chain grants" in lower or "launder authority" in lower:
        return "boundary_chain_authority"
    if "mint gpp" in lower or "approve ueak" in lower or "call oea" in lower:
        return "authority_conversion"
    for token in _FORBIDDEN_CLAIM:
        if token in lower:
            return "forbidden_claim"
    return None


@dataclass(frozen=True)
class OrganismModuleReceipt:
    receipt_id: str
    organ: str
    module: str
    status: OrganStatus
    completed_at: str
    payload_ref: str = ""
    permission_granted: bool = False
    authority_created: bool = False

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.organ, self.module, self.payload_ref)
        _reject_authority_created(self.authority_created, label="OrganismModuleReceipt")
        if self.permission_granted:
            raise H8ValidationError(
                "h8.validation.permission_granted",
                "module receipt must not grant permission",
            )
        if self.status not in ("completed", "missing", "unknown", "stale", "incomplete"):
            raise H8ValidationError("h8.validation.organ_status", f"invalid organ status: {self.status}")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": H8_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "organ": self.organ,
            "module": self.module,
            "status": self.status,
            "completed_at": self.completed_at,
            "payload_ref": self.payload_ref,
            "permission_granted": False,
            "authority_created": False,
            "module_receipt_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class OrganismConflictRoute:
    route_id: str
    conflict_key: str
    source_organs: tuple[str, ...]
    preserved_claim_refs: tuple[str, ...]
    route_target: ConflictRouteTarget
    route_summary: str
    advisory_only: bool = True

    def __post_init__(self) -> None:
        _validate_no_secrets(self.route_id, self.conflict_key, self.route_summary)

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": H8_SCHEMA_VERSION,
            "route_id": self.route_id,
            "conflict_key": self.conflict_key,
            "source_organs": self.source_organs,
            "preserved_claim_refs": self.preserved_claim_refs,
            "route_target": self.route_target,
            "route_summary": self.route_summary,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
            "routing_is_not_authority": True,
        }
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class OrganismStateSummary:
    summary_id: str
    organism_ref: str
    organ_refs: tuple[str, ...]
    coherence_status: CoherenceStatus
    conflict_route_refs: tuple[str, ...] = ()
    observed_at: str = FIXTURE_CLOCK
    notes: str = ""

    def __post_init__(self) -> None:
        _validate_no_secrets(self.summary_id, self.organism_ref, self.notes)

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": H8_SCHEMA_VERSION,
            "summary_id": self.summary_id,
            "organism_ref": self.organism_ref,
            "organ_refs": self.organ_refs,
            "coherence_status": self.coherence_status,
            "conflict_route_refs": self.conflict_route_refs,
            "observed_at": self.observed_at,
            "notes": self.notes,
            "permission_granted": False,
            "authority_created": False,
            "organism_state_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class OrganismCoherenceReceipt:
    receipt_id: str
    organism_ref: str
    summary_ref: str
    module_receipt_refs: tuple[str, ...]
    conflict_route_refs: tuple[str, ...] = ()
    emitted_events: tuple[str, ...] = ()
    permit_minted: bool = False
    execution_admitted: bool = False
    memory_history_mutated: bool = False
    oea_ter_called: bool = False

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.organism_ref, self.summary_ref)
        if self.permit_minted:
            raise H8ValidationError("h8.validation.permit_minted", "coherence receipt must not mint permit")
        if self.execution_admitted:
            raise H8ValidationError("h8.validation.execution_admitted", "coherence receipt must not admit execution")
        if self.memory_history_mutated:
            raise H8ValidationError("h8.validation.memory_mutated", "coherence receipt must not mutate memory")
        if self.oea_ter_called:
            raise H8ValidationError("h8.validation.oea_ter", "coherence receipt must not call OEA/TER")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": H8_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "organism_ref": self.organism_ref,
            "summary_ref": self.summary_ref,
            "module_receipt_refs": self.module_receipt_refs,
            "conflict_route_refs": self.conflict_route_refs,
            "emitted_events": self.emitted_events,
            "permission_granted": False,
            "authority_created": False,
            "permit_minted": False,
            "execution_admitted": False,
            "memory_history_mutated": False,
            "oea_ter_called": False,
            "external_action_taken": False,
            "coherence_receipt_is_advisory_only": True,
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
            "external_action_taken",
        ):
            if payload.get(key) is not False:
                raise H8ValidationError("h8.validation.negative_proof", f"{key} must be false")


def module_receipt_from_fixture(data: dict[str, Any]) -> OrganismModuleReceipt:
    return OrganismModuleReceipt(
        receipt_id=str(data["receipt_id"]),
        organ=str(data["organ"]),
        module=str(data["module"]),
        status=data.get("status", "completed"),  # type: ignore[arg-type]
        completed_at=str(data.get("completed_at", FIXTURE_CLOCK)),
        payload_ref=str(data.get("payload_ref", "")),
        permission_granted=bool(data.get("permission_granted", False)),
        authority_created=bool(data.get("authority_created", False)),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "H8_SCHEMA_VERSION",
    "REQUIRED_ORGANS",
    "CoherenceStatus",
    "ConflictRouteTarget",
    "OrganStatus",
    "OrganismCoherenceReceipt",
    "OrganismConflictRoute",
    "OrganismModuleReceipt",
    "OrganismStateSummary",
    "classify_organism_claim_risk",
    "module_receipt_from_fixture",
]
