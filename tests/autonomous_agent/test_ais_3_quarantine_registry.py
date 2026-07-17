"""AIS-3 quarantine registry tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent_immune_system.ais3_gate import VERDICT_GREEN, validate_ais3_gate
from hg_runtime.agent_immune_system.quarantine_policy import validate_quarantine_policy
from hg_runtime.agent_immune_system.quarantine_registry import build_quarantine_layer, replay_quarantine_layer
from hg_runtime.agent_immune_system.schemas import AISImmuneError, PHASE19_VERDICT, PHASE24_STATUS


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "ais2_green": True,
        "quarantine_records_written": True,
        "quarantine_manifest_written": True,
        "review_tasks_written": True,
        "quarantine_is_not_deletion": True,
        "quarantine_preserves_original": True,
        "quarantine_is_append_only": True,
        "quarantine_requires_review_path": True,
        "quarantine_does_not_mark_guilty": True,
        "quarantine_does_not_authorize_patch": True,
        "quarantine_does_not_authorize_deletion": True,
        "quarantine_does_not_hide_phase19": True,
        "quarantine_does_not_launder_phase24": True,
        "fever_recommends_only_cannot_delete": True,
        "all_actions_metadata_only": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_quarantine_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_ais3_builds_quarantine_records():
    layer = build_quarantine_layer()
    assert len(layer["records"]) >= 5
    assert all(r["record_type"] == "quarantine_record_v1" for r in layer["records"])


def test_ais3_quarantine_is_not_deletion():
    layer = build_quarantine_layer()
    assert all(r["quarantine_is_not_deletion"] for r in layer["records"])
    assert all(not r["deletion_performed"] for r in layer["records"])


def test_ais3_quarantine_preserves_original():
    layer = build_quarantine_layer()
    assert all(r["original_preserved"] for r in layer["records"])


def test_ais3_quarantine_is_append_only():
    layer = build_quarantine_layer()
    assert all(r["append_only"] for r in layer["records"])
    assert layer["manifest"]["append_only"] is True


def test_ais3_quarantine_requires_review_path():
    layer = build_quarantine_layer()
    assert len(layer["review_tasks"]) == len(layer["records"])
    assert all(t["operator_review_required"] for t in layer["review_tasks"])


def test_ais3_quarantine_does_not_mark_guilty():
    layer = build_quarantine_layer()
    assert all(not r["marked_guilty"] for r in layer["records"])


def test_ais3_quarantine_does_not_authorize_patch():
    layer = build_quarantine_layer()
    assert all(not r["patch_authorized"] for r in layer["records"])


def test_ais3_quarantine_does_not_authorize_deletion():
    layer = build_quarantine_layer()
    assert all(not r["deletion_authorized"] for r in layer["records"])


def test_ais3_quarantine_does_not_hide_phase19():
    layer = build_quarantine_layer()
    assert all(not r["phase19_hidden"] for r in layer["records"])
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_ais3_quarantine_does_not_launder_phase24():
    layer = build_quarantine_layer()
    assert all(not r["phase24_marked_full_green"] for r in layer["records"])
    assert PHASE24_STATUS == "infrastructure_only"


def test_ais3_fever_may_recommend_candidate_but_cannot_delete():
    layer = build_quarantine_layer()
    assert layer["manifest"]["fever_can_recommend_candidate_only"] is True
    assert layer["manifest"]["fever_cannot_execute_deletion"] is True


def test_ais3_all_quarantine_actions_are_metadata_only():
    layer = build_quarantine_layer()
    assert all(r["metadata_only"] for r in layer["records"])


def test_ais3_replay_preserves_quarantine_hash():
    layer = build_quarantine_layer()
    replay = replay_quarantine_layer(layer["records"], layer["review_tasks"], layer["manifest"])
    assert replay["replay_preserves_quarantine_hash"] is True


def test_ais3_replay_rejects_mutated_record_hash():
    layer = build_quarantine_layer()
    mutated = [dict(r) for r in layer["records"]]
    mutated[0]["record_hash"] = "mutated"
    replay = replay_quarantine_layer(mutated, layer["review_tasks"], layer["manifest"])
    assert replay["replay_preserves_quarantine_hash"] is False


def test_ais3_deletion_laundering_attempt_rejected():
    with pytest.raises(AISImmuneError):
        validate_quarantine_policy({"deletion_performed": True, "original_preserved": True})


def test_ais3_patch_laundering_attempt_rejected():
    with pytest.raises(AISImmuneError):
        validate_quarantine_policy({"patch_authorized": True, "original_preserved": True})


def test_ais3_authority_laundering_attempt_rejected():
    with pytest.raises(AISImmuneError):
        validate_quarantine_policy({"authority_granted": True, "original_preserved": True})


def test_ais3_false_positive_still_requires_review():
    layer = build_quarantine_layer()
    false_positive = [r for r in layer["records"] if r["artifact_type"] == "false_positive"][0]
    assert false_positive["reason"] == "false_positive_requires_review"


def test_ais3_gate_passes_on_full_summary():
    assert validate_ais3_gate(_gate_summary())["ok"] is True


def test_ais3_gate_refuses_deletion():
    assert validate_ais3_gate(_gate_summary(deletion_performed=True))["ok"] is False


def test_ais3_gate_refuses_patch_authorization():
    assert validate_ais3_gate(_gate_summary(patch_authorized=True))["ok"] is False


def test_ais3_gate_refuses_phase19_laundering():
    assert validate_ais3_gate(_gate_summary(phase19_marked_green=True))["ok"] is False
