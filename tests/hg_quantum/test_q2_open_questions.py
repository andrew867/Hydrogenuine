from __future__ import annotations

from hg_quantum.cognition.mediator_rate_policy import mediator_rate_status, recommended_entity_ceiling
from hg_quantum.entanglement.shell_model import MIN_KAPPA_INTER, ShellModel
from hg_quantum.error_correction.sum_rule_prior import blend_capacity, record_capacity_estimate
from hg_quantum.transport.fingerprint_codec import CODEC_DESCRIPTIVE_POLICY, FingerprintBandwidthCodec
from hg_realtime.swarm.contracts import QuantumSwarmPlan


def test_shell_fingerprint_tiebreaker_when_role_missing():
    plan = QuantumSwarmPlan(
        summary="t",
        tasks=[
            {
                "entity_id": "e1",
                "workflow_id": "wf",
                "cognitive_fingerprint": {
                    "quantum_cognitive_profile": {"symmetry_breaking_role": "adversarial_pole"},
                },
            }
        ],
        base_fingerprint={"cognitive_fingerprint": {}},
    )
    assignment = ShellModel().assign_shells(plan)
    assert assignment.entity_shell["e1"] == "verifier"


def test_kappa_inter_floor():
    model = ShellModel(kappa_inter=0.01)
    assert model.kappa_inter >= MIN_KAPPA_INTER


def test_sum_rule_rolling_prior_blend(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    record_capacity_estimate(entity_count=3, total_capacity=10.0, workspace_root=tmp_path)
    record_capacity_estimate(entity_count=3, total_capacity=12.0, workspace_root=tmp_path)
    blended = blend_capacity(8.0, entity_count=3, workspace_root=tmp_path)
    assert blended["prior"] == 11.0
    assert 8.0 < blended["blended_capacity"] < 11.0


def test_codec_policy_constant():
    assert FingerprintBandwidthCodec.descriptive_policy == CODEC_DESCRIPTIVE_POLICY


def test_mediator_rate_policy_tightens_after_shadow_floor():
    assert recommended_entity_ceiling(shadow_probe_events=0) == 12
    assert recommended_entity_ceiling(shadow_probe_events=10) == 6
    status = mediator_rate_status()
    assert "recommended_ceiling_per_hour" in status
