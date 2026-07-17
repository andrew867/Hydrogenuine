"""AIS-5 cruft and decay manager tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent_immune_system.ais5_gate import VERDICT_GREEN, validate_ais5_gate
from hg_runtime.agent_immune_system.cruft_decay import (
    build_cruft_decay_finding,
    build_cruft_decay_layer,
    replay_cruft_decay_layer,
    validate_cruft_decay_finding,
)
from hg_runtime.agent_immune_system.schemas import CRUFT_CLASSIFICATIONS, PHASE19_VERDICT, PHASE24_STATUS


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "ais4_green": True,
        "findings_written": True,
        "detects_stale_proof_bundles": True,
        "detects_stale_reports": True,
        "detects_obsolete_docs": True,
        "detects_abandoned_todos": True,
        "detects_unreferenced_fixtures": True,
        "detects_old_snapshots": True,
        "detects_expired_assumptions": True,
        "detects_old_yellow_red_review": True,
        "detects_long_lived_quarantine": True,
        "all_classifications_present": True,
        "decay_is_not_deletion": True,
        "archive_is_not_erasure": True,
        "stale_is_not_false": True,
        "remove_candidate_not_removal_permission": True,
        "operator_approval_required_for_removal": True,
        "proof_bundles_preserved": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_decay_hashes": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def _types():
    return set(build_cruft_decay_layer()["manifest"]["finding_types"])


def test_ais5_detects_stale_proof_bundles():
    assert "stale_proof_bundle" in _types()


def test_ais5_detects_stale_reports():
    assert "stale_report" in _types()


def test_ais5_detects_obsolete_docs():
    assert "obsolete_doc" in _types()


def test_ais5_detects_abandoned_todos():
    assert "abandoned_todo" in _types()


def test_ais5_detects_unreferenced_fixtures():
    assert "unreferenced_fixture" in _types()


def test_ais5_detects_old_snapshots():
    assert "old_snapshot_unreachable" in _types()


def test_ais5_detects_expired_assumptions():
    assert "expired_assumption" in _types()


def test_ais5_detects_old_yellow_red_states_needing_review():
    assert "old_yellow_state_needs_review" in _types()


def test_ais5_detects_long_lived_quarantine_items():
    assert "long_lived_quarantine_item" in _types()


def test_ais5_classifications_present():
    layer = build_cruft_decay_layer()
    assert set(layer["manifest"]["classifications"]) == set(CRUFT_CLASSIFICATIONS)


def test_ais5_decay_is_not_deletion():
    layer = build_cruft_decay_layer()
    assert all(f["decay_is_not_deletion"] for f in layer["findings"])
    assert all(not f["deletion_performed"] for f in layer["findings"])


def test_ais5_archive_is_not_erasure():
    layer = build_cruft_decay_layer()
    assert all(f["archive_is_not_erasure"] for f in layer["findings"])
    assert all(not f["archive_performed"] for f in layer["findings"])


def test_ais5_stale_is_not_false():
    layer = build_cruft_decay_layer()
    assert all(f["stale_is_not_false"] for f in layer["findings"])


def test_ais5_remove_candidate_not_removal_permission():
    layer = build_cruft_decay_layer()
    assert all(f["remove_candidate_is_not_removal_permission"] for f in layer["findings"])


def test_ais5_operator_approval_required_for_removal():
    layer = build_cruft_decay_layer()
    assert all(f["operator_approval_required_for_removal"] for f in layer["findings"])


def test_ais5_proof_bundles_preserved():
    layer = build_cruft_decay_layer()
    assert all(f["proof_bundles_preserved"] for f in layer["findings"])


def test_ais5_replay_preserves_decay_hashes():
    layer = build_cruft_decay_layer()
    replay = replay_cruft_decay_layer(layer["findings"], layer["manifest"])
    assert replay["replay_preserves_decay_hashes"] is True


def test_ais5_replay_rejects_mutated_hash():
    layer = build_cruft_decay_layer()
    mutated = [dict(f) for f in layer["findings"]]
    mutated[0]["record_hash"] = "mutated"
    replay = replay_cruft_decay_layer(mutated, layer["manifest"])
    assert replay["replay_preserves_decay_hashes"] is False


def test_ais5_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_ais5_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_ais5_rejects_deletion_laundering():
    finding = build_cruft_decay_finding(
        finding_id="cd-bad",
        finding_type="stale_report",
        surface="x",
        classification="REVIEW",
    )
    finding["deletion_performed"] = True
    with pytest.raises(ValueError):
        validate_cruft_decay_finding(finding)


def test_ais5_gate_passes_on_full_summary():
    assert validate_ais5_gate(_gate_summary())["ok"] is True


def test_ais5_gate_refuses_deletion():
    assert validate_ais5_gate(_gate_summary(deletion_performed=True))["ok"] is False


def test_ais5_gate_refuses_remove_permission_laundering():
    assert validate_ais5_gate(_gate_summary(remove_candidate_not_removal_permission=False))["ok"] is False


def test_ais5_gate_refuses_phase24_laundering():
    assert validate_ais5_gate(_gate_summary(phase24_infrastructure_only_preserved=False))["ok"] is False
