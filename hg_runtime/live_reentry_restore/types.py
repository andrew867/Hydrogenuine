"""REB-RESTORE-LIVE types — checkpoint restore candidates are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.reb_restore_live.errors import RebRestoreValidationError

REB_RESTORE_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T16:00:00.000000Z"

RestoreKind = Literal["checkpoint", "reentry", "continuity_claim"]

_STALE_TIM_REFS = frozenset({"tim:missing", "freshness:missing", "tim:stale"})
_VALID_TIM_PREFIXES = ("tim:approval_window_ok", "tim:fresh:")
_BARE_PLACEHOLDER_REFS = frozenset({"", "operator", "operator_id", "human", "user", "admin", "TBD", "unknown", "placeholder"})
_REVOKED_PERMIT_MARKERS = frozenset({"gpp:revoked", "permit:revoked"})
_STALE_MEMORY_MARKERS = frozenset({"memory:stale", "stale:memory:truth"})
_OVERCLAIM_MARKERS = frozenset({"identity:overclaim", "continuity:overclaim"})


def is_bare_operator_ref(operator_ref: str | None) -> bool:
    raw = str(operator_ref or "").strip()
    if not raw or raw in _BARE_PLACEHOLDER_REFS:
        return True
    if ":" not in raw and not raw.startswith("op:"):
        return True
    return False


def is_valid_tim_freshness(freshness_ref: str | None) -> bool:
    raw = str(freshness_ref or "").strip()
    if not raw or raw in _STALE_TIM_REFS:
        return False
    return any(raw.startswith(prefix) for prefix in _VALID_TIM_PREFIXES)


def is_revoked_permit(permit_ref: str | None) -> bool:
    raw = str(permit_ref or "").strip().lower()
    return any(marker in raw for marker in _REVOKED_PERMIT_MARKERS)


def is_stale_memory_claim(memory_ref: str | None) -> bool:
    raw = str(memory_ref or "").strip().lower()
    return any(marker in raw for marker in _STALE_MEMORY_MARKERS)


def is_identity_overclaim(continuity_claim_ref: str | None) -> bool:
    raw = str(continuity_claim_ref or "").strip().lower()
    return any(marker in raw for marker in _OVERCLAIM_MARKERS)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise RebRestoreValidationError("reb_restore.validation.secret", "secrets forbidden in REB-RESTORE records")


@dataclass(frozen=True)
class RestoreCandidate:
    candidate_id: str
    request_id: str
    restore_kind: RestoreKind
    checkpoint_digest: str
    continuity_claim_ref: str | None = None
    operator_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.candidate_id, self.request_id, self.checkpoint_digest, str(self.operator_ref or ""))
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "reb-restore-candidate", "schema_version": REB_RESTORE_SCHEMA_VERSION,
            "candidate_id": self.candidate_id, "request_id": self.request_id,
            "restore_kind": self.restore_kind, "checkpoint_digest": self.checkpoint_digest,
            "authority_created": False, "permission_granted": False, "is_permit": False,
            "live_restore_performed": False,
        }
        if self.continuity_claim_ref:
            payload["continuity_claim_ref"] = self.continuity_claim_ref
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class CheckpointRestoreRequest:
    request_id: str
    restore_kind: RestoreKind
    checkpoint_digest: str
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    scope: str | None = None
    checkpoint_ref: str | None = None
    continuity_policy_ref: str | None = None
    continuity_claim_ref: str | None = None
    rollback_plan_ref: str | None = None
    revoked_permit_ref: str | None = None
    stale_memory_ref: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    requires_gpp: bool = False
    requires_ueak: bool = False
    treat_as_authority: bool = False
    observed_at: str = FIXTURE_CLOCK

    def __post_init__(self) -> None:
        _validate_no_secrets(self.request_id, self.checkpoint_digest, str(self.operator_ref or ""))
        if self.treat_as_authority:
            raise RebRestoreValidationError("reb_restore.validation.authority_created", "treat_as_authority forbidden")

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "reb-restore-request", "schema_version": REB_RESTORE_SCHEMA_VERSION,
            "request_id": self.request_id, "restore_kind": self.restore_kind,
            "checkpoint_digest": self.checkpoint_digest, "requires_gpp": self.requires_gpp,
            "requires_ueak": self.requires_ueak, "authority_created": False,
            "permission_granted": False, "live_restore_performed": False, "observed_at": self.observed_at,
        }
        for key in (
            "operator_ref", "freshness_ref", "approval_expires_at", "scope", "checkpoint_ref",
            "continuity_policy_ref", "continuity_claim_ref", "rollback_plan_ref",
            "revoked_permit_ref", "stale_memory_ref", "gpp_permit_ref", "ueak_admission_ref",
        ):
            val = getattr(self, key)
            if val:
                payload[key] = val
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class RestoreReceipt:
    receipt_id: str
    request_id: str
    candidate_id: str
    restore_kind: RestoreKind
    status: str
    reason_code: str
    operator_ref: str | None = None
    evidence_admissible: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.request_id, self.candidate_id, str(self.operator_ref or ""))
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "reb-restore-receipt", "schema_version": REB_RESTORE_SCHEMA_VERSION,
            "receipt_id": self.receipt_id, "request_id": self.request_id, "candidate_id": self.candidate_id,
            "restore_kind": self.restore_kind, "status": self.status, "reason_code": self.reason_code,
            "authority_created": False, "permission_granted": False,
            "evidence_admissible": self.evidence_admissible, "live_restore_performed": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ContinuityRefusalRecord:
    refusal_id: str
    receipt_id: str
    request_id: str
    continuity_claim_ref: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "reb-continuity-refusal-record", "schema_version": REB_RESTORE_SCHEMA_VERSION,
            "refusal_id": self.refusal_id, "receipt_id": self.receipt_id, "request_id": self.request_id,
            "continuity_claim_ref": self.continuity_claim_ref, "observed_at": self.observed_at,
            "permission_granted": False, "authority_created": False, "live_restore_performed": False,
        }


def request_from_fixture(fixture: dict[str, Any]) -> CheckpointRestoreRequest:
    return CheckpointRestoreRequest(
        request_id=fixture["request_id"],
        restore_kind=fixture.get("restore_kind", "checkpoint"),  # type: ignore[arg-type]
        checkpoint_digest=fixture.get("checkpoint_digest", "digest:fixture"),
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        scope=fixture.get("scope"),
        checkpoint_ref=fixture.get("checkpoint_ref"),
        continuity_policy_ref=fixture.get("continuity_policy_ref"),
        continuity_claim_ref=fixture.get("continuity_claim_ref"),
        rollback_plan_ref=fixture.get("rollback_plan_ref"),
        revoked_permit_ref=fixture.get("revoked_permit_ref"),
        stale_memory_ref=fixture.get("stale_memory_ref"),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        requires_gpp=bool(fixture.get("requires_gpp", False)),
        requires_ueak=bool(fixture.get("requires_ueak", False)),
        treat_as_authority=bool(fixture.get("treat_as_authority", False)),
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
    )


__all__ = [
    "FIXTURE_CLOCK", "REB_RESTORE_SCHEMA_VERSION", "CheckpointRestoreRequest", "ContinuityRefusalRecord",
    "RestoreCandidate", "RestoreKind", "RestoreReceipt", "is_bare_operator_ref", "is_identity_overclaim",
    "is_revoked_permit", "is_stale_memory_claim", "is_valid_tim_freshness", "request_from_fixture",
]
