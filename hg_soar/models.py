"""SOAR runtime models — sovereign arbitration; no permits or execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from hg_core.governance.canonical_hash import canonical_hash

from hg_soar.types import (
    D7Binding,
    D7Critique,
    D7Decision,
    DOMAIN_IDS,
    DomainEvaluation,
    DomainId,
    SOAR_SCHEMA_VERSION,
)

SOAR_EVENT_SCHEMA = "soar-event"
SOAR_DECISION_SCHEMA = "soar-decision"
SOAR_ROUTE_SCHEMA = "soar-route"

SoarRouteTarget = Literal["none", "HAL", "GPP", "UEAK", "review"]
SoarDecisionState = Literal[
    "advisory_complete",
    "collapsed",
    "route_hal",
    "route_review",
    "sovereign_refusal",
    "fail_closed",
]

_DOMAIN_NAMES: dict[DomainId, str] = {
    "D1": "safety",
    "D2": "perception",
    "D3": "memory",
    "D4": "task",
    "D5": "social",
    "D6": "learning",
    "D7": "sovereign",
}


@dataclass(frozen=True)
class SoarDomain:
    domain_id: DomainId
    name: str
    advisory_only: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "advisory_only": self.advisory_only,
        }


@dataclass(frozen=True)
class DomainWeight:
    domain_id: DomainId
    weight: float

    def to_payload(self) -> dict[str, Any]:
        return {"domain_id": self.domain_id, "weight": self.weight}


@dataclass(frozen=True)
class DomainConstraint:
    domain_id: DomainId
    constraint_type: str
    detail: str = ""

    def to_payload(self) -> dict[str, str]:
        return {
            "domain_id": self.domain_id,
            "constraint_type": self.constraint_type,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class SoarSignal:
    """Advisory domain signal — D1-D6 propose only; not execution authority."""

    signal_id: str
    domain_id: DomainId
    evaluation: DomainEvaluation
    advisory_only: bool
    weight: float = 1.0

    def to_payload(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "domain_id": self.domain_id,
            "advisory_only": self.advisory_only,
            "weight": self.weight,
            "evaluation": self.evaluation.to_payload(),
        }


@dataclass(frozen=True)
class SoarDecisionReason:
    code: str
    detail: str = ""

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class SoarRoute:
    target: SoarRouteTarget
    route_ref: str
    fixture_only: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": SOAR_ROUTE_SCHEMA,
            "schema_version": SOAR_SCHEMA_VERSION,
            "target": self.target,
            "route_ref": self.route_ref,
            "fixture_only": self.fixture_only,
        }


@dataclass(frozen=True)
class SovereignRefusal:
    refusal_id: str
    request_id: str
    binding: D7Binding
    reasons: tuple[SoarDecisionReason, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "refusal_id": self.refusal_id,
            "request_id": self.request_id,
            "binding": self.binding,
            "reasons": [r.to_payload() for r in self.reasons],
        }


@dataclass(frozen=True)
class CritiqueSignal:
    """D7 critique outcome — restrict-only."""

    critique: D7Critique
    binding_before: D7Binding
    binding_after: D7Binding

    def to_payload(self) -> dict[str, Any]:
        return {
            "critique": self.critique.to_payload(),
            "binding_before": self.binding_before,
            "binding_after": self.binding_after,
        }


@dataclass(frozen=True)
class MonotoneCritiqueGuard:
    """Enforces weaken-only critique — cannot expand authority."""

    allowed_verdicts: tuple[str, ...] = ("AFFIRM", "FLAG", "FORCE_DEFER")

    def apply(self, primary: D7Decision, critique: D7Critique) -> D7Binding:
        from hg_soar.critique import apply_critique, binding_rank

        if critique.verdict not in self.allowed_verdicts:
            raise ValueError(f"critique verdict not allowed: {critique.verdict}")
        final = apply_critique(primary, critique)
        if binding_rank(final) > binding_rank(primary.binding):
            raise ValueError("critique attempted authority expansion")
        return final


@dataclass(frozen=True)
class SoarD7Collapse:
    """D7 sovereign collapse — not execution permission by itself."""

    collapse_id: str
    request_id: str
    primary_decision: D7Decision
    binding: D7Binding
    contradictions: tuple[str, ...]
    domain_weights: tuple[DomainWeight, ...]
    collapse_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "collapse_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "soar-d7-collapse",
            "schema_version": SOAR_SCHEMA_VERSION,
            "collapse_id": self.collapse_id,
            "request_id": self.request_id,
            "primary_decision": self.primary_decision.to_payload(),
            "binding": self.binding,
            "contradictions": list(self.contradictions),
            "domain_weights": [w.to_payload() for w in self.domain_weights],
            "execution_permission": False,
        }
        if include_hash:
            payload["collapse_hash"] = self.collapse_hash
        return payload


@dataclass(frozen=True)
class SoarArbitrationContext:
    request_id: str
    proposal_ref: str
    context_refs: tuple[str, ...]
    identity_ref: str
    admission_ref: str
    freshness_ref: str
    contradictions: tuple[str, ...] = ()
    domain_constraints: tuple[DomainConstraint, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "proposal_ref": self.proposal_ref,
            "context_refs": list(self.context_refs),
            "identity_ref": self.identity_ref,
            "admission_ref": self.admission_ref,
            "freshness_ref": self.freshness_ref,
            "contradictions": list(self.contradictions),
            "domain_constraints": [c.to_payload() for c in self.domain_constraints],
        }


@dataclass(frozen=True)
class SoarBundle:
    request_id: str
    signals: tuple[SoarSignal, ...]
    context: SoarArbitrationContext
    bundle_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "bundle_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "soar-bundle",
            "schema_version": SOAR_SCHEMA_VERSION,
            "request_id": self.request_id,
            "signals": [s.to_payload() for s in self.signals],
            "context": self.context.to_payload(),
        }
        if include_hash:
            payload["bundle_hash"] = self.bundle_hash
        return payload

    def advisory_signals(self) -> tuple[SoarSignal, ...]:
        return tuple(s for s in self.signals if s.advisory_only)


@dataclass(frozen=True)
class SoarRequest:
    """SOAR ingress — proposal + authority evidence refs."""

    request_id: str
    proposal_ref: str
    proposal_payload: dict[str, Any]
    identity_ref: str
    admission_ref: str
    freshness_ref: str
    approval_expires_at: Optional[str] = None
    contradictions: tuple[str, ...] = ()
    context_refs: tuple[str, ...] = ()
    idempotency_key: str = ""
    redaction_ref: str = "sec:redaction_passed"
    known_domains: tuple[DomainId, ...] = DOMAIN_IDS

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "soar-request",
            "schema_version": SOAR_SCHEMA_VERSION,
            "request_id": self.request_id,
            "proposal_ref": self.proposal_ref,
            "identity_ref": self.identity_ref,
            "admission_ref": self.admission_ref,
            "freshness_ref": self.freshness_ref,
            "approval_expires_at": self.approval_expires_at,
            "contradictions": list(self.contradictions),
            "context_refs": list(self.context_refs),
            "idempotency_key": self.idempotency_key or self.request_id,
            "known_domains": list(self.known_domains),
        }


@dataclass(frozen=True)
class SoarDecision:
    decision_id: str
    request_id: str
    decision_state: SoarDecisionState
    binding: D7Binding
    collapse: Optional[SoarD7Collapse]
    critique: Optional[CritiqueSignal]
    routes: tuple[SoarRoute, ...]
    reasons: tuple[SoarDecisionReason, ...]
    refusal: Optional[SovereignRefusal] = None
    decision_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": SOAR_DECISION_SCHEMA,
            "schema_version": SOAR_SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "decision_state": self.decision_state,
            "binding": self.binding,
            "reasons": [r.to_payload() for r in self.reasons],
            "routes": [r.to_payload() for r in self.routes],
            "permit_minted": False,
            "execution_approved": False,
        }
        if self.collapse is not None:
            payload["collapse"] = self.collapse.to_payload()
        if self.critique is not None:
            payload["critique"] = self.critique.to_payload()
        if self.refusal is not None:
            payload["refusal"] = self.refusal.to_payload()
        if include_hash:
            payload["decision_hash"] = self.decision_hash
        return payload


@dataclass(frozen=True)
class SoarEvent:
    seq: int
    event_type: str
    timestamp: str
    request_id: str
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": SOAR_EVENT_SCHEMA,
            "schema_version": SOAR_SCHEMA_VERSION,
            "seq": self.seq,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class SoarRuntimeState:
    seq: int
    state_hash: str
    processed_idempotency_keys: frozenset[str]
    last_decision_id: Optional[str]
    event_count: int
    last_binding: Optional[D7Binding]

    def to_payload(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "state_hash": self.state_hash,
            "processed_idempotency_keys": sorted(self.processed_idempotency_keys),
            "last_decision_id": self.last_decision_id,
            "event_count": self.event_count,
            "last_binding": self.last_binding,
        }


def domain_registry() -> tuple[SoarDomain, ...]:
    return tuple(
        SoarDomain(domain_id=did, name=_DOMAIN_NAMES[did], advisory_only=(did != "D7"))
        for did in DOMAIN_IDS
    )


def signal_from_evaluation(evaluation: DomainEvaluation) -> SoarSignal:
    advisory = evaluation.domain_id != "D7"
    return SoarSignal(
        signal_id=f"sig_{evaluation.evaluation_id}",
        domain_id=evaluation.domain_id,
        evaluation=evaluation,
        advisory_only=advisory,
        weight=evaluation.confidence,
    )


def fixture_soar_request(**overrides: Any) -> SoarRequest:
    proposal_ref = overrides.get("proposal_ref", "prop_soar_fixture")
    return SoarRequest(
        request_id=overrides.get("request_id", f"soar_req_{proposal_ref}"),
        proposal_ref=proposal_ref,
        proposal_payload=overrides.get(
            "proposal_payload",
            {
                "proposal_id": proposal_ref,
                "kind": "candidate_action",
                "content": {
                    "proposal_id": proposal_ref,
                    "kind": "candidate_action",
                    "capability_id": "cap.oea_stub_log",
                    "effect_class": "audit_log",
                    "action_type": "oea_stub_log",
                },
            },
        ),
        identity_ref=overrides.get("identity_ref", "op:local"),
        admission_ref=overrides.get("admission_ref", "adm:fixture_1"),
        freshness_ref=overrides.get("freshness_ref", "tim:fresh_fixture"),
        approval_expires_at=overrides.get("approval_expires_at"),
        contradictions=overrides.get("contradictions", ()),
        context_refs=overrides.get("context_refs", ("ctx:fixture",)),
        idempotency_key=overrides.get("idempotency_key", ""),
        redaction_ref=overrides.get("redaction_ref", "sec:redaction_passed"),
        known_domains=overrides.get("known_domains", DOMAIN_IDS),
    )


__all__ = [
    "CritiqueSignal",
    "DomainConstraint",
    "DomainWeight",
    "MonotoneCritiqueGuard",
    "SOAR_DECISION_SCHEMA",
    "SOAR_EVENT_SCHEMA",
    "SoarArbitrationContext",
    "SoarBundle",
    "SoarD7Collapse",
    "SoarDecision",
    "SoarDecisionReason",
    "SoarDecisionState",
    "SoarDomain",
    "SoarEvent",
    "SoarRequest",
    "SoarRoute",
    "SoarRouteTarget",
    "SoarRuntimeState",
    "SoarSignal",
    "SovereignRefusal",
    "domain_registry",
    "fixture_soar_request",
    "signal_from_evaluation",
]
