"""SEN-LIVE types — sensor observation candidates are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.sen_live.errors import SenValidationError
from hg_core.policy_safety.hashing import compute_record_hash

SEN_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T14:00:00.000000Z"

SensorModality = Literal["audio", "video", "scalar", "text", "proximity"]

_STALE_TIM_REFS = frozenset({"tim:missing", "freshness:missing", "tim:stale"})
_VALID_TIM_PREFIXES = ("tim:approval_window_ok", "tim:fresh:")

_BARE_PLACEHOLDER_REFS = frozenset(
    {
        "",
        "operator",
        "operator_id",
        "human",
        "user",
        "admin",
        "TBD",
        "unknown",
        "placeholder",
    }
)

_SCALAR_TRUTH_MARKERS = frozenset({"scalar:truth", "truth:scalar", "raw_scalar_authority"})


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


def is_scalar_truth_claim(observation_digest: str | None) -> bool:
    raw = str(observation_digest or "").strip().lower()
    return any(marker in raw for marker in _SCALAR_TRUTH_MARKERS)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise SenValidationError("sen.validation.secret", "secrets forbidden in SEN records")


@dataclass(frozen=True)
class SensorObservationCandidate:
    candidate_id: str
    request_id: str
    modality: SensorModality
    observation_digest: str
    privacy_tier: str
    operator_ref: str | None = None
    consent_ref: str | None = None
    redaction_policy_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.candidate_id,
            self.request_id,
            self.observation_digest,
            str(self.operator_ref or ""),
            str(self.consent_ref or ""),
            str(self.redaction_policy_ref or ""),
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sen-observation-candidate",
            "schema_version": SEN_SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "request_id": self.request_id,
            "modality": self.modality,
            "observation_digest": self.observation_digest,
            "privacy_tier": self.privacy_tier,
            "authority_created": False,
            "permission_granted": False,
            "is_permit": False,
            "observation_is_truth": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.consent_ref:
            payload["consent_ref"] = self.consent_ref
        if self.redaction_policy_ref:
            payload["redaction_policy_ref"] = self.redaction_policy_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SensorIngestRequest:
    request_id: str
    modality: SensorModality
    observation_digest: str
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    scope: str | None = None
    consent_ref: str | None = None
    redaction_policy_ref: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    requires_gpp: bool = False
    requires_ueak: bool = False
    treat_as_authority: bool = False
    observed_at: str = FIXTURE_CLOCK

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.request_id,
            self.observation_digest,
            str(self.operator_ref or ""),
            str(self.freshness_ref or ""),
            str(self.scope or ""),
            str(self.consent_ref or ""),
            str(self.redaction_policy_ref or ""),
        )
        if self.treat_as_authority:
            raise SenValidationError("sen.validation.authority_created", "treat_as_authority forbidden")

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sen-ingest-request",
            "schema_version": SEN_SCHEMA_VERSION,
            "request_id": self.request_id,
            "modality": self.modality,
            "observation_digest": self.observation_digest,
            "requires_gpp": self.requires_gpp,
            "requires_ueak": self.requires_ueak,
            "authority_created": False,
            "permission_granted": False,
            "observation_is_truth": False,
            "observed_at": self.observed_at,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.freshness_ref:
            payload["freshness_ref"] = self.freshness_ref
        if self.approval_expires_at:
            payload["approval_expires_at"] = self.approval_expires_at
        if self.scope:
            payload["scope"] = self.scope
        if self.consent_ref:
            payload["consent_ref"] = self.consent_ref
        if self.redaction_policy_ref:
            payload["redaction_policy_ref"] = self.redaction_policy_ref
        if self.gpp_permit_ref:
            payload["gpp_permit_ref"] = self.gpp_permit_ref
        if self.ueak_admission_ref:
            payload["ueak_admission_ref"] = self.ueak_admission_ref
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class SensorIngestReceipt:
    receipt_id: str
    request_id: str
    candidate_id: str
    modality: SensorModality
    status: str
    reason_code: str
    operator_ref: str | None = None
    evidence_admissible: bool = False
    redaction_applied: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.request_id, self.candidate_id, str(self.operator_ref or ""))
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sen-ingest-receipt",
            "schema_version": SEN_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "candidate_id": self.candidate_id,
            "modality": self.modality,
            "status": self.status,
            "reason_code": self.reason_code,
            "authority_created": False,
            "permission_granted": False,
            "evidence_admissible": self.evidence_admissible,
            "redaction_applied": self.redaction_applied,
            "live_sensor_connection": False,
            "observation_is_truth": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class QuarantineRecord:
    quarantine_id: str
    receipt_id: str
    request_id: str
    observation_digest: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "sen-quarantine-record",
            "schema_version": SEN_SCHEMA_VERSION,
            "quarantine_id": self.quarantine_id,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "observation_digest": self.observation_digest,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "live_sensor_connection": False,
        }


@dataclass(frozen=True)
class WithdrawalRecord:
    withdrawal_id: str
    quarantine_id: str
    observation_digest: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "sen-withdrawal-record",
            "schema_version": SEN_SCHEMA_VERSION,
            "withdrawal_id": self.withdrawal_id,
            "quarantine_id": self.quarantine_id,
            "observation_digest": self.observation_digest,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "live_sensor_connection": False,
        }


def request_from_fixture(fixture: dict[str, Any]) -> SensorIngestRequest:
    return SensorIngestRequest(
        request_id=fixture["request_id"],
        modality=fixture.get("modality", "text"),  # type: ignore[arg-type]
        observation_digest=fixture.get("observation_digest", "digest:fixture"),
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        scope=fixture.get("scope"),
        consent_ref=fixture.get("consent_ref"),
        redaction_policy_ref=fixture.get("redaction_policy_ref"),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        requires_gpp=bool(fixture.get("requires_gpp", False)),
        requires_ueak=bool(fixture.get("requires_ueak", False)),
        treat_as_authority=bool(fixture.get("treat_as_authority", False)),
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "SEN_SCHEMA_VERSION",
    "QuarantineRecord",
    "SensorIngestReceipt",
    "SensorIngestRequest",
    "SensorModality",
    "SensorObservationCandidate",
    "WithdrawalRecord",
    "is_bare_operator_ref",
    "is_scalar_truth_claim",
    "is_valid_tim_freshness",
    "request_from_fixture",
]
