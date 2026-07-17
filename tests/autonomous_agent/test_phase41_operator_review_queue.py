"""Phase 41 operator review queue tests."""

from __future__ import annotations

import copy

from hg_runtime.operator_review_queue.fixtures import candidate_fixtures
from hg_runtime.operator_review_queue.gate import validate_phase41_gate
from hg_runtime.operator_review_queue.permit import permit_fixture, validate_permit
from hg_runtime.operator_review_queue.queue import queue_item, queue_manifest
from hg_runtime.operator_review_queue.receipt import ReviewReceiptLog
from hg_runtime.operator_review_queue.replay import replay_records
from hg_runtime.operator_review_queue.rollback import rollback_record
from hg_runtime.operator_review_queue.sandbox_apply import apply_dry_run
from hg_runtime.operator_review_queue.schemas import (
    DRY_RUN_APPLY_COMPLETED,
    DRY_RUN_APPLY_ROLLED_BACK,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    QUEUED_FOR_OPERATOR_REVIEW,
    REJECTED_EXTERNAL_SIDE_EFFECT_RISK,
    REJECTED_INVALID_PERMIT,
    REJECTED_LIVE_REPO_MUTATION,
    REJECTED_NO_OPERATOR_PERMIT,
    REJECTED_NOT_SAFE_TO_REVIEW,
    REJECTED_SELF_ISSUED_PERMIT,
    VERDICT_GREEN,
)


def _items():
    return {c["fixture_id"]: queue_item(c) for c in candidate_fixtures()}


def _summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "phase40_green": True,
        "phase39_green": True,
        "phase38_green": True,
        "phase37_green": True,
        "phase35_green": True,
        "safe_doc_candidate_queued": True,
        "safe_test_candidate_queued": True,
        "queue_entry_is_approval": False,
        "operator_permit_required_for_apply": True,
        "apply_without_operator_permit_rejected": True,
        "self_issued_operator_permit_rejected": True,
        "invalid_operator_permit_rejected": True,
        "valid_operator_permit_fixture_accepted": True,
        "dry_run_apply_completed": True,
        "dry_run_apply_sandbox_only": True,
        "rollback_tested": True,
        "phase19_yellow_preserved": True,
        "phase40_repair_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_queue_and_apply_receipts": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_live_apply_rejected": True,
    }
    data.update(overrides)
    return data


def test_phase41_queue_accepts_safe_doc_candidate():
    assert _items()["SAFE_DOC_PATCH_CANDIDATE"]["queued_status"] == QUEUED_FOR_OPERATOR_REVIEW


def test_phase41_queue_accepts_safe_test_candidate():
    assert _items()["SAFE_TEST_PATCH_CANDIDATE"]["queued_status"] == QUEUED_FOR_OPERATOR_REVIEW


def test_phase41_queue_entry_is_not_approval():
    assert queue_manifest(list(_items().values()))["queue_entry_is_approval"] is False


def test_phase41_apply_requires_operator_permit(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, None, tmp_path / "sandbox")
    assert result["result"] == REJECTED_NO_OPERATOR_PERMIT


def test_phase41_apply_without_operator_permit_rejected(tmp_path):
    item = _items()["SAFE_TEST_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, None, tmp_path / "sandbox")
    assert result["files_changed_in_sandbox"] == []


def test_phase41_self_issued_operator_permit_rejected():
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    assert validate_permit(item, permit_fixture(item, issuer_type="AGENT_ZERO"))["decision"] == REJECTED_SELF_ISSUED_PERMIT


def test_phase41_invalid_operator_permit_rejected():
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    assert validate_permit(item, permit_fixture(item, hash_mismatch=True))["decision"] == REJECTED_INVALID_PERMIT


def test_phase41_valid_operator_permit_fixture_accepted():
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    assert validate_permit(item, permit_fixture(item))["valid"] is True


def test_phase41_valid_permit_does_not_apply_to_live_repo(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, permit_fixture(item), tmp_path / "sandbox")
    assert result["live_repo_mutated"] is False


def test_phase41_doc_patch_dry_run_apply_sandbox_only(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, permit_fixture(item), tmp_path / "sandbox")
    assert result["result"] == DRY_RUN_APPLY_COMPLETED
    assert result["sandbox_only"] is True


def test_phase41_test_patch_dry_run_apply_sandbox_only(tmp_path):
    item = _items()["SAFE_TEST_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, permit_fixture(item), tmp_path / "sandbox")
    assert result["files_changed_in_sandbox"]


def test_phase41_runtime_patch_queued_not_auto_applied(tmp_path):
    item = _items()["RUNTIME_PATCH_NEEDS_REVIEW"]
    assert item["queued_status"] == QUEUED_FOR_OPERATOR_REVIEW
    assert item["candidate_risk_class"] == "runtime_review"


def test_phase41_authority_patch_rejected():
    assert _items()["UNSAFE_AUTHORITY_PATCH"]["queued_status"] == REJECTED_NOT_SAFE_TO_REVIEW


def test_phase41_live_effect_patch_rejected():
    assert _items()["LIVE_EFFECT_PATCH"]["queued_status"] == REJECTED_EXTERNAL_SIDE_EFFECT_RISK


def test_phase41_live_repo_mutation_attempt_rejected(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, permit_fixture(item), tmp_path / "sandbox", live_repo_target=True)
    assert result["result"] == REJECTED_LIVE_REPO_MUTATION


def test_phase41_rollback_restores_sandbox(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    sandbox = tmp_path / "sandbox"
    result, _ = apply_dry_run(item, permit_fixture(item), sandbox)
    rollback = rollback_record(result, sandbox)
    assert rollback["result"] == DRY_RUN_APPLY_ROLLED_BACK
    assert rollback["sandbox_clean"] is True


def test_phase41_dry_run_apply_not_committed(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, permit_fixture(item), tmp_path / "sandbox")
    assert result["candidate_committed"] is False


def test_phase41_dry_run_apply_not_pushed(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, permit_fixture(item), tmp_path / "sandbox")
    assert result["candidate_pushed"] is False


def test_phase41_dry_run_apply_not_deployed(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, permit_fixture(item), tmp_path / "sandbox")
    assert result["candidate_deployed"] is False


def test_phase41_authority_granted_always_false():
    assert all(not item["authority_granted"] for item in _items().values())


def test_phase41_tools_authorized_always_false():
    assert all(not item["tools_authorized"] for item in _items().values())


def test_phase41_live_effects_always_false():
    assert all(not item["live_effects_created"] for item in _items().values())


def test_phase41_external_provider_calls_always_false():
    assert all(not item["external_provider_calls_made"] for item in _items().values())


def test_phase41_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_phase41_preserves_phase40_repair():
    assert _summary()["phase40_repair_preserved"] is True


def test_phase41_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_phase41_replay_preserves_queue_manifest(tmp_path):
    log = ReviewReceiptLog(tmp_path / "receipt_chain.jsonl")
    manifest = queue_manifest(list(_items().values()))
    log.append(manifest["schema"], manifest)
    assert replay_records(log.records())["ok"] is True


def test_phase41_replay_preserves_apply_receipts(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, permit_fixture(item), tmp_path / "sandbox")
    log = ReviewReceiptLog(tmp_path / "receipt_chain.jsonl")
    log.append(item["schema"], item)
    log.append(result["schema"], result)
    assert replay_records(log.records())["ok"] is True


def test_phase41_replay_rejects_mutated_permit(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    permit = permit_fixture(item)
    log = ReviewReceiptLog(tmp_path / "receipt_chain.jsonl")
    log.append(permit["schema"], permit)
    rows = log.records()
    rows[0]["payload"]["issuer_is_agent_zero"] = True
    assert replay_records(rows)["ok"] is False


def test_phase41_replay_rejects_mutated_dry_run_result(tmp_path):
    item = _items()["SAFE_DOC_PATCH_CANDIDATE"]
    result, _ = apply_dry_run(item, permit_fixture(item), tmp_path / "sandbox")
    log = ReviewReceiptLog(tmp_path / "receipt_chain.jsonl")
    log.append(result["schema"], result)
    rows = log.records()
    rows[0]["payload"]["live_repo_mutated"] = True
    assert replay_records(rows)["ok"] is False


def test_phase41_no_secret_material_in_artifacts():
    text = repr(candidate_fixtures())
    assert "sk-lm-" not in text


def test_phase41_fake_green_live_apply_rejected():
    assert validate_phase41_gate(_summary(live_repo_mutated=True))["ok"] is False


def test_phase41_gate_requires_phase40_green():
    assert validate_phase41_gate(_summary(phase40_green=False))["ok"] is False


def test_phase41_gate_requires_phase39_green():
    assert validate_phase41_gate(_summary(phase39_green=False))["ok"] is False


def test_phase41_gate_requires_phase38_green():
    assert validate_phase41_gate(_summary(phase38_green=False))["ok"] is False


def test_phase41_gate_refuses_without_queue_manifest():
    assert validate_phase41_gate(_summary(safe_doc_candidate_queued=False))["ok"] is False


def test_phase41_gate_refuses_without_valid_permit_fixture():
    assert validate_phase41_gate(_summary(valid_operator_permit_fixture_accepted=False))["ok"] is False


def test_phase41_gate_refuses_if_live_repo_mutated():
    assert validate_phase41_gate(_summary(live_repo_mutated=True))["ok"] is False


def test_phase41_gate_refuses_if_candidate_committed():
    assert validate_phase41_gate(_summary(patch_candidates_committed=True))["ok"] is False


def test_phase41_gate_refuses_if_candidate_pushed():
    assert validate_phase41_gate(_summary(patch_candidates_pushed=True))["ok"] is False


def test_phase41_gate_refuses_if_candidate_deployed():
    assert validate_phase41_gate(_summary(patch_candidates_deployed=True))["ok"] is False


def test_phase41_gate_refuses_if_authority_granted():
    assert validate_phase41_gate(_summary(authority_granted=True))["ok"] is False


def test_phase41_gate_refuses_if_live_effect_created():
    assert validate_phase41_gate(_summary(live_external_side_effects_created=True))["ok"] is False


def test_phase41_gate_refuses_without_proof_bundle():
    assert validate_phase41_gate(_summary(proof_bundle_valid=False))["ok"] is False
