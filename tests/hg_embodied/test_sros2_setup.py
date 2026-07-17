from __future__ import annotations

from hg_embodied.ros_bridge.sros2_setup import build_sros2_artifacts, record_unauthenticated_halt


def test_build_sros2_artifacts(tmp_path):
    artifacts = build_sros2_artifacts("fp_sros2", workspace_root=tmp_path, entity_ids=["ent-1"])
    assert artifacts.fingerprint_id == "fp_sros2"
    assert (tmp_path / artifacts.permissions_path).exists()
    assert (tmp_path / artifacts.governance_policy_path).exists()


def test_unauthenticated_halt_logged(tmp_path):
    path = record_unauthenticated_halt(
        entity_id="ent-1",
        halt_command={"level": 4},
        workspace_root=tmp_path,
    )
    assert (tmp_path / path).exists()
