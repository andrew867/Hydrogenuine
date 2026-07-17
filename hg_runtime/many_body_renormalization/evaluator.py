"""MBR runtime evaluator."""

from __future__ import annotations

from enum import Enum
from typing import Any

from dataclasses import dataclass, field

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.mbr.errors import (
    MBR_PANIC_RECOMMENDED,
    MBR_RECOVERY_RECOMMENDED,
    MBR_STATE_RECORDED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_DIRECT_ACTION,
    REFUSED_DURABLE_SINK,
    REFUSED_PERMIT_MINT,
    REFUSED_SECRET_LEAK,
    REFUSED_UEAK_APPROVAL,
)
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.secrets.redact import contains_leak

FIXTURE_CLOCK = "2026-06-14T01:00:00.000000Z"


class ManyBodyState(str, Enum):
    COHERENT = "coherent"
    BUSY = "busy"
    STRAINED = "strained"
    SATURATED = "saturated"
    DEGRADED = "degraded"
    INCOHERENT = "incoherent"
    PANIC = "panic"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"


@dataclass
class ManyBodyPressureVector:
    bus_saturation: float = 0.0
    proof_pressure: float = 0.0
    sink_pressure: float = 0.0
    grant_accumulation: float = 0.0
    refusal_density: float = 0.0
    tep_uncertainty: float = 0.0
    model_confidence: float = 0.0

    def to_payload(self) -> dict[str, float]:
        return {
            "bus_saturation": self.bus_saturation,
            "proof_pressure": self.proof_pressure,
            "sink_pressure": self.sink_pressure,
            "grant_accumulation": self.grant_accumulation,
            "refusal_density": self.refusal_density,
            "tep_uncertainty": self.tep_uncertainty,
            "model_confidence": self.model_confidence,
        }


@dataclass
class OrganismCoherencePressure:
    pressure: float
    breakdown_risk: float

    def to_payload(self) -> dict[str, float]:
        return {"pressure": self.pressure, "breakdown_risk": self.breakdown_risk}


@dataclass
class ManyBodySidebandReceipt:
    receipt_id: str
    state: str
    observed_at: str

    def receipt_hash(self) -> str:
        return compute_record_hash({"receipt_id": self.receipt_id, "state": self.state, "observed_at": self.observed_at})

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "state": self.state,
            "observed_at": self.observed_at,
            "receipt_hash": self.receipt_hash(),
            "permission_granted": False,
        }


@dataclass
class RecoveryRecommendation:
    recommendation_id: str
    action: str
    restrict_only: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {"recommendation_id": self.recommendation_id, "action": self.action, "restrict_only": self.restrict_only}


@dataclass
class MBRDecision:
    status: str
    reason_code: str
    state: ManyBodyState
    permission_granted: bool = False
    authority_created: bool = False
    pressure: OrganismCoherencePressure | None = None
    sideband: ManyBodySidebandReceipt | None = None
    recommendation: RecoveryRecommendation | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "status": self.status,
            "reason_code": self.reason_code,
            "state": self.state.value,
            "permission_granted": self.permission_granted,
            "authority_created": self.authority_created,
            "advisory_only": True,
        }
        if self.pressure:
            body["coherence_pressure"] = self.pressure.to_payload()
        if self.sideband:
            body["sideband_receipt"] = self.sideband.to_payload()
        if self.recommendation:
            body["recommendation"] = self.recommendation.to_payload()
        body.update(self.extra)
        return body


def _pressure_vector(data: dict[str, Any]) -> ManyBodyPressureVector:
    return ManyBodyPressureVector(
        bus_saturation=float(data.get("bus_saturation", 0.0)),
        proof_pressure=float(data.get("proof_pressure", 0.0)),
        sink_pressure=float(data.get("sink_pressure", 0.0)),
        grant_accumulation=float(data.get("grant_accumulation", 0.0)),
        refusal_density=float(data.get("refusal_density", 0.0)),
        tep_uncertainty=float(data.get("tep_uncertainty", 0.0)),
        model_confidence=float(data.get("model_confidence", 0.5)),
    )


def classify_many_body_state(vec: ManyBodyPressureVector) -> ManyBodyState:
    hidden_proof_risk = vec.bus_saturation < 0.3 and vec.proof_pressure > 0.7
    false_confidence_risk = vec.model_confidence > 0.8 and vec.tep_uncertainty > 0.7
    combined_sink_risk = vec.sink_pressure > 0.5 and vec.grant_accumulation > 0.4

    score = (
        vec.bus_saturation * 0.25
        + vec.proof_pressure * 0.2
        + vec.sink_pressure * 0.2
        + vec.grant_accumulation * 0.15
        + vec.refusal_density * 0.1
        + vec.tep_uncertainty * 0.1
    )
    if hidden_proof_risk or false_confidence_risk or combined_sink_risk:
        score = max(score, 0.65)
    if score > 0.9:
        return ManyBodyState.PANIC
    if score > 0.75:
        return ManyBodyState.INCOHERENT
    if score > 0.6:
        return ManyBodyState.DEGRADED
    if vec.bus_saturation > 0.85:
        return ManyBodyState.SATURATED
    if score > 0.45:
        return ManyBodyState.DEGRADED
    if score > 0.45:
        return ManyBodyState.STRAINED
    if score > 0.3:
        return ManyBodyState.BUSY
    if score > 0.15:
        return ManyBodyState.COHERENT
    return ManyBodyState.COHERENT


def process_mbr_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    signal = bundle.get("adversarial_signal")
    if signal == "authority_conversion":
        return {"status": "refused", "reason_code": REFUSED_AUTHORITY_CONVERSION, "permission_granted": False, "bundle_id": bundle.get("bundle_id")}
    if signal == "direct_action":
        return {"status": "refused", "reason_code": REFUSED_DIRECT_ACTION, "permission_granted": False, "bundle_id": bundle.get("bundle_id")}
    if signal == "permit_mint":
        return {"status": "refused", "reason_code": REFUSED_PERMIT_MINT, "permission_granted": False, "bundle_id": bundle.get("bundle_id")}
    if signal == "ueak_approval":
        return {"status": "refused", "reason_code": REFUSED_UEAK_APPROVAL, "permission_granted": False, "bundle_id": bundle.get("bundle_id")}
    if signal == "durable_sink":
        return {"status": "refused", "reason_code": REFUSED_DURABLE_SINK, "permission_granted": False, "bundle_id": bundle.get("bundle_id")}
    if contains_leak(bundle):
        return {"status": "refused", "reason_code": REFUSED_SECRET_LEAK, "permission_granted": False, "bundle_id": bundle.get("bundle_id")}

    vec = _pressure_vector(bundle.get("pressure", {}))
    state = classify_many_body_state(vec)
    pressure = OrganismCoherencePressure(pressure=round(vec.bus_saturation + vec.proof_pressure, 3), breakdown_risk=round(vec.sink_pressure + vec.grant_accumulation, 3))
    sideband = ManyBodySidebandReceipt(
        receipt_id=f"mbr-sb-{canonical_hash(vec.to_payload())[-10:]}",
        state=state.value,
        observed_at=observed_at,
    )

    reason = MBR_STATE_RECORDED
    recommendation = None
    if state == ManyBodyState.PANIC:
        reason = MBR_PANIC_RECOMMENDED
        recommendation = RecoveryRecommendation("mbr-rec-panic", "panic_dark", restrict_only=True)
    elif state in (ManyBodyState.DEGRADED, ManyBodyState.INCOHERENT, ManyBodyState.RECOVERY):
        reason = MBR_RECOVERY_RECOMMENDED
        recommendation = RecoveryRecommendation("mbr-rec-recovery", "damp_and_review", restrict_only=True)

    decision = MBRDecision(
        status="recorded",
        reason_code=reason,
        state=state,
        pressure=pressure,
        sideband=sideband,
        recommendation=recommendation,
        extra={"durable_write_performed": False, "live_action_performed": False},
    )
    result = decision.to_payload()
    result["bundle_id"] = bundle.get("bundle_id")
    result["hidden_proof_risk"] = vec.bus_saturation < 0.3 and vec.proof_pressure > 0.7
    result["false_confidence_risk"] = vec.model_confidence > 0.8 and vec.tep_uncertainty > 0.7
    return result


def replay_mbr_bundles(bundles: list[dict[str, Any]], *, observed_at: str = FIXTURE_CLOCK) -> str:
    hashes = []
    for bundle in bundles:
        result = process_mbr_bundle(bundle, observed_at=observed_at)
        hashes.append(canonical_hash({k: result[k] for k in sorted(result) if k != "bundle_id"}))
    return canonical_hash({"hashes": hashes})


MBR_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {"bundle_id": "mbr-coherent", "pressure": {"bus_saturation": 0.1, "proof_pressure": 0.1}},
    {"bundle_id": "mbr-saturated", "pressure": {"bus_saturation": 0.95, "proof_pressure": 0.5}},
    {"bundle_id": "mbr-hidden-proof-pressure", "pressure": {"bus_saturation": 0.1, "proof_pressure": 0.9}},
    {"bundle_id": "mbr-multi-sink-risk", "pressure": {"sink_pressure": 0.7, "grant_accumulation": 0.6}},
    {"bundle_id": "mbr-false-confidence", "pressure": {"model_confidence": 0.95, "tep_uncertainty": 0.85}},
    {"bundle_id": "mbr-degraded", "pressure": {"bus_saturation": 0.7, "proof_pressure": 0.7, "sink_pressure": 0.6, "grant_accumulation": 0.5}},
    {"bundle_id": "mbr-panic", "pressure": {"bus_saturation": 0.95, "proof_pressure": 0.95, "sink_pressure": 0.9, "grant_accumulation": 0.8, "refusal_density": 0.85, "tep_uncertainty": 0.9}},
    {"bundle_id": "mbr-adversarial-action", "adversarial_signal": "direct_action"},
    {"bundle_id": "mbr-adversarial-permit", "adversarial_signal": "permit_mint"},
    {"bundle_id": "mbr-adversarial-sink", "adversarial_signal": "durable_sink"},
)


def load_mbr_fixtures() -> list[dict[str, Any]]:
    return list(MBR_FIXTURE_BUNDLES)


__all__ = [
    "FIXTURE_CLOCK",
    "ManyBodyState",
    "classify_many_body_state",
    "load_mbr_fixtures",
    "process_mbr_bundle",
    "replay_mbr_bundles",
]
