"""P26-1 experience ledger adapter tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.artifact_memory_mapper import build_artifact_manifest, map_artifacts_to_memory
from hg_runtime.experience_ledger.gate import validate_p26_1_gate
from hg_runtime.experience_ledger.ledger_adapter import build_p26_1_ledger
from hg_runtime.experience_ledger.ledger_replay import replay_ledger


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P26_1_EXPERIENCE_LEDGER_ADAPTER",
        "explicit_artifact_manifest_only": True,
        "sle_rc_artifact_mapped": True,
        "phase25_artifact_mapped": True,
        "p26_gap_artifact_mapped": True,
        "experience_records_written": True,
        "memory_records_written": True,
        "provenance_pointers_recorded": True,
        "source_quality_pointers_recorded": True,
        "boundary_tags_recorded": True,
        "retraction_capability_recorded": True,
        "quarantine_capability_recorded": True,
        "stable_hash_chain_written": True,
        "replay_verification_passed": True,
        "append_only_ledger": True,
        "memory_is_not_truth": True,
        "experience_is_not_evidence_by_itself": True,
        "no_belief_promotion": True,
        "no_action_authorization": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p26_1_consumes_explicit_artifact_manifest_only():
    manifest = build_artifact_manifest()
    assert manifest["explicit_manifest_only"] is True
    assert manifest["artifact_count"] == 3


def test_p26_1_maps_sle_rc_phase25_and_p26_gap():
    mapped = map_artifacts_to_memory()
    families = {record["family"] for record in mapped["memory_records"]}
    assert {"SLE-RC", "PHASE-25", "P26-GAP"} == families


def test_p26_1_writes_append_only_memory_records():
    mapped = map_artifacts_to_memory()
    assert len(mapped["memory_records"]) == 3
    assert all(record["memory_hash"] for record in mapped["memory_records"])


def test_p26_1_records_provenance_pointers():
    mapped = map_artifacts_to_memory()
    assert all(record["provenance_refs"] for record in mapped["memory_records"])


def test_p26_1_records_source_quality_pointers():
    mapped = map_artifacts_to_memory()
    assert all(record["source_quality_refs"] for record in mapped["memory_records"])


def test_p26_1_records_boundary_tags():
    mapped = map_artifacts_to_memory()
    assert all(record["boundary_tags"] for record in mapped["experience_records"])


def test_p26_1_records_retraction_and_quarantine_capability():
    mapped = map_artifacts_to_memory()
    assert all(record["retraction_supported"] for record in mapped["memory_records"])
    assert all(record["quarantine_supported"] for record in mapped["memory_records"])


def test_p26_1_computes_stable_hash_chain():
    layer = build_p26_1_ledger(Path.cwd())
    assert len(layer["ledger_hash_chain"]) == len(layer["memory_records"])
    assert layer["ledger_manifest"]["ledger_chain_root"]


def test_p26_1_replay_verifies_ledger_hash_chain():
    layer = build_p26_1_ledger(Path.cwd())
    assert layer["replay"]["replay_preserves_ledger_hash_chain"] is True


def test_p26_1_replay_detects_mutated_memory():
    layer = build_p26_1_ledger(Path.cwd())
    memory = [dict(record) for record in layer["memory_records"]]
    memory[0]["artifact_ref"] = "mutated"
    replay = replay_ledger(memory, expected_root=layer["ledger_manifest"]["ledger_chain_root"])
    assert replay["replay_preserves_ledger_hash_chain"] is False


def test_p26_1_does_not_promote_beliefs():
    layer = build_p26_1_ledger(Path.cwd())
    assert all(not record["belief_promoted"] for record in layer["memory_records"])


def test_p26_1_does_not_authorize_actions():
    layer = build_p26_1_ledger(Path.cwd())
    assert layer["ledger_manifest"]["authority_granted"] is False
    assert layer["ledger_manifest"]["tools_authorized"] is False


def test_p26_1_gate_passes_full_summary():
    assert validate_p26_1_gate(_summary())["ok"] is True


def test_p26_1_gate_refuses_memory_truth():
    assert validate_p26_1_gate(_summary(memory_treated_as_truth=True))["ok"] is False


def test_p26_1_gate_refuses_missing_explicit_manifest():
    assert validate_p26_1_gate(_summary(explicit_artifact_manifest_only=False))["ok"] is False


def test_p26_1_gate_refuses_missing_replay():
    assert validate_p26_1_gate(_summary(replay_verification_passed=False))["ok"] is False


def test_p26_1_gate_refuses_belief_promotion():
    assert validate_p26_1_gate(_summary(belief_promoted=True))["ok"] is False


def test_p26_1_gate_refuses_live_effects():
    assert validate_p26_1_gate(_summary(live_external_side_effects_created=True))["ok"] is False

