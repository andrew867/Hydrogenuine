"""EWP-3 contradiction review packet tests."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.contradiction_packet_builder import build_contradiction_review_layer
from hg_runtime.evidence_workbench_packets.gate import validate_ewp3_gate
from hg_runtime.evidence_workbench_packets.redaction import secret_scan
from hg_runtime.evidence_workbench_packets.schemas import PHASE19_VERDICT, PHASE24_STATUS


def _records():
    return build_contradiction_review_layer()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_EWP_3_CONTRADICTION_REVIEW_PACKETS",
        "reviewed_beta_green": True,
        "ewp1_green": True,
        "claim_packets_consumed": True,
        "contradiction_packets_written": True,
        "cluster_packets_written": True,
        "contradiction_not_resolution": True,
        "cluster_not_proof": True,
        "contradicted_source_preserved": True,
        "stale_not_false": True,
        "quarantine_not_deletion": True,
        "operator_review_required": True,
        "no_belief_promotion": True,
        "no_tools_actions_live_effects": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_packet_hashes": True,
        "replay_preserves_manifest_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_ewp3_builds_contradiction_packets():
    records = _records()
    assert records["contradiction_review_packets"]
    assert records["contradiction_cluster_packets"]


def test_ewp3_contradiction_is_not_resolution():
    rows = _records()["source_contradiction_records"]
    assert all(not row["contradiction_record_treated_as_resolution"] for row in rows)


def test_ewp3_contradicted_source_preserved():
    rows = _records()["source_contradiction_records"]
    assert all(not row["deletion_performed"] for row in rows)


def test_ewp3_stale_not_false():
    rows = _records()["source_contradiction_records"]
    assert all(not row["stale_source_treated_as_false"] for row in rows)


def test_ewp3_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_ewp3_gate_passes():
    assert validate_ewp3_gate(_summary())["ok"] is True


def test_ewp3_gate_refuses_contradiction_as_resolution():
    assert validate_ewp3_gate(_summary(contradiction_record_treated_as_resolution=True))["ok"] is False
