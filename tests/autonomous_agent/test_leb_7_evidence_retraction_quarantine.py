"""LEB-7 local evidence retraction and quarantine loop tests."""

from __future__ import annotations

import pytest

from hg_runtime.local_evidence_bridge.evidence_decay import build_evidence_decay_record
from hg_runtime.local_evidence_bridge.evidence_quarantine_loop import (
    build_loop_fixture_receipts,
    build_retraction_quarantine_loop,
    replay_retraction_quarantine,
    validate_leb7_gate,
)
from hg_runtime.local_evidence_bridge.evidence_retention_policy import build_retention_policy
from hg_runtime.local_evidence_bridge.evidence_retraction import build_evidence_retraction_record
from hg_runtime.local_evidence_bridge.redaction import secret_scan
from hg_runtime.local_evidence_bridge.schemas import EvidenceBridgeError, PHASE19_VERDICT, PHASE24_STATUS


def _loop():
    return build_retraction_quarantine_loop(build_loop_fixture_receipts())


def _gate_summary(**overrides):
    data = {
        "verdict": "GREEN_LEB_7_EVIDENCE_RETRACTION_QUARANTINE_LOOP",
        "retention_policy_written": True,
        "retraction_records_written": True,
        "quarantine_records_written": True,
        "decay_records_written": True,
        "manifest_written": True,
        "evidence_retraction_not_erasure": True,
        "evidence_quarantine_not_deletion": True,
        "evidence_decay_not_deletion": True,
        "original_receipt_preserved": True,
        "derived_belief_revisions_auditable": True,
        "retraction_creates_review_requirement": True,
        "append_only": True,
        "no_deletion": True,
        "no_erasure": True,
        "no_automatic_patching": True,
        "no_auto_quarantine_enforcement": True,
        "replay_preserves_loop_hashes": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Loop construction -----------------------------------------------------

def test_leb7_loop_retracts_flagged_not_clean():
    m = _loop()["manifest"]
    assert m["input_receipt_count"] == 6
    assert m["retraction_count"] == 5  # CLEAN excluded


def test_leb7_quarantine_and_decay_split():
    m = _loop()["manifest"]
    assert m["quarantine_count"] == 4  # BAD/SUSPECT/CONTRADICTED/REDACTION_FAILED
    assert m["decay_count"] == 1  # STALE


def test_leb7_retraction_is_not_erasure():
    for r in _loop()["retractions"]:
        assert r["evidence_retraction_is_erasure"] is False
        assert r["original_receipt_preserved"] is True
        assert r["deletion_performed"] is False


def test_leb7_quarantine_is_not_deletion():
    for q in _loop()["quarantines"]:
        assert q["evidence_quarantine_is_deletion"] is False
        assert q["original_receipt_preserved"] is True
        assert q["auto_quarantine_enforced"] is False


def test_leb7_decay_is_not_deletion():
    for d in _loop()["decays"]:
        assert d["evidence_decay_is_deletion"] is False
        assert d["evidence_decay_is_erasure"] is False
        assert d["original_receipt_preserved"] is True


def test_leb7_original_preserved_everywhere():
    layer = _loop()
    everything = layer["retractions"] + layer["quarantines"] + layer["decays"]
    assert all(rec["original_receipt_preserved"] for rec in everything)


def test_leb7_retraction_creates_review_requirement():
    for r in _loop()["retractions"]:
        assert r["review_required"] is True
        assert r["review_task_id"]


def test_leb7_derived_belief_revisions_remain_auditable():
    for r in _loop()["retractions"]:
        assert r["derived_belief_revisions_auditable"] is True


def test_leb7_no_deletion_or_erasure():
    m = _loop()["manifest"]
    assert m["deletion_performed"] is False
    assert m["erasure_performed"] is False


def test_leb7_append_only():
    assert _loop()["manifest"]["append_only"] is True


# --- Unit builders ---------------------------------------------------------

def test_leb7_retention_policy_no_deletion():
    p = build_retention_policy()
    assert p["deletion_enabled"] is False
    assert p["erasure_enabled"] is False
    assert p["append_only"] is True


def test_leb7_invalid_retraction_reason_rejected():
    with pytest.raises(EvidenceBridgeError):
        build_evidence_retraction_record(
            retraction_id="x", receipt={"receipt_id": "r"}, reason="DELETE_FOREVER"
        )


def test_leb7_decay_record_preserves_original():
    d = build_evidence_decay_record(decay_id="d1", receipt={"receipt_id": "r", "receipt_hash": "h"}, retraction_id="ret1")
    assert d["original_receipt_preserved"] is True
    assert d["evidence_decay_is_deletion"] is False


# --- Replay & secrets ------------------------------------------------------

def test_leb7_replay_preserves_loop_hashes():
    assert _loop()["replay"]["replay_preserves_loop_hashes"] is True


def test_leb7_replay_rejects_mutated_retraction():
    layer = _loop()
    retr = [dict(r) for r in layer["retractions"]]
    retr[0]["reason"] = "STALE"
    replay = replay_retraction_quarantine(retr, layer["quarantines"], layer["decays"], layer["manifest"])
    assert replay["replay_preserves_loop_hashes"] is False


def test_leb7_no_secret_material_in_records():
    assert secret_scan(_loop()) is True


# --- Prior phases ----------------------------------------------------------

def test_leb7_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_leb7_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


# --- Gate ------------------------------------------------------------------

def test_leb7_gate_passes_on_full_summary():
    assert validate_leb7_gate(_gate_summary())["ok"] is True


def test_leb7_gate_refuses_if_deletion():
    assert validate_leb7_gate(_gate_summary(deletion_performed=True))["ok"] is False


def test_leb7_gate_refuses_if_erasure():
    assert validate_leb7_gate(_gate_summary(erasure_performed=True))["ok"] is False


def test_leb7_gate_refuses_if_retraction_is_erasure():
    assert validate_leb7_gate(_gate_summary(evidence_retraction_not_erasure=False))["ok"] is False


def test_leb7_gate_refuses_if_quarantine_is_deletion():
    assert validate_leb7_gate(_gate_summary(evidence_quarantine_not_deletion=False))["ok"] is False


def test_leb7_gate_refuses_if_auto_quarantine_enforced():
    assert validate_leb7_gate(_gate_summary(auto_quarantine_enforced=True))["ok"] is False


def test_leb7_gate_refuses_if_automatic_patching():
    assert validate_leb7_gate(_gate_summary(automatic_patching_enabled=True))["ok"] is False


def test_leb7_gate_refuses_if_no_review_requirement():
    assert validate_leb7_gate(_gate_summary(retraction_creates_review_requirement=False))["ok"] is False
