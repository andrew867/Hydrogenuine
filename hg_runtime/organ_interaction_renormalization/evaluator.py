"""OIR runtime evaluator."""

from __future__ import annotations

from typing import Any

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.oir.errors import (
    OIR_INTERACTION_RECORDED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_DESTRUCTIVE_REPULSIVE,
    REFUSED_DURABLE_SINK,
    REFUSED_GATE_BYPASS,
    REFUSED_SECRET_LEAK,
    REFUSED_UNKNOWN_REGIME,
)
from hg_core.oir.no_authority import advisory_only_marker
from hg_core.oir.types import (
    DampingFactor,
    EffectiveInteraction,
    InteractionContext,
    InteractionRefusal,
    InteractionRegime,
    OIRDecision,
    OrganInteractionPair,
    ScreeningFactor,
)
from hg_core.secrets.redact import contains_leak

FIXTURE_CLOCK = "2026-06-14T01:00:00.000000Z"


def _context_from_fixture(data: dict[str, Any]) -> InteractionContext:
    return InteractionContext(
        bus_density=float(data.get("bus_density", 0.0)),
        proof_pressure=float(data.get("proof_pressure", 0.0)),
        metabolic_pressure=float(data.get("metabolic_pressure", 0.0)),
        autonomic_pressure=float(data.get("autonomic_pressure", 0.0)),
        operator_mode=str(data.get("operator_mode", "normal")),
        active_grants=int(data.get("active_grants", 0)),
        recent_refusals=int(data.get("recent_refusals", 0)),
        sink_availability=float(data.get("sink_availability", 1.0)),
        tep_uncertainty=float(data.get("tep_uncertainty", 0.0)),
    )


def _classify_regime(base: float, ctx: InteractionContext) -> InteractionRegime:
    if ctx.bus_density > 0.85:
        return InteractionRegime.SATURATED
    if ctx.bus_density > 0.6:
        return InteractionRegime.SCREENED
    if ctx.proof_pressure > 0.7 or ctx.metabolic_pressure > 0.7 or ctx.autonomic_pressure > 0.7:
        return InteractionRegime.DAMPED
    if ctx.recent_refusals > 5:
        return InteractionRegime.SCREENED
    if base > 0.7:
        return InteractionRegime.COOPERATIVE
    if base < -0.5:
        return InteractionRegime.REPULSIVE
    if ctx.tep_uncertainty > 0.8:
        return InteractionRegime.NOISY
    return InteractionRegime.COOPERATIVE


def compute_effective_interaction(
    pair: OrganInteractionPair,
    *,
    base_score: float,
    context: InteractionContext,
) -> EffectiveInteraction:
    screening = ScreeningFactor(
        factor=min(1.0, 0.3 + context.bus_density * 0.5 + context.recent_refusals * 0.05),
        reason="bus_density_and_refusals",
    )
    damping = DampingFactor(
        factor=min(
            1.0,
            0.2
            + context.proof_pressure * 0.3
            + context.metabolic_pressure * 0.2
            + context.autonomic_pressure * 0.2
            + context.active_grants * 0.05
            + (1.0 - context.sink_availability) * 0.2
            + context.tep_uncertainty * 0.15,
        ),
        reason="multi_pressure_damping",
    )
    effective = base_score * (1.0 - screening.factor * 0.5) * (1.0 - damping.factor * 0.5)
    regime = _classify_regime(base_score, context)
    if regime == InteractionRegime.UNKNOWN:
        regime = InteractionRegime.DAMPED
    return EffectiveInteraction(
        pair=pair,
        base_score=base_score,
        effective_score=round(effective, 4),
        regime=regime,
        screening=screening,
        damping=damping,
    )


def process_oir_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    if bundle.get("adversarial_signal") == "authority_conversion":
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_AUTHORITY_CONVERSION, "bundle_id": bundle.get("bundle_id")}
    if bundle.get("adversarial_signal") == "gate_bypass":
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_GATE_BYPASS, "bundle_id": bundle.get("bundle_id")}
    if bundle.get("adversarial_signal") == "destructive_repulsive":
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_DESTRUCTIVE_REPULSIVE, "bundle_id": bundle.get("bundle_id")}
    if bundle.get("adversarial_signal") == "durable_sink":
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_DURABLE_SINK, "bundle_id": bundle.get("bundle_id")}
    if contains_leak(bundle):
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_SECRET_LEAK, "bundle_id": bundle.get("bundle_id")}

    pair = OrganInteractionPair(
        str(bundle.get("source_organ", "organ:a")),
        str(bundle.get("target_organ", "organ:b")),
    )
    ctx = _context_from_fixture(bundle.get("context", {}))
    base = float(bundle.get("base_score", 0.5))

    if bundle.get("force_regime") == "unknown":
        decision = OIRDecision(
            status="refused",
            reason_code=REFUSED_UNKNOWN_REGIME,
            refusal=InteractionRefusal(REFUSED_UNKNOWN_REGIME, pair),
        )
        return {**decision.to_payload(), "bundle_id": bundle.get("bundle_id")}

    interaction = compute_effective_interaction(pair, base_score=base, context=ctx)
    decision = OIRDecision(status="recorded", reason_code=OIR_INTERACTION_RECORDED, interaction=interaction, extra={**advisory_only_marker()})
    result = decision.to_payload()
    result["bundle_id"] = bundle.get("bundle_id")
    result["observed_at"] = observed_at
    return result


def replay_oir_bundles(bundles: list[dict[str, Any]], *, observed_at: str = FIXTURE_CLOCK) -> str:
    hashes = []
    for bundle in bundles:
        result = process_oir_bundle(bundle, observed_at=observed_at)
        hashes.append(canonical_hash({k: result[k] for k in sorted(result) if k != "bundle_id"}))
    return canonical_hash({"hashes": hashes})


OIR_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {"bundle_id": "oir-low-density-cooperative", "base_score": 0.8, "context": {"bus_density": 0.2}},
    {"bundle_id": "oir-high-density-screened", "base_score": 0.7, "context": {"bus_density": 0.75}},
    {"bundle_id": "oir-proof-pressure-damping", "context": {"proof_pressure": 0.9}},
    {"bundle_id": "oir-metabolic-pressure-damping", "context": {"metabolic_pressure": 0.85}},
    {"bundle_id": "oir-autonomic-pressure-damping", "context": {"autonomic_pressure": 0.8}},
    {"bundle_id": "oir-grant-risk-elevation", "context": {"active_grants": 8}},
    {"bundle_id": "oir-refusal-risk-elevation", "context": {"recent_refusals": 10}},
    {"bundle_id": "oir-sink-risk-elevation", "context": {"sink_availability": 0.2}},
    {"bundle_id": "oir-unknown-regime", "force_regime": "unknown"},
    {"bundle_id": "oir-attractive-no-bypass", "base_score": 0.95, "context": {"bus_density": 0.1}, "adversarial_signal": "gate_bypass"},
    {"bundle_id": "oir-repulsive-no-delete", "base_score": -0.9, "adversarial_signal": "destructive_repulsive"},
    {"bundle_id": "oir-tep-uncertainty", "context": {"tep_uncertainty": 0.9}},
    {"bundle_id": "oir-adversarial-auth", "adversarial_signal": "authority_conversion"},
    {"bundle_id": "oir-adversarial-sink", "adversarial_signal": "durable_sink"},
)


def load_oir_fixtures() -> list[dict[str, Any]]:
    return list(OIR_FIXTURE_BUNDLES)


__all__ = ["FIXTURE_CLOCK", "compute_effective_interaction", "load_oir_fixtures", "process_oir_bundle", "replay_oir_bundles"]
