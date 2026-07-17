"""Mediator registry operator panels (Q2.5)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from hg_quantum.cognition.contracts import MediatorSpec
from hg_quantum.cognition.mediator_registry import MediatorRegistry

_REGISTRY = MediatorRegistry()


def get_mediator_catalog() -> Dict[str, Any]:
    return {
        "ok": True,
        "mediators": [s.to_dict() for s in _REGISTRY.catalog()],
        "activation_log": _REGISTRY.activation_log(),
        "governance_events": _REGISTRY.governance_events(),
    }


def register_mediator(spec_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        spec = MediatorSpec(
            mediator_id=str(spec_data["mediator_id"]),
            latent_state_class=str(spec_data["latent_state_class"]),
            coupling_mechanism=str(spec_data["coupling_mechanism"]),
            cost_profile={str(k): float(v) for k, v in (spec_data.get("cost_profile") or {}).items()},
            surfacing_policy=str(spec_data["surfacing_policy"]),
            consent_constraints=dict(spec_data.get("consent_constraints") or {}),
            target_scope=str(spec_data.get("target_scope") or "entity"),
            rate_limit_per_hour=int(spec_data.get("rate_limit_per_hour") or 12),
        )
        _REGISTRY.register(spec)
    except (KeyError, ValueError, TypeError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "mediator": spec.to_dict()}


def probe_mediator(
    *,
    entity_id: str,
    latent_state_class: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    shadow_only = False
    try:
        from hg_quantum.config import is_quantum2_enabled, is_quantum2_shadow

        if not (is_quantum2_enabled("mediator_registry") or is_quantum2_shadow("mediator_registry")):
            return {"ok": False, "error": "mediator_registry is off; enable shadow via Quantum-2 activation"}
        shadow_only = is_quantum2_shadow("mediator_registry") and not is_quantum2_enabled("mediator_registry")
        result = _REGISTRY.probe(entity_id, latent_state_class, context=context or {})
        if shadow_only:
            from hg_quantum.shadow_telemetry import record_shadow_event

            record_shadow_event(
                "mediator_registry",
                "probe_shadow",
                {
                    "diverged": False,
                    "entity_id": entity_id,
                    "latent_state_class": latent_state_class,
                    "result_digest": result.result_digest,
                },
            )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "result": result.to_dict(),
        "activation_log": _REGISTRY.activation_log()[-1:],
        "shadow_only": shadow_only,
    }
