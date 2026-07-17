"""PUB-EXT-LIVE types — publication release candidates are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.pub_ext_live.errors import PubExtValidationError
from hg_core.policy_safety.hashing import compute_record_hash

PUB_EXT_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T15:00:00.000000Z"

ReleaseKind = Literal["publish", "external_action", "disclosure", "withdrawal"]

_STALE_TIM_REFS = frozenset({"tim:missing", "freshness:missing", "tim:stale"})
_VALID_TIM_PREFIXES = ("tim:approval_window_ok", "tim:fresh:")

_BARE_PLACEHOLDER_REFS = frozenset(
    {"", "operator", "operator_id", "human", "user", "admin", "TBD", "unknown", "placeholder"}
)


def is_bare_operator_ref(operator_ref: str | None) -> bool:
    raw = str(operator_ref or "").strip()
    if not raw:
        return True
    if raw in _BARE_PLACEHOLDER_REFS:
        return True
    if ":" not in raw and not raw.startswith("op:"):
        return True
    return False


def is_valid_tim_freshness(freshness_ref: str | None) -> bool:
    raw = str(freshness_ref or "").strip()
    if not raw or raw in _STALE_TIM_REFS:
        return False
    return any(raw.startswith(prefix) for prefix in _VALID_TIM_PREFIXES)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise PubExtValidationError("pub_ext.validation.secret", "secrets forbidden in PUB-EXT records")


@dataclass(frozen=True)
class PublicationCandidate:
    candidate_id: str
    request_id: str
    release_kind: ReleaseKind
    content_digest: str
    disclosure_tier: str
    operator_ref: str | None = None
    rollback_plan_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.candidate_id, self.request_id, self.content_digest, str(self.operator_ref or "")
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "pub-ext-release-candidate",
            "schema_version": PUB_EXT_SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "request_id": self.request_id,
            "release_kind": self.release_kind,
            "content_digest": self.content_digest,
            "disclosure_tier": self.disclosure_tier,
            "authority_created": False,
            "permission_granted": False,
            "is_permit": False,
            "published": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.rollback_plan_ref:
            payload["rollback_plan_ref"] = self.rollback_plan_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class PublicationRequest:
    request_id: str
    release_kind: ReleaseKind
    content_digest: str
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    scope: str | None = None
    disclosure_policy_ref: str | None = None
    redaction_policy_ref: str | None = None
    rollback_plan_ref: str | None = None
    withdrawal_plan_ref: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    requires_gpp: bool = False
    requires_ueak: bool = False
    irreversible: bool = False
    irreversible_ack: bool = False
    treat_as_authority: bool = False
    observed_at: str = FIXTURE_CLOCK

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.request_id, self.content_digest, str(self.operator_ref or ""), str(self.scope or "")
        )
        if self.treat_as_authority:
            raise PubExtValidationError("pub_ext.validation.authority_created", "treat_as_authority forbidden")

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "pub-ext-release-request",
            "schema_version": PUB_EXT_SCHEMA_VERSION,
            "request_id": self.request_id,
            "release_kind": self.release_kind,
            "content_digest": self.content_digest,
            "requires_gpp": self.requires_gpp,
            "requires_ueak": self.requires_ueak,
            "irreversible": self.irreversible,
            "irreversible_ack": self.irreversible_ack,
            "authority_created": False,
            "permission_granted": False,
            "published": False,
            "observed_at": self.observed_at,
        }
        for key in (
            "operator_ref", "freshness_ref", "approval_expires_at", "scope",
            "disclosure_policy_ref", "redaction_policy_ref", "rollback_plan_ref",
            "withdrawal_plan_ref", "gpp_permit_ref", "ueak_admission_ref",
        ):
            val = getattr(self, key)
            if val:
                payload[key] = val
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class PublicationReceipt:
    receipt_id: str
    request_id: str
    candidate_id: str
    release_kind: ReleaseKind
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
            "schema": "pub-ext-release-receipt",
            "schema_version": PUB_EXT_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "candidate_id": self.candidate_id,
            "release_kind": self.release_kind,
            "status": self.status,
            "reason_code": self.reason_code,
            "authority_created": False,
            "permission_granted": False,
            "evidence_admissible": self.evidence_admissible,
            "published": False,
            "live_external_action": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class WithdrawalRecord:
    withdrawal_id: str
    receipt_id: str
    request_id: str
    content_digest: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "pub-ext-withdrawal-record",
            "schema_version": PUB_EXT_SCHEMA_VERSION,
            "withdrawal_id": self.withdrawal_id,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "content_digest": self.content_digest,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "published": False,
            "live_external_action": False,
        }


@dataclass(frozen=True)
class CompensationRecord:
    compensation_id: str
    withdrawal_id: str
    content_digest: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "pub-ext-compensation-record",
            "schema_version": PUB_EXT_SCHEMA_VERSION,
            "compensation_id": self.compensation_id,
            "withdrawal_id": self.withdrawal_id,
            "content_digest": self.content_digest,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "published": False,
        }


def request_from_fixture(fixture: dict[str, Any]) -> PublicationRequest:
    return PublicationRequest(
        request_id=fixture["request_id"],
        release_kind=fixture.get("release_kind", "publish"),  # type: ignore[arg-type]
        content_digest=fixture.get("content_digest", "digest:fixture"),
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        scope=fixture.get("scope"),
        disclosure_policy_ref=fixture.get("disclosure_policy_ref"),
        redaction_policy_ref=fixture.get("redaction_policy_ref"),
        rollback_plan_ref=fixture.get("rollback_plan_ref"),
        withdrawal_plan_ref=fixture.get("withdrawal_plan_ref"),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        requires_gpp=bool(fixture.get("requires_gpp", False)),
        requires_ueak=bool(fixture.get("requires_ueak", False)),
        irreversible=bool(fixture.get("irreversible", False)),
        irreversible_ack=bool(fixture.get("irreversible_ack", False)),
        treat_as_authority=bool(fixture.get("treat_as_authority", False)),
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
    )


__all__ = [
    "FIXTURE_CLOCK", "PUB_EXT_SCHEMA_VERSION", "CompensationRecord", "PublicationCandidate",
    "PublicationReceipt", "PublicationRequest", "ReleaseKind", "WithdrawalRecord",
    "is_bare_operator_ref", "is_valid_tim_freshness", "request_from_fixture",
]
