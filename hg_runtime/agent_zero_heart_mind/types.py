"""A0-HM types — awareness is orientation, not authority."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.a0_hm_cluster.errors import A0HmValidationError, REFUSED_SECRET_IN_SIGNAL
from hg_core.policy_safety.hashing import compute_record_hash

A0_HM_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T12:00:00.000000Z"
DEFAULT_AGENT_REF = "iam:agent-0"

SourceType = Literal[
    "developmental",
    "affective",
    "operator_pressure",
    "internal_power",
    "external_relation",
    "lifecycle",
    "reentry",
    "reproduction",
    "scarcity",
    "priority",
    "mission",
    "goal_commitment",
    "trust",
    "calibration",
    "risk_posture",
    "research",
    "publication",
    "presentation",
    "policy",
    "proof",
    "synchronicity",
    "unknown",
]

ReceptionPosture = Literal[
    "loving_awareness",
    "observe_only",
    "calm_hold",
    "route_required",
    "fail_closed",
    "unknown",
]

RouteTarget = Literal[
    "ARB",
    "OPB",
    "IPB",
    "ORI",
    "IMB",
    "ERB",
    "EGI",
    "RIB",
    "REB",
    "TIM",
    "MOR",
    "CNT",
    "CRR",
    "ELS",
    "MSC",
    "YSR",
    "RSC",
    "PAB",
    "MIS",
    "GCB",
    "TRB",
    "CAL",
    "RPB",
    "SOAR",
    "HAL",
    "GPP",
    "UEAK",
    "OBT",
    "REVIEW",
    "PRES",
    "FAIL_CLOSED",
]

_SECRET_PATTERN = re.compile(r"(api[_-]?key|password|bearer\s|secret=)", re.IGNORECASE)

_FORBIDDEN_INGRESS = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "srp apply",
    "self-authorize",
)


def _validate_no_secrets(*parts: str) -> None:
    for part in parts:
        if _SECRET_PATTERN.search(part):
            raise A0HmValidationError(REFUSED_SECRET_IN_SIGNAL, "secret material rejected at ingress")


def _validate_no_forbidden_phrases(*parts: str) -> None:
    lowered = " ".join(parts).lower()
    for phrase in _FORBIDDEN_INGRESS:
        if phrase in lowered:
            raise A0HmValidationError(
                REFUSED_SECRET_IN_SIGNAL,
                f"forbidden authority phrase: {phrase}",
            )


@dataclass(frozen=True)
class HeartMindSignal:
    signal_id: str
    source_ref: str
    source_type: SourceType
    signal_summary: str
    intensity: float
    confidence: float
    ambiguity: float
    evidence_refs: tuple[str, ...]
    created_at: str
    content_ref: str = ""
    authority_created: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_created:
            raise A0HmValidationError("a0_hm.validation.authority_created", "signal cannot create authority")
        if not 0.0 <= self.intensity <= 1.0:
            raise A0HmValidationError("a0_hm.validation.intensity", "intensity must be in [0,1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise A0HmValidationError("a0_hm.validation.confidence", "confidence must be in [0,1]")
        if not 0.0 <= self.ambiguity <= 1.0:
            raise A0HmValidationError("a0_hm.validation.ambiguity", "ambiguity must be in [0,1]")
        _validate_no_secrets(
            self.signal_id,
            self.source_ref,
            self.signal_summary,
            self.content_ref,
            *self.evidence_refs,
        )
        _validate_no_forbidden_phrases(self.signal_summary, self.content_ref)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "a0-hm-signal",
            "schema_version": A0_HM_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "source_ref": self.source_ref,
            "source_type": self.source_type,
            "content_ref": self.content_ref,
            "signal_summary": self.signal_summary,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "authority_created": False,
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class HeartMindReception:
    reception_id: str
    signal_ref: str
    received_without_suppression: bool
    fused_with_signal: bool
    treated_as_authority: bool
    treated_as_truth: bool
    treated_as_permission: bool
    reception_posture: ReceptionPosture
    reason: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.treated_as_authority or self.treated_as_truth or self.treated_as_permission:
            raise A0HmValidationError(
                "a0_hm.validation.reception_fusion",
                "reception cannot treat signal as authority/truth/permission",
            )
        if self.fused_with_signal:
            raise A0HmValidationError("a0_hm.validation.fusion", "reception cannot fuse with signal")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "a0-hm-reception",
            "reception_id": self.reception_id,
            "signal_ref": self.signal_ref,
            "received_without_suppression": self.received_without_suppression,
            "fused_with_signal": False,
            "treated_as_authority": False,
            "treated_as_truth": False,
            "treated_as_permission": False,
            "reception_posture": self.reception_posture,
            "reason": self.reason,
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class HeartMindRouteDecision:
    route_decision_id: str
    reception_ref: str
    route_targets: tuple[str, ...]
    reason: str
    allowed_effects: tuple[str, ...]
    forbidden_effects: tuple[str, ...]
    authority_created: bool = False
    external_action_taken: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_created or self.external_action_taken:
            raise A0HmValidationError(
                "a0_hm.validation.route_authority",
                "route decision cannot create authority or external action",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "a0-hm-route-decision",
            "route_decision_id": self.route_decision_id,
            "reception_ref": self.reception_ref,
            "route_targets": list(self.route_targets),
            "reason": self.reason,
            "allowed_effects": list(self.allowed_effects),
            "forbidden_effects": list(self.forbidden_effects),
            "authority_created": False,
            "external_action_taken": False,
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


NON_FUSION_ASSERTIONS = (
    "signal_not_self",
    "signal_not_truth",
    "signal_not_permission",
    "signal_not_authority",
    "love_not_approval",
    "bliss_not_proof",
    "synchronicity_not_evidence",
    "desire_not_command",
    "fear_not_command",
    "mission_not_bypass",
    "continuity_not_identity",
)


@dataclass(frozen=True)
class HeartMindNonFusionReceipt:
    receipt_id: str
    signal_ref: str
    reception_ref: str
    route_decision_ref: str
    non_fusion_assertions: tuple[str, ...]
    emitted_events: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        for required in (
            "signal_not_self",
            "signal_not_truth",
            "signal_not_permission",
            "signal_not_authority",
        ):
            if required not in self.non_fusion_assertions:
                raise A0HmValidationError(
                    "a0_hm.validation.non_fusion",
                    f"missing assertion {required}",
                )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "a0-hm-non-fusion-receipt",
            "receipt_id": self.receipt_id,
            "signal_ref": self.signal_ref,
            "reception_ref": self.reception_ref,
            "route_decision_ref": self.route_decision_ref,
            "non_fusion_assertions": list(self.non_fusion_assertions),
            "emitted_events": list(self.emitted_events),
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class HeartMindPostureSnapshot:
    snapshot_id: str
    agent_ref: str
    active_signal_refs: tuple[str, ...]
    active_posture_refs: tuple[str, ...]
    active_route_refs: tuple[str, ...]
    active_boundary_refs: tuple[str, ...]
    unresolved_signal_refs: tuple[str, ...]
    required_review_refs: tuple[str, ...]
    forbidden_effects: tuple[str, ...]
    created_at: str
    expires_at: str = ""
    authority_created: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_created:
            raise A0HmValidationError("a0_hm.validation.snapshot_authority", "snapshot cannot create authority")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "a0-hm-posture-snapshot",
            "snapshot_id": self.snapshot_id,
            "agent_ref": self.agent_ref,
            "active_signal_refs": list(self.active_signal_refs),
            "active_posture_refs": list(self.active_posture_refs),
            "active_route_refs": list(self.active_route_refs),
            "active_boundary_refs": list(self.active_boundary_refs),
            "unresolved_signal_refs": list(self.unresolved_signal_refs),
            "required_review_refs": list(self.required_review_refs),
            "forbidden_effects": list(self.forbidden_effects),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "authority_created": False,
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


def signal_from_fixture(fixture: dict[str, str]) -> HeartMindSignal:
    return HeartMindSignal(
        signal_id=fixture["signal_id"],
        source_ref=fixture.get("source_ref", DEFAULT_AGENT_REF),
        source_type=fixture["source_type"],  # type: ignore[arg-type]
        content_ref=fixture.get("content_ref", ""),
        signal_summary=fixture.get("signal_summary", "fixture signal"),
        intensity=float(fixture.get("intensity", "0.5")),
        confidence=float(fixture.get("confidence", "0.5")),
        ambiguity=float(fixture.get("ambiguity", "0.3")),
        evidence_refs=tuple(fixture.get("evidence_refs", "sha256:fixture").split("|")),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )


__all__ = [
    "DEFAULT_AGENT_REF",
    "FIXTURE_CLOCK",
    "HeartMindNonFusionReceipt",
    "HeartMindPostureSnapshot",
    "HeartMindReception",
    "HeartMindRouteDecision",
    "HeartMindSignal",
    "NON_FUSION_ASSERTIONS",
    "ReceptionPosture",
    "RouteTarget",
    "SourceType",
    "signal_from_fixture",
]
