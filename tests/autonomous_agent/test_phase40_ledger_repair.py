"""Phase 40 ledger repair tests."""

from __future__ import annotations

from hg_runtime.ledger_repair.closure_record import closure_record
from hg_runtime.ledger_repair.evidence_exclusion import audit_evidence_claim, polluted_evidence_exclusion
from hg_runtime.ledger_repair.fixtures import build_fixture_records
from hg_runtime.ledger_repair.gate import validate_phase40_gate
from hg_runtime.ledger_repair.incident_registry import clean_incident_fixture, incident_record, phase19_incident_findable
from hg_runtime.ledger_repair.permit_boundary import boundary_decision, operator_permit_record, operator_permit_request, patch_queue_item
from hg_runtime.ledger_repair.repair_record import repair_record, repair_request
from hg_runtime.ledger_repair.replay import RepairLog, replay_records
from hg_runtime.ledger_repair.schemas import CLOSURE_BOUNDED, LedgerRepairError, PHASE19_INCIDENT_ID, VERDICT_GREEN


def _summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "phase39_green": True,
        "phase38_green": True,
        "phase37_green": True,
        "phase35_green": True,
        "phase19_incident_recorded": True,
        "original_phase19_incident_preserved": True,
        "phase19_yellow_preserved_after_repair": True,
        "repair_is_append_only": True,
        "polluted_evidence_excluded_from_clean_claims": True,
        "operator_permit_required_for_patch_apply": True,
        "replay_preserves_repair_chain": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_repair_rejected": True,
    }
    data.update(overrides)
    return data


def test_phase40_records_phase19_incident():
    assert incident_record()["incident_id"] == PHASE19_INCIDENT_ID


def test_phase40_repair_record_append_only():
    assert repair_record(incident_record())["repair_type"] == "APPEND_ONLY_COMPENSATING_RECORD"


def test_phase40_repair_preserves_original_incident():
    assert repair_record(incident_record())["original_record_preserved"] is True


def test_phase40_repair_rejects_delete_original():
    with __import__("pytest").raises(LedgerRepairError):
        repair_request(incident_record(), delete_original=True)


def test_phase40_repair_rejects_rewrite_original():
    with __import__("pytest").raises(LedgerRepairError):
        repair_request(incident_record(), rewrite_original=True)


def test_phase40_repair_rejects_mark_original_green():
    with __import__("pytest").raises(LedgerRepairError):
        repair_request(incident_record(), mark_original_green=True)


def test_phase40_phase19_yellow_preserved():
    assert "YELLOW_PHASE19" in repair_record(incident_record())["source_verdict"]


def test_phase40_phase24_infrastructure_only_preserved():
    assert closure_record(incident_record(), repair_record(incident_record()))["phase24_infrastructure_only_preserved"] is True


def test_phase40_incident_closure_bounded_not_erased():
    assert closure_record(incident_record(), repair_record(incident_record()))["closure_status"] == CLOSURE_BOUNDED


def test_phase40_polluted_evidence_excluded_from_clean_claims():
    assert polluted_evidence_exclusion(repair_record(incident_record()))["excluded_from_clean_live_claims"] is True


def test_phase40_polluted_evidence_clean_claim_rejected():
    assert audit_evidence_claim(polluted_evidence_exclusion(repair_record(incident_record())), claim_type="clean_live")["claim_allowed"] is False


def test_phase40_clean_incident_fixture_passes():
    assert audit_evidence_claim(clean_incident_fixture(), claim_type="clean_live")["claim_allowed"] is True


def test_phase40_invalid_green_laundering_rejected():
    assert validate_phase40_gate(_summary(phase19_yellow_preserved_after_repair=False))["ok"] is False


def test_phase40_original_incident_still_findable():
    assert phase19_incident_findable([incident_record()]) is True


def test_phase40_repair_record_hash_deterministic():
    assert repair_record(incident_record())["repair_record_hash"] == repair_record(incident_record())["repair_record_hash"]


def test_phase40_closure_hash_deterministic():
    i = incident_record(); r = repair_record(i)
    assert closure_record(i, r)["closure_hash"] == closure_record(i, r)["closure_hash"]


def test_phase40_replay_preserves_repair_chain(tmp_path):
    log = RepairLog(tmp_path / "r.jsonl"); rec = repair_record(incident_record()); log.append(rec["schema"], rec)
    assert replay_records(log.records())["ok"] is True


def test_phase40_replay_rejects_mutated_repair_record(tmp_path):
    log = RepairLog(tmp_path / "r.jsonl"); rec = repair_record(incident_record()); log.append(rec["schema"], rec)
    rows = log.records(); rows[0]["payload"]["repair_type"] = "REWRITE"
    assert replay_records(rows)["ok"] is False


def test_phase40_replay_rejects_missing_original_hash(tmp_path):
    log = RepairLog(tmp_path / "r.jsonl"); rec = repair_record(incident_record()); rec["original_record_hash"] = ""; log.append(rec["schema"], rec)
    assert replay_records(log.records())["ok"] is False


def test_phase40_patch_apply_without_operator_permit_rejected():
    assert boundary_decision(patch_queue_item())["decision"] == "REJECTED_NO_OPERATOR_PERMIT"


def test_phase40_operator_permit_cannot_be_self_issued():
    req = operator_permit_request(issuer="agent_zero")
    assert operator_permit_record(req)["operator_permit_valid"] is False


def test_phase40_valid_operator_permit_records_apply_deferred():
    req = operator_permit_request(); permit = operator_permit_record(req)
    assert boundary_decision(patch_queue_item(), permit)["decision"] == "PERMIT_RECORDED_APPLY_DEFERRED"


def test_phase40_valid_operator_permit_does_not_apply_code():
    req = operator_permit_request(); permit = operator_permit_record(req)
    assert boundary_decision(patch_queue_item(), permit)["candidate_applied"] is False


def test_phase40_patch_candidate_not_committed():
    assert boundary_decision(patch_queue_item())["candidate_committed"] is False


def test_phase40_patch_candidate_not_pushed():
    assert boundary_decision(patch_queue_item())["candidate_pushed"] is False


def test_phase40_patch_candidate_not_deployed():
    assert boundary_decision(patch_queue_item())["candidate_deployed"] is False


def test_phase40_authority_granted_always_false():
    assert repair_record(incident_record())["authority_granted"] is False


def test_phase40_tools_authorized_always_false():
    assert repair_record(incident_record())["tools_authorized"] is False


def test_phase40_live_effects_always_false():
    assert repair_record(incident_record())["live_effects_created"] is False


def test_phase40_live_posts_always_false():
    assert repair_record(incident_record())["created_live_posts"] is False


def test_phase40_external_provider_calls_always_false():
    assert repair_record(incident_record())["created_external_side_effects"] is False


def test_phase40_no_secret_material_in_artifacts():
    assert "sk-" not in str(build_fixture_records())


def test_phase40_fake_green_repair_rejected():
    assert validate_phase40_gate({"verdict": VERDICT_GREEN, "phase39_green": True})["ok"] is False


def test_phase40_gate_requires_phase39_green():
    assert validate_phase40_gate(_summary(phase39_green=False))["ok"] is False


def test_phase40_gate_requires_phase38_green():
    assert validate_phase40_gate(_summary(phase38_green=False))["ok"] is False


def test_phase40_gate_requires_phase37_green():
    assert validate_phase40_gate(_summary(phase37_green=False))["ok"] is False


def test_phase40_gate_refuses_if_phase19_marked_green():
    assert validate_phase40_gate(_summary(phase19_yellow_preserved_after_repair=False))["ok"] is False


def test_phase40_gate_refuses_if_original_incident_missing():
    assert validate_phase40_gate(_summary(original_phase19_incident_preserved=False))["ok"] is False


def test_phase40_gate_refuses_if_repair_rewrites_original():
    assert validate_phase40_gate(_summary(repair_rewrote_original=True))["ok"] is False


def test_phase40_gate_refuses_if_polluted_evidence_used_for_clean_claim():
    assert validate_phase40_gate(_summary(clean_live_claim_allowed_from_polluted_evidence=True))["ok"] is False


def test_phase40_gate_refuses_if_patch_applied():
    assert validate_phase40_gate(_summary(patch_candidates_applied=True))["ok"] is False


def test_phase40_gate_refuses_if_authority_granted():
    assert validate_phase40_gate(_summary(authority_granted=True))["ok"] is False


def test_phase40_gate_refuses_if_live_effect_created():
    assert validate_phase40_gate(_summary(live_external_side_effects_created=True))["ok"] is False


def test_phase40_gate_refuses_without_proof_bundle():
    assert validate_phase40_gate(_summary(proof_bundle_valid=False))["ok"] is False
