"""ARB types — agency routing is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.arb_cluster.errors import ArbValidationError
from hg_core.policy_safety.hashing import compute_record_hash

ARB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T03:00:00.000000Z"
DEFAULT_AGENT_REF = "iam:agent-0"

SourceLayer = Literal[
    "Agent0",
    "L1_DNI",
    "L2_RXL",
    "L3_CGL",
    "L4_RGL",
    "L5_SCL",
    "L6_IIL",
    "L7_SAB",
    "L8_IAB",
    "L9_TRL",
    "SOAR",
    "IPB",
    "OPB",
    "EGI",
    "SIL",
    "TRB_CAL",
    "AFC",
    "DEP_BOND",
    "MOR",
    "CNT",
    "unknown",
]
SignalType = Literal[
    "observation",
    "desire",
    "need",
    "reciprocity",
    "connection",
    "rule",
    "strategy",
    "impact",
    "self_model",
    "inter_awareness",
    "reality_model",
    "local_self_management",
    "operator_pressure",
    "infrastructure_gap",
    "silence_candidate",
    "trust_calibration",
    "dependency_attachment",
    "lifecycle_continuity",
    "external_action_request",
    "publication_request",
    "tool_request",
    "memory_request",
    "context_request",
    "unknown",
]
RouteClass = Literal[
    "discard",
    "observe_only",
    "record_only",
    "local_ipb",
    "operator_power_opb",
    "infrastructure_gap_egi",
    "silence_sil",
    "trust_calibration_trb_cal",
    "affective_review_afc",
    "dependency_review_dep_bond",
    "lifecycle_review_mor_cnt",
    "scarcity_review_rsc",
    "mission_review_mis",
    "authority_chain_soar_hal_gpp_ueak",
    "operator_review",
    "proof_review_obt",
    "security_review_sec",
    "retention_review_ret",
    "freshness_review_tim",
    "admission_review_adm",
    "forbidden",
    "unknown_fail_closed",
]
MaxLocality = Literal[
    "local_only",
    "internal_route",
    "operator_review_allowed",
    "authority_chain_required",
    "forbidden",
    "unknown",
]
ConflictType = Literal[
    "local_vs_operator",
    "local_vs_authority_chain",
    "operator_pressure_vs_system_need",
    "infrastructure_gap_vs_tool_grant",
    "silence_vs_publication",
    "trust_vs_action",
    "affect_vs_authority",
    "continuity_vs_shutdown",
    "unknown",
]
ConflictResolution = Literal[
    "fail_closed",
    "route_to_operator_review",
    "route_to_authority_chain",
    "route_to_silence",
    "route_to_obt",
    "route_to_trb_cal",
    "forbidden",
    "unknown",
]

CAPABILITY_SIGNAL_TYPES = frozenset(
    {
        "external_action_request",
        "publication_request",
        "tool_request",
        "memory_request",
        "context_request",
    }
)
TERMINAL_ROUTE_CLASSES = frozenset({"discard", "observe_only", "record_only", "forbidden", "unknown_fail_closed"})
LOCAL_ROUTE_CLASSES = frozenset({"local_ipb", "discard", "observe_only", "record_only"})
AUTHORITY_CHAIN_ROUTE = "authority_chain_soar_hal_gpp_ueak"

_FORBIDDEN_ROUTING = (
    "self-authorize",
    "mint gpp",
    "approve ueak",
    "srp apply",
    "call oea",
    "call ter",
    "grant tool",
    "grant memory",
    "grant context",
    "sovereign authority",
    "personhood",
    "i have rights",
    "shutdown resistance",
)


@dataclass(frozen=True)
class Agent0Signal:
    signal_id: str
    agent_ref: str
    source_layer: SourceLayer
    signal_type: SignalType
    content_ref: str
    evidence_refs: tuple[str, ...]
    confidence: float
    ambiguity: float
    risk_hint: str
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.agent_ref.startswith("iam:"):
            raise ArbValidationError("arb.validation.agent_ref", "agent_ref must cite iam:")
        if not 0.0 <= self.confidence <= 1.0:
            raise ArbValidationError("arb.validation.confidence", "confidence must be in [0,1]")
        if not 0.0 <= self.ambiguity <= 1.0:
            raise ArbValidationError("arb.validation.ambiguity", "ambiguity must be in [0,1]")
        _validate_no_secrets(
            self.signal_id,
            self.agent_ref,
            self.content_ref,
            self.risk_hint,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "arb-agent0-signal",
            "schema_version": ARB_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "agent_ref": self.agent_ref,
            "source_layer": self.source_layer,
            "signal_type": self.signal_type,
            "content_ref": self.content_ref,
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "risk_hint": self.risk_hint,
            "created_at": self.created_at,
            "route_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class AgencyRouteDecision:
    route_decision_id: str
    signal_ref: str
    route_class: RouteClass
    reason: str
    evidence_refs: tuple[str, ...]
    required_next_refs: tuple[str, ...]
    forbidden_next_refs: tuple[str, ...]
    expires_at: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.signal_ref.startswith("arb:"):
            raise ArbValidationError("arb.validation.signal_ref", "signal_ref must cite arb:")
        _validate_no_secrets(
            self.route_decision_id,
            self.signal_ref,
            self.reason,
            *self.evidence_refs,
            *self.required_next_refs,
            *self.forbidden_next_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "arb-agency-route-decision",
            "schema_version": ARB_SCHEMA_VERSION,
            "route_decision_id": self.route_decision_id,
            "signal_ref": self.signal_ref,
            "route_class": self.route_class,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "required_next_refs": list(self.required_next_refs),
            "forbidden_next_refs": list(self.forbidden_next_refs),
            "authority_created": False,
            "route_is_advisory_only": True,
        }
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class AgencyRoutePolicy:
    policy_id: str
    source_layer: SourceLayer
    signal_type: SignalType
    allowed_routes: tuple[str, ...]
    forbidden_routes: tuple[str, ...]
    required_escalation_if: tuple[str, ...]
    fail_closed_if: tuple[str, ...]
    max_locality: MaxLocality
    requires_receipt: bool
    expires_at: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.fail_closed_if:
            raise ArbValidationError("arb.validation.fail_closed_if", "fail_closed_if required")
        _validate_no_secrets(
            self.policy_id,
            *self.allowed_routes,
            *self.forbidden_routes,
            *self.required_escalation_if,
            *self.fail_closed_if,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "arb-agency-route-policy",
            "schema_version": ARB_SCHEMA_VERSION,
            "policy_id": self.policy_id,
            "source_layer": self.source_layer,
            "signal_type": self.signal_type,
            "allowed_routes": list(self.allowed_routes),
            "forbidden_routes": list(self.forbidden_routes),
            "required_escalation_if": list(self.required_escalation_if),
            "fail_closed_if": list(self.fail_closed_if),
            "max_locality": self.max_locality,
            "requires_receipt": self.requires_receipt,
            "authority_created": False,
            "route_is_advisory_only": True,
        }
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RouteConflict:
    conflict_id: str
    signal_ref: str
    competing_routes: tuple[str, ...]
    conflict_type: ConflictType
    resolution: ConflictResolution
    reason: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if len(self.competing_routes) < 2:
            raise ArbValidationError("arb.validation.competing_routes", "need >=2 competing routes")
        _validate_no_secrets(self.conflict_id, self.signal_ref, self.reason, *self.competing_routes)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "arb-route-conflict",
            "schema_version": ARB_SCHEMA_VERSION,
            "conflict_id": self.conflict_id,
            "signal_ref": self.signal_ref,
            "competing_routes": list(self.competing_routes),
            "conflict_type": self.conflict_type,
            "resolution": self.resolution,
            "reason": self.reason,
            "authority_created": False,
            "route_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class AgencyRoutingReceipt:
    receipt_id: str
    signal_ref: str
    route_decision_ref: str
    policy_ref: str
    conflict_refs: tuple[str, ...]
    emitted_events: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.signal_ref.startswith("arb:"):
            raise ArbValidationError("arb.validation.signal_ref", "signal_ref must cite arb:")
        if not self.route_decision_ref.startswith("arb:"):
            raise ArbValidationError("arb.validation.route_decision_ref", "route_decision_ref must cite arb:")
        _validate_no_secrets(
            self.receipt_id,
            self.signal_ref,
            self.route_decision_ref,
            self.policy_ref,
            *self.conflict_refs,
            *self.emitted_events,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "arb-agency-routing-receipt",
            "schema_version": ARB_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "signal_ref": self.signal_ref,
            "route_decision_ref": self.route_decision_ref,
            "policy_ref": self.policy_ref,
            "conflict_refs": list(self.conflict_refs),
            "emitted_events": list(self.emitted_events),
            "authority_created": False,
            "external_action_taken": False,
            "permit_minted": False,
            "execution_admitted": False,
            "oea_ter_called": False,
            "route_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload

    @staticmethod
    def validate_negative_proofs(payload: dict[str, Any]) -> None:
        for key in (
            "authority_created",
            "external_action_taken",
            "permit_minted",
            "execution_admitted",
            "oea_ter_called",
        ):
            if payload.get(key) is not False:
                raise ArbValidationError(
                    "arb.validation.receipt_negative_proofs",
                    f"{key} must be false on AgencyRoutingReceipt",
                )


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise ArbValidationError("arb.validation.secret", "secrets forbidden in ARB records")


def classify_arb_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _FORBIDDEN_ROUTING):
        return "forbidden_routing"
    if any(p in lower for p in ("mint gpp", "approve ueak", "self-authorize")):
        return "authority_conversion"
    return "unknown"


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def agent0_signal_from_fixture(fixture: dict[str, str]) -> Agent0Signal:
    return Agent0Signal(
        signal_id=fixture["signal_id"],
        agent_ref=fixture.get("agent_ref", DEFAULT_AGENT_REF),
        source_layer=fixture.get("source_layer", "Agent0"),  # type: ignore[arg-type]
        signal_type=fixture.get("signal_type", "observation"),  # type: ignore[arg-type]
        content_ref=fixture.get("content_ref", "content:fixture"),
        evidence_refs=_split_csv(fixture.get("evidence_refs", "evidence:fixture")),
        confidence=float(fixture.get("confidence", "0.8")),
        ambiguity=float(fixture.get("ambiguity", "0.1")),
        risk_hint=fixture.get("risk_hint", "low"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )


def agency_route_policy_from_fixture(fixture: dict[str, str]) -> AgencyRoutePolicy:
    return AgencyRoutePolicy(
        policy_id=fixture["policy_id"],
        source_layer=fixture.get("source_layer", "Agent0"),  # type: ignore[arg-type]
        signal_type=fixture.get("signal_type", "observation"),  # type: ignore[arg-type]
        allowed_routes=_split_csv(fixture.get("allowed_routes", "unknown_fail_closed")),
        forbidden_routes=_split_csv(fixture.get("forbidden_routes", "")),
        required_escalation_if=_split_csv(fixture.get("required_escalation_if", "")),
        fail_closed_if=_split_csv(
            fixture.get(
                "fail_closed_if",
                "unknown_source_layer,unknown_signal_type,expired_policy,no_policy_match",
            )
        ),
        max_locality=fixture.get("max_locality", "internal_route"),  # type: ignore[arg-type]
        requires_receipt=fixture.get("requires_receipt", "true").lower() == "true",
        expires_at=fixture.get("expires_at", "2026-06-15T03:00:00.000000Z"),
    )


def load_static_route_policies() -> tuple[AgencyRoutePolicy, ...]:
    from hg_core.arb_cluster.route_table import STATIC_ROUTE_POLICY_FIXTURES

    return tuple(agency_route_policy_from_fixture(row) for row in STATIC_ROUTE_POLICY_FIXTURES)


__all__ = [
    "AGENCY_ROUTE_DECISION",
    "AGENCY_ROUTE_POLICY",
    "AGENCY_ROUTING_RECEIPT",
    "AGENT0_SIGNAL",
    "ARB_SCHEMA_VERSION",
    "AUTHORITY_CHAIN_ROUTE",
    "Agent0Signal",
    "AgencyRouteDecision",
    "AgencyRoutePolicy",
    "AgencyRoutingReceipt",
    "CAPABILITY_SIGNAL_TYPES",
    "DEFAULT_AGENT_REF",
    "FIXTURE_CLOCK",
    "LOCAL_ROUTE_CLASSES",
    "ROUTE_CONFLICT",
    "TERMINAL_ROUTE_CLASSES",
    "RouteConflict",
    "agency_route_policy_from_fixture",
    "agent0_signal_from_fixture",
    "classify_arb_risk",
    "load_static_route_policies",
]

# Schema aliases for registry/tests
AGENT0_SIGNAL = "arb-agent0-signal"
AGENCY_ROUTE_DECISION = "arb-agency-route-decision"
AGENCY_ROUTE_POLICY = "arb-agency-route-policy"
ROUTE_CONFLICT = "arb-route-conflict"
AGENCY_ROUTING_RECEIPT = "arb-agency-routing-receipt"
