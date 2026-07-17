from __future__ import annotations

from hg_quantum.coordination.varifocal_router import VarifocalRouter


def test_varifocal_reduces_mesh_traffic():
    router = VarifocalRouter(fingerprint_id="fp_test")
    focal = router.compute_focal_target(
        {"entities": ["ent-a", "ent-b", "ent-c"]},
        {"focus_pair": ["ent-a", "ent-b"]},
    )
    decisions = []
    for _ in range(10):
        decisions.extend(
            router.route_with_focus(
                {"type": "shadow_diagnostic", "target_entity": "ent-c"},
                focal,
            )
        )
    dropped = sum(1 for d in decisions if d.action == "drop")
    assert dropped >= 5
    diag = router.routing_diagnostics()
    assert diag["traffic_savings_pct"] > 30.0


def test_varifocal_preserves_critical_messages():
    router = VarifocalRouter()
    focal = router.compute_focal_target({"entities": ["a", "b"]}, {})
    for msg_type in ("mesh_alert", "approval_request", "emergency_halt"):
        decisions = router.route_with_focus(
            {"type": msg_type, "target_entity": "off-target"},
            focal,
        )
        assert all(d.action == "deliver" for d in decisions)


def test_varifocal_rotation_responds_to_task_shift():
    router = VarifocalRouter()
    focal1 = router.compute_focal_target(
        {"entities": ["x", "y", "z"]},
        {"focus_pair": ["x", "y"]},
    )
    focal2 = router.compute_focal_target(
        {"entities": ["x", "y", "z"]},
        {"focus_pair": ["y", "z"]},
    )
    assert focal1.focal_targets != focal2.focal_targets
    assert focal2.intensity_by_target.get("z", 0) > focal1.intensity_by_target.get("z", 0)
