"""LEB-5 evidence review queue tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.local_evidence_bridge.evidence_review_queue import (
    build_fixture_targets,
    build_review_queue,
    validate_leb5_gate,
)
from hg_runtime.local_evidence_bridge.redaction import secret_scan
from hg_runtime.local_evidence_bridge.review_policy import build_review_policy, classify_target
from hg_runtime.local_evidence_bridge.review_replay import replay_review_queue
from hg_runtime.local_evidence_bridge.review_task import build_review_task
from hg_runtime.local_evidence_bridge.schemas import EvidenceBridgeError, PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]


def _queue(fever_level="NORMAL"):
    return build_review_queue(targets=build_fixture_targets(ROOT), fever_level=fever_level)


def _gate_summary(**overrides):
    data = {
        "verdict": "GREEN_LEB_5_EVIDENCE_REVIEW_QUEUE",
        "review_tasks_written": True,
        "review_manifest_written": True,
        "review_policy_written": True,
        "review_task_not_action": True,
        "review_task_not_belief_promotion": True,
        "review_task_not_tool_authorization": True,
        "review_task_not_operator_approval": True,
        "suspicious_recommends_quarantine_candidate": True,
        "high_fever_restricts_review_flow": True,
        "no_automatic_patching": True,
        "no_deletion": True,
        "replay_preserves_review_hashes": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Queue construction ----------------------------------------------------

def test_leb5_builds_review_tasks():
    q = _queue()
    assert q["manifest"]["task_count"] == 4
    assert all(t["record_type"] == "evidence_review_task_v1" for t in q["tasks"])


def test_leb5_review_task_is_not_action():
    for t in _queue()["tasks"]:
        assert t["review_task_is_action"] is False


def test_leb5_review_task_is_not_belief_promotion():
    for t in _queue()["tasks"]:
        assert t["review_task_is_belief_promotion"] is False
        assert t["belief_promoted"] is False


def test_leb5_review_task_is_not_tool_authorization():
    for t in _queue()["tasks"]:
        assert t["review_task_is_tool_authorization"] is False
        assert t["tools_authorized"] is False


def test_leb5_review_task_is_not_operator_approval():
    for t in _queue()["tasks"]:
        assert t["review_task_is_operator_approval"] is False


def test_leb5_default_status_is_pending_operator_review():
    for t in _queue()["tasks"]:
        assert t["review_status"] == "PENDING_OPERATOR_REVIEW"


# --- Suspicious / quarantine candidate ------------------------------------

def test_leb5_suspicious_recommends_quarantine_candidate():
    q = _queue()
    assert q["manifest"]["quarantine_candidate_count"] >= 2
    assert any(t["recommended_action"] == "QUARANTINE_CANDIDATE" for t in q["tasks"])


def test_leb5_redaction_flagged_is_quarantine_candidate():
    action, reason = classify_target({"record_type": "x", "secret_like_content_redacted": True})
    assert action == "QUARANTINE_CANDIDATE"
    assert reason == "redaction_flagged_suspicious"


def test_leb5_contradiction_is_quarantine_candidate():
    action, _ = classify_target({"record_type": "evidence_claim_link_v1", "link_kind": "CONTRADICTION_CANDIDATE"})
    assert action == "QUARANTINE_CANDIDATE"


def test_leb5_quarantine_candidate_is_not_deletion():
    for t in _queue()["tasks"]:
        assert t["deletion_performed"] is False


# --- Fever restriction -----------------------------------------------------

def test_leb5_high_fever_restricts_review_flow():
    q = _queue("RED_FEVER")
    assert q["manifest"]["review_flow_restricted"] is True
    assert all(t["review_status"] == "RESTRICTED_PENDING_OPERATOR_REVIEW" for t in q["tasks"])


def test_leb5_panic_fever_restricts_review_flow():
    q = _queue("PANIC_FEVER")
    assert q["manifest"]["review_flow_restricted"] is True
    assert q["policy"]["restrictions"]


def test_leb5_normal_fever_not_restricted():
    q = _queue("NORMAL")
    assert q["manifest"]["review_flow_restricted"] is False


def test_leb5_fever_never_unlocks_action():
    assert build_review_policy(fever_level="PANIC_FEVER")["fever_unlocks_action"] is False


# --- No patching / deletion ------------------------------------------------

def test_leb5_policy_no_automatic_patching_or_deletion():
    p = build_review_policy()
    assert p["automatic_patching_enabled"] is False
    assert p["deletion_enabled"] is False


def test_leb5_invalid_recommended_action_rejected():
    with pytest.raises(EvidenceBridgeError):
        build_review_task(
            task_id="t", target={"record_type": "x"}, recommended_action="DELETE",
            reason="r", fever_level="NORMAL", restricted=False,
        )


# --- Replay & secrets ------------------------------------------------------

def test_leb5_replay_preserves_review_hashes():
    q = _queue()
    assert replay_review_queue(q["tasks"], q["manifest"])["replay_preserves_review_hashes"] is True


def test_leb5_replay_rejects_mutated_task():
    q = _queue()
    mutated = [dict(t) for t in q["tasks"]]
    mutated[0]["recommended_action"] = "QUARANTINE_CANDIDATE"
    mutated[0]["review_status"] = "TAMPERED"
    assert replay_review_queue(mutated, q["manifest"])["replay_preserves_review_hashes"] is False


def test_leb5_no_secret_material_in_tasks():
    assert secret_scan(_queue()) is True


# --- Prior phases ----------------------------------------------------------

def test_leb5_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_leb5_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


# --- Gate ------------------------------------------------------------------

def test_leb5_gate_passes_on_full_summary():
    assert validate_leb5_gate(_gate_summary())["ok"] is True


def test_leb5_gate_refuses_if_review_task_is_action():
    assert validate_leb5_gate(_gate_summary(review_task_not_action=False))["ok"] is False


def test_leb5_gate_refuses_if_belief_promotion():
    assert validate_leb5_gate(_gate_summary(automatic_belief_promotion=True))["ok"] is False


def test_leb5_gate_refuses_if_deletion():
    assert validate_leb5_gate(_gate_summary(deletion_performed=True))["ok"] is False


def test_leb5_gate_refuses_if_automatic_patching():
    assert validate_leb5_gate(_gate_summary(automatic_patching_enabled=True))["ok"] is False


def test_leb5_gate_refuses_if_fever_unlocks_action():
    assert validate_leb5_gate(_gate_summary(fever_unlocks_action=True))["ok"] is False


def test_leb5_gate_refuses_if_no_quarantine_candidate():
    assert validate_leb5_gate(_gate_summary(suspicious_recommends_quarantine_candidate=False))["ok"] is False


def test_leb5_gate_refuses_if_web_browse():
    assert validate_leb5_gate(_gate_summary(web_browse_performed=True))["ok"] is False
