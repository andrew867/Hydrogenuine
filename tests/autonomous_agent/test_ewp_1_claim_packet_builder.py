"""EWP-1 claim packet builder tests."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.claim_packet_builder import build_claim_evidence_packets, build_ewp1_inputs
from hg_runtime.evidence_workbench_packets.gate import validate_ewp1_gate
from hg_runtime.evidence_workbench_packets.packet_replay import replay_claim_packet_build
from hg_runtime.evidence_workbench_packets.redaction import secret_scan
from hg_runtime.evidence_workbench_packets.schemas import PHASE19_VERDICT, PHASE24_STATUS, record_hash


def _records():
    return build_claim_evidence_packets(build_ewp1_inputs())


def _summary(**overrides):
    data = {
        "verdict": "GREEN_EWP_1_CLAIM_PACKET_BUILDER",
        "reviewed_beta_green": True,
        "sqp_consolidation_green": True,
        "ewp0_green": True,
        "leb_claim_links_consumed": True,
        "orp_reviewed_links_consumed": True,
        "orp_belief_revisions_consumed": True,
        "sqp_fingerprints_consumed": True,
        "sqp_duplicates_consumed": True,
        "sqp_quality_consumed": True,
        "sqp_provenance_consumed": True,
        "sqp_staleness_conflicts_consumed": True,
        "sqp_review_hints_consumed": True,
        "claim_packets_written": True,
        "source_summaries_written": True,
        "support_records_written": True,
        "contradiction_records_written": True,
        "packet_not_truth": True,
        "support_not_proof": True,
        "quality_not_authority": True,
        "provenance_not_proof": True,
        "contradictions_visible": True,
        "duplicates_collapsed_originals_preserved": True,
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


def test_ewp1_builds_claim_packets():
    records = _records()
    assert len(records["claim_evidence_packets"]) == 3
    assert all(row["record_type"] == "claim_evidence_packet_v1" for row in records["claim_evidence_packets"])


def test_ewp1_packet_is_not_truth():
    assert all(not row["packet_treated_as_truth"] for row in _records()["claim_evidence_packets"])


def test_ewp1_support_is_not_proof():
    assert all(not row["support_record_treated_as_proof"] for row in _records()["packet_support_records"])


def test_ewp1_contradictions_visible():
    assert _records()["packet_contradiction_records"]


def test_ewp1_duplicates_collapsed_originals_preserved():
    summaries = _records()["packet_source_summaries"]
    assert any(row["duplicate_collapsed"] and len(row["original_source_ids"]) > 1 for row in summaries)


def test_ewp1_replay_deterministic():
    records = _records()
    manifest_hash = record_hash(
        {
            "claim_packets": records["claim_evidence_packets"],
            "summaries": records["packet_source_summaries"],
            "supports": records["packet_support_records"],
            "contradictions": records["packet_contradiction_records"],
        }
    )
    replay = replay_claim_packet_build(
        expected_manifest_hash=manifest_hash,
        expected_packet_hashes=[row["packet_hash"] for row in records["claim_evidence_packets"]],
    )
    assert replay["replay_preserves_manifest_hash"] is True
    assert replay["replay_preserves_packet_hashes"] is True


def test_ewp1_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_ewp1_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_ewp1_gate_passes():
    assert validate_ewp1_gate(_summary())["ok"] is True


def test_ewp1_gate_refuses_packet_as_truth():
    assert validate_ewp1_gate(_summary(packet_treated_as_truth=True))["ok"] is False
