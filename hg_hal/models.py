"""HAL runtime models — event-sourced arbitration; no permits or execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from hg_core.governance.canonical_hash import canonical_hash

from hg_hal.types import ArbitrationRequest, ArbitrationResult

HAL_EVENT_SCHEMA = "hal-event"
HAL_EVENT_SCHEMA_VERSION = "1.0"
HAL_DECISION_SCHEMA = "hal-decision"
HAL_DECISION_SCHEMA_VERSION = "1.0"

HalDecisionState = Literal[
    "propose",
    "defer",
    "request_clarification",
    "route_to_operator",
    "route_to_GPP",
    "route_to_UEAK",
    "route_to_SOAR",
    "reject",
    "fail_closed",
    "unknown",
]

HalRouteTarget = Literal["none", "GPP", "UEAK", "SOAR", "operator"]


@dataclass(frozen=True)
class HalDecisionReason:
    code: str
    detail: str = ""

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class HalRoute:
    target: HalRouteTarget
    route_ref: str
    decision_state: HalDecisionState

    def to_payload(self) -> dict[str, str]:
        return {
            "target": self.target,
            "route_ref": self.route_ref,
            "decision_state": self.decision_state,
        }


@dataclass(frozen=True)
class HalArbitrationContext:
    request_id: str
    proposal_ref: str
    context_refs: tuple[str, ...]
    identity_ref: str
    admission_ref: str
    freshness_ref: str
    contradictions: tuple[str, ...]
    aep_max_severity: int = 0
    soar_binding: Optional[str] = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "proposal_ref": self.proposal_ref,
            "context_refs": list(self.context_refs),
            "identity_ref": self.identity_ref,
            "admission_ref": self.admission_ref,
            "freshness_ref": self.freshness_ref,
            "contradictions": list(self.contradictions),
            "aep_max_severity": self.aep_max_severity,
            "soar_binding": self.soar_binding,
        }


@dataclass(frozen=True)
class HalRequest:
    """HAL ingress — arbitration request plus authority evidence refs."""

    arbitration: ArbitrationRequest
    identity_ref: str
    admission_ref: str
    freshness_ref: str
    approval_expires_at: Optional[str] = None
    idempotency_key: str = ""
    redaction_ref: str = "sec:redaction_passed"
    redaction_payload: Optional[dict[str, Any]] = None
    contradictions: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "hal-request",
            "schema_version": "1.0",
            "arbitration": self.arbitration.to_payload(),
            "identity_ref": self.identity_ref,
            "admission_ref": self.admission_ref,
            "freshness_ref": self.freshness_ref,
            "approval_expires_at": self.approval_expires_at,
            "idempotency_key": self.idempotency_key or self.arbitration.request_id,
            "redaction_ref": self.redaction_ref,
            "contradictions": list(self.contradictions),
        }


@dataclass(frozen=True)
class HalDecision:
    decision_id: str
    request_id: str
    decision_state: HalDecisionState
    route: HalRoute
    reasons: tuple[HalDecisionReason, ...]
    arbitration_result: Optional[ArbitrationResult]
    selected_candidate_ref: Optional[str]
    deferred_candidate_refs: tuple[str, ...]
    contradictions: tuple[str, ...]
    decision_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": HAL_DECISION_SCHEMA,
            "schema_version": HAL_DECISION_SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "decision_state": self.decision_state,
            "route": self.route.to_payload(),
            "reasons": [r.to_payload() for r in self.reasons],
            "selected_candidate_ref": self.selected_candidate_ref,
            "deferred_candidate_refs": list(self.deferred_candidate_refs),
            "contradictions": list(self.contradictions),
        }
        if self.arbitration_result is not None:
            payload["arbitration"] = self.arbitration_result.to_payload(include_hash=False)
        if include_hash:
            payload["decision_hash"] = self.decision_hash
        return payload


@dataclass(frozen=True)
class HalEvent:
    seq: int
    event_type: str
    timestamp: str
    request_id: str
    payload: dict[str, Any]
    event_hash: str = field(init=False)

    def __post_init__(self) -> None:
        body = {
            "schema": HAL_EVENT_SCHEMA,
            "schema_version": HAL_EVENT_SCHEMA_VERSION,
            "seq": self.seq,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "payload": self.payload,
        }
        object.__setattr__(self, "event_hash", canonical_hash(body))

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": HAL_EVENT_SCHEMA,
            "schema_version": HAL_EVENT_SCHEMA_VERSION,
            "seq": self.seq,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "payload": self.payload,
            "event_hash": self.event_hash,
        }


@dataclass(frozen=True)
class HalPanicState:
    active: bool = False
    entered_at: Optional[str] = None
    reason_code: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "entered_at": self.entered_at,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class HalDegradedMode:
    active: bool = False
    mode: str = "none"
    entered_at: Optional[str] = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "mode": self.mode,
            "entered_at": self.entered_at,
        }


@dataclass(frozen=True)
class HalRuntimeState:
    seq: int
    state_hash: str
    panic: HalPanicState
    degraded: HalDegradedMode
    processed_idempotency_keys: frozenset[str]
    last_decision_id: Optional[str]
    event_count: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "state_hash": self.state_hash,
            "panic": self.panic.to_payload(),
            "degraded": self.degraded.to_payload(),
            "processed_idempotency_keys": sorted(self.processed_idempotency_keys),
            "last_decision_id": self.last_decision_id,
            "event_count": self.event_count,
        }


def fixture_hal_request(**overrides: Any) -> HalRequest:
    from hg_hal.types import ArbitrationCandidate

    arbitration = ArbitrationRequest(
        request_id=overrides.get("request_id", "hal_req_fixture"),
        proposal_ref=overrides.get("proposal_ref", "prop_fixture"),
        candidates=overrides.get(
            "candidates",
            (
                ArbitrationCandidate(
                    candidate_id="cand_fixture",
                    action_ref="act_fixture",
                    capability_id="cap.oea_stub_log",
                    effect_class="audit_log",
                ),
            ),
        ),
        context_refs=overrides.get("context_refs", ("ctx_fixture",)),
    )
    return HalRequest(
        arbitration=arbitration,
        identity_ref=overrides.get("identity_ref", "op:local"),
        admission_ref=overrides.get("admission_ref", "adm:token_fixture_valid"),
        freshness_ref=overrides.get("freshness_ref", "tim:approval_window_ok"),
        approval_expires_at=overrides.get("approval_expires_at", "2099-12-31T23:59:59.000000Z"),
        idempotency_key=overrides.get("idempotency_key", arbitration.request_id),
        redaction_ref=overrides.get("redaction_ref", "sec:redaction_passed"),
        redaction_payload=overrides.get("redaction_payload"),
        contradictions=overrides.get("contradictions", ()),
    )


__all__ = [
    "HAL_DECISION_SCHEMA",
    "HAL_EVENT_SCHEMA",
    "HalArbitrationContext",
    "HalDecision",
    "HalDecisionReason",
    "HalDecisionState",
    "HalDegradedMode",
    "HalEvent",
    "HalPanicState",
    "HalRequest",
    "HalRoute",
    "HalRouteTarget",
    "HalRuntimeState",
    "fixture_hal_request",
]
