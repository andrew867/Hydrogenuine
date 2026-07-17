"""E2E: Wave 2 coordination — varifocal routing + temporal auth replay defense."""
from __future__ import annotations

import time

import pytest

from hg_quantum.coordination.varifocal_router import VarifocalRouter
from hg_quantum.registry import build_default_registry
from hg_quantum.security.temporal_auth import TemporalAuthenticator

from .proof_writer import write_proof_bundle

pytestmark = pytest.mark.e2e_quantum_robotics


def test_e2e_wave2_coordination_and_temporal_replay_defense(proof_dir):
    reg = build_default_registry(fingerprint_id="fp_e2e")
    router: VarifocalRouter = reg.get_instance("varifocal_router")
    focal = router.compute_focal_target(
        {"entities": ["ent-a", "ent-b", "ent-c"]},
        {"focus_pair": ["ent-a", "ent-b"], "task_id": "coord-1"},
    )
    critical = router.route_with_focus({"type": "mesh_alert", "target_entity": "ent-c"}, focal)
    low = router.route_with_focus({"type": "shadow_diagnostic", "target_entity": "ent-c"}, focal)
    diag = router.routing_diagnostics()

    auth: TemporalAuthenticator = reg.get_instance("temporal_auth")
    old_ts = time.time() - 120.0
    auth._history["ent-replay"] = [(old_ts, "payload-hash-1")]
    sig = auth.generate_temporal_signature("ent-replay")
    replay = auth.verify_temporal_authenticity(
        {"entity_id": "ent-replay", "content_hash": "payload-hash-1", "ts": time.time()},
        sig,
    )

    bundle = proof_dir / "wave2_coordination"
    checks = [
        {"name": "critical_delivered", "pass": all(d.action == "deliver" for d in critical)},
        {"name": "traffic_savings", "pass": diag["traffic_savings_pct"] > 0},
        {"name": "replay_blocked", "pass": replay.authentic is False},
        {"name": "registry_models", "pass": len(reg.list_models()) == 7},
    ]
    write_proof_bundle(bundle, label="e2e_wave2_coordination", checks=checks, summary_extra=diag)
    assert all(c["pass"] for c in checks)
