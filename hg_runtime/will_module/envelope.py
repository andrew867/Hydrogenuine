"""WillEnvelope construction and validation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from hg_runtime.will_module.hash import will_hash
from hg_runtime.will_module.schema import (
    WILL_SCHEMA_VERSION,
    AttentionLock,
    CommitmentHorizon,
    ConsentPosture,
    FIXTURE_CLOCK,
    IntentVector,
    PERSISTENCE_BOUNDS,
    PersistenceBudget,
    PersistenceBudgetClass,
    ValueVector,
    VetoState,
    WillSource,
)


def _enforce_advisory(payload: dict[str, Any]) -> None:
    if payload.get("permission_granted") is True or payload.get("authority_created") is True:
        raise ValueError("WILL must not grant permission or authority")
    if payload.get("advisory_only") is not True:
        raise ValueError("WILL must remain advisory_only")


@dataclass
class WillEnvelope:
    will_id: str
    run_id: str
    source: WillSource
    intent_summary: str
    intent_vector: IntentVector
    value_vector: ValueVector
    attention_target: AttentionLock
    commitment_horizon: CommitmentHorizon
    persistence_budget: PersistenceBudget
    consent_posture: ConsentPosture
    veto_state: VetoState
    allowed_domains: list[str] = field(default_factory=list)
    disallowed_domains: list[str] = field(default_factory=list)
    tool_request_scope: dict[str, Any] = field(default_factory=dict)
    memory_scope: dict[str, Any] = field(default_factory=dict)
    social_scope: dict[str, Any] = field(default_factory=dict)
    risk_tolerance: str = "low"
    uncertainty: float = 0.1
    expires_at: str = FIXTURE_CLOCK
    reaffirmation_required: bool = False
    operator_ref: str | None = None
    agent_ref: str | None = None
    emotional_context: dict[str, Any] | None = None
    meaning_anchor: dict[str, Any] | None = None
    receipt_ref: str = ""
    hash: str = ""

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "schema_version": WILL_SCHEMA_VERSION,
            "schema": "will-envelope",
            "will_id": self.will_id,
            "run_id": self.run_id,
            "operator_ref": self.operator_ref,
            "agent_ref": self.agent_ref,
            "source": self.source.value,
            "intent_summary": self.intent_summary,
            "intent_vector": self.intent_vector.to_payload(),
            "value_vector": self.value_vector.to_payload(),
            "attention_target": self.attention_target.to_payload(),
            "commitment_horizon": self.commitment_horizon.value,
            "persistence_budget": self.persistence_budget.to_payload(),
            "consent_posture": self.consent_posture.value,
            "veto_state": self.veto_state.value,
            "allowed_domains": list(self.allowed_domains),
            "disallowed_domains": list(self.disallowed_domains),
            "tool_request_scope": dict(self.tool_request_scope),
            "memory_scope": dict(self.memory_scope),
            "social_scope": dict(self.social_scope),
            "risk_tolerance": self.risk_tolerance,
            "emotional_context": self.emotional_context,
            "meaning_anchor": self.meaning_anchor,
            "uncertainty": self.uncertainty,
            "expires_at": self.expires_at,
            "reaffirmation_required": self.reaffirmation_required,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }

    def finalize(self, *, receipt_ref: str) -> WillEnvelope:
        self.receipt_ref = receipt_ref
        body = self.semantic_payload()
        self.hash = will_hash(body)
        return self

    def to_payload(self) -> dict[str, Any]:
        payload = self.semantic_payload()
        payload["hash"] = self.hash
        payload["receipt_ref"] = self.receipt_ref
        _enforce_advisory(payload)
        return payload

    def is_expired(self, *, now: str | None = None) -> bool:
        if self.persistence_budget.budget_class == PersistenceBudgetClass.EXPIRED:
            return True
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            ref = datetime.fromisoformat((now or FIXTURE_CLOCK).replace("Z", "+00:00"))
            return ref >= exp
        except ValueError:
            return False


def persistence_from_class(budget_class: str | PersistenceBudgetClass) -> PersistenceBudget:
    key = budget_class.value if isinstance(budget_class, PersistenceBudgetClass) else str(budget_class).upper()
    bounds = PERSISTENCE_BOUNDS.get(key, PERSISTENCE_BOUNDS["MODERATE"])
    return PersistenceBudget(
        budget_class=PersistenceBudgetClass(key) if key in PersistenceBudgetClass.__members__ else PersistenceBudgetClass.MODERATE,
        max_attempts=bounds["max_attempts"],
        max_wallclock_s=bounds["max_wallclock_s"],
        max_tokens=bounds["max_tokens"],
    )


def build_envelope_from_config(
    config: dict[str, Any],
    *,
    run_id: str,
    will_id: str | None = None,
    source: WillSource = WillSource.OPERATOR,
    expires_in_hours: int = 8,
) -> WillEnvelope:
    budget_class = config.get("persistence_budget", "MODERATE")
    expires = config.get("expires_at")
    if not expires:
        expires = (datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)).isoformat()
    env = WillEnvelope(
        will_id=will_id or f"will-{uuid.uuid4().hex[:12]}",
        run_id=run_id,
        source=source,
        intent_summary=str(config.get("intent_summary", "bounded advisory intent")),
        intent_vector=IntentVector(goals=config.get("intent_vector", {}).get("goals", [])),
        value_vector=ValueVector(values=config.get("value_vector", {}).get("values", [])),
        attention_target=AttentionLock(
            target=str(config.get("attention_target", "bounded task")),
            lock_strength=float(config.get("attention_lock_strength", 0.6)),
        ),
        commitment_horizon=CommitmentHorizon(str(config.get("commitment_horizon", "SESSION")).upper()),
        persistence_budget=persistence_from_class(budget_class),
        consent_posture=ConsentPosture(str(config.get("consent_posture", "ASK_FIRST")).upper()),
        veto_state=VetoState(str(config.get("veto_state", "NONE")).upper()),
        allowed_domains=list(config.get("allowed_domains", [])),
        disallowed_domains=list(config.get("disallowed_domains", [])),
        tool_request_scope=dict(config.get("tool_request_scope", {})),
        memory_scope=dict(config.get("memory_scope", {})),
        social_scope=dict(config.get("social_scope", {})),
        risk_tolerance=str(config.get("risk_tolerance", "low")),
        uncertainty=float(config.get("uncertainty", 0.1)),
        expires_at=expires,
        reaffirmation_required=bool(config.get("reaffirmation_required", False)),
        operator_ref=config.get("operator_ref"),
        agent_ref=config.get("agent_ref"),
        meaning_anchor=config.get("meaning_anchor"),
    )
    _enforce_advisory(config)
    return env


def validate_envelope_payload(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key in ("will_id", "run_id", "intent_summary", "expires_at"):
        if not payload.get(key):
            failures.append(f"missing:{key}")
    if payload.get("advisory_only") is not True:
        failures.append("advisory_only_not_true")
    if payload.get("permission_granted") is not False:
        failures.append("permission_granted_not_false")
    if payload.get("authority_created") is not False:
        failures.append("authority_created_not_false")
    budget = payload.get("persistence_budget") or {}
    for bound_key in ("max_attempts", "max_wallclock_s"):
        val = budget.get(bound_key)
        if val is None or int(val) < 0:
            failures.append(f"invalid_persistence:{bound_key}")
    return failures


__all__ = [
    "WillEnvelope",
    "build_envelope_from_config",
    "persistence_from_class",
    "validate_envelope_payload",
]
