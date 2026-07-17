"""Advanced Wave 2 models operator panel service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hg_quantum.registry import build_default_registry


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class _AdvancedModelsState:
    def __init__(self) -> None:
        self.seeded = False
        self.fingerprint_id = ""
        self.registry = None
        self.recommendations: List[Dict[str, Any]] = []


_STATE = _AdvancedModelsState()


def reset_advanced_models_state() -> None:
    _STATE.seeded = False
    _STATE.fingerprint_id = ""
    _STATE.registry = None
    _STATE.recommendations.clear()


def seed_advanced_models_demo(*, fingerprint_id: str = "fp_wave2_demo") -> Dict[str, Any]:
    from hg_quantum.coordination.kpz_predictor import KpzTransportPredictor
    from hg_quantum.coordination.varifocal_router import VarifocalRouter
    from hg_quantum.cognition.dark_state_detector import DarkStateDetector
    from hg_quantum.non_hermitian.exceptional_point_detector import ExceptionalPointDetector
    from hg_quantum.persistence.optoacoustic_linker import OptoacousticLinker

    reg = build_default_registry(fingerprint_id=fingerprint_id)
    router: VarifocalRouter = reg.get_instance("varifocal_router")
    focal = router.compute_focal_target(
        {"entities": ["ent-alpha", "ent-beta", "ent-gamma"]},
        {"task_id": "demo-task", "focus_pair": ["ent-alpha", "ent-beta"], "priority": "high"},
    )
    for msg in (
        {"type": "shadow_diagnostic", "target_entity": "ent-gamma"},
        {"type": "job_progress", "target_entity": "ent-gamma"},
        {"type": "mesh_alert", "target_entity": "ent-gamma"},
    ):
        router.route_with_focus(msg, focal, target_entity=msg["target_entity"])

    kpz: KpzTransportPredictor = reg.get_instance("kpz_predictor")
    prediction = kpz.predict("writing", correlation_density=0.55)
    kpz.compare_observed(prediction, {"swarm_size": 5, "warmup_seconds": 13.0, "noise_magnitude": 0.37})

    dark: DarkStateDetector = reg.get_instance("dark_state")
    signals = dark.analyze_entity_state(
        "ent-alpha",
        {"output_token_count": 15, "latent": {"reasoning_depth": 0.88}},
    )

    ep: ExceptionalPointDetector = reg.get_instance("exceptional_point")
    points = ep.scan({"context_usage": 0.88, "swarm_size": 10, "drift_score": 0.5, "retry_count": 3})

    linker: OptoacousticLinker = reg.get_instance("optoacoustic")
    linker.link_mesh_to_proof(
        {"event_id": "demo-mesh-1", "type": "entanglement_state_update", "fingerprint_id": fingerprint_id, "ts": 1.0},
        {"snapshot_id": "demo-proof-1", "type": "swarm_proof"},
    )

    _STATE.registry = reg
    _STATE.fingerprint_id = fingerprint_id
    _STATE.seeded = True
    _STATE.recommendations = []
    for p in points:
        _STATE.recommendations.append({
            "type": "exceptional_point",
            "action": p.recommendation,
            "requires_approval": True,
            "point_id": p.point_id,
        })
    for s in signals:
        _STATE.recommendations.append({
            "type": "dark_state",
            "latent_class": s.latent_class,
            "strength": s.strength,
            "policy": s.surfacing_policy,
        })
    _STATE.recommendations.append({
        "type": "kpz",
        "recommended_size": prediction.recommended_size,
        "warmup_seconds": prediction.warmup_seconds,
    })

    return {
        "ok": True,
        "fingerprint_id": fingerprint_id,
        "models_seeded": len(reg.list_models()),
        "routing_savings_pct": router.routing_diagnostics().get("traffic_savings_pct"),
    }


def _ensure_seeded() -> None:
    if not _STATE.seeded:
        seed_advanced_models_demo()


def get_models_dashboard() -> Dict[str, Any]:
    _ensure_seeded()
    reg = _STATE.registry
    assert reg is not None
    models = reg.list_models()
    return {
        "ok": True,
        "fingerprint_id": _STATE.fingerprint_id,
        "models": models,
        "recommendations": list(_STATE.recommendations),
        "generated_at": _iso_now(),
        "evidence_links": {
            "proofs": "#/proofs",
            "entanglement": "#/entanglement",
            "physical_agents": "#/physical-agents",
            "timeline": "#/timeline",
        },
    }


def get_model_detail(model_id: str) -> Dict[str, Any]:
    _ensure_seeded()
    reg = _STATE.registry
    assert reg is not None
    try:
        diag = reg.diagnostics(model_id)
    except KeyError:
        return {"ok": False, "error": "model_not_found"}
    if not diag.get("ok"):
        return diag
    return {"ok": True, **diag}
