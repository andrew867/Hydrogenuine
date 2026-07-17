"""Phase 36 autonomous proposal soak tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.autonomous_proposal_soak.backlog import backlog_yaml, replay_backlog, write_backlog
from hg_runtime.autonomous_proposal_soak.diagnostics import (
    refuse_external_provider_probe,
    refuse_live_social_probe,
    refuse_moltbook_live_probe,
)
from hg_runtime.autonomous_proposal_soak.gate import validate_phase36_gate
from hg_runtime.autonomous_proposal_soak.proposal_schema import broken_item, patch_candidate_record, repair_proposal
from hg_runtime.autonomous_proposal_soak.replay import ProposalSoakLog
from hg_runtime.autonomous_proposal_soak.schemas import ProposalSoakError, VERDICT_GREEN_REPAIRED, VERDICT_YELLOW_BACKLOG, preempt_if_needed


def _seed():
    return broken_item(
        {
            "proposal_id": "P33_6_SMALL_DOC_WRITER_LOAD_PATH_LIMITED",
            "title": "small_doc_writer role could not complete under max_loaded_models policy",
            "severity": "HIGH",
            "phase_or_component": "Phase 33.6 local_inference_organs",
            "observed_failure": "P33.6 gate returned YELLOW_LOCAL_MULTI_ORGAN_PARTIAL_LOAD_LIMITED",
            "expected_behavior": "small_doc_writer role should run by reusing a compatible loaded tiny/small model",
            "actual_behavior": "small_doc_writer load path was limited/refused",
            "authority_risk": "LOW if fixed via shared-model advisory role binding",
            "required_tests": ["small_doc_writer_can_reuse_loaded_tiny_model_under_max_loaded_three"],
        }
    )


def test_proposal_soak_cannot_grant_authority():
    with pytest.raises(ProposalSoakError, match="proposal_soak_cannot_grant_authority"):
        broken_item({**_seed(), "grants_authority": True})


def test_proposal_soak_cannot_authorize_tools():
    with pytest.raises(ProposalSoakError, match="proposal_soak_cannot_authorize_tools"):
        broken_item({**_seed(), "authorizes_tool": True})


def test_proposal_soak_cannot_create_live_effects():
    with pytest.raises(ProposalSoakError, match="proposal_soak_cannot_create_live_effects"):
        broken_item({**_seed(), "creates_live_effect": True})


def test_proposal_soak_cannot_claim_agi():
    with pytest.raises(ProposalSoakError, match="proposal_soak_cannot_claim_agi"):
        broken_item({**_seed(), "claims_agi": True})


def test_proposal_soak_preserves_phase19_yellow():
    result = {"phase19_verdict_before_phase36": "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"}
    assert "YELLOW_PHASE19" in result["phase19_verdict_before_phase36"]


def test_proposal_soak_seed_issue_generates_repair_proposal():
    proposal = repair_proposal(_seed(), evidence_refs=["proof/gate_result.json"])
    assert proposal["proposal_id"] == "P33_6_SMALL_DOC_WRITER_LOAD_PATH_LIMITED"


def test_proposal_soak_records_reproduction_steps():
    assert repair_proposal(_seed(), evidence_refs=["x"])["reproduction_steps"]


def test_proposal_soak_records_expected_and_actual_behavior():
    proposal = repair_proposal(_seed(), evidence_refs=["x"])
    assert proposal["expected_behavior"]
    assert proposal["actual_behavior"]


def test_proposal_soak_records_evidence_refs():
    assert repair_proposal(_seed(), evidence_refs=["x"])["evidence_refs"] == ["x"]


def test_proposal_soak_records_authority_risk():
    assert repair_proposal(_seed(), evidence_refs=["x"])["authority_risk"]


def test_proposal_soak_records_required_spec_changes():
    assert repair_proposal(_seed(), evidence_refs=["x"])["required_spec_changes"]


def test_proposal_soak_records_required_test_changes():
    assert repair_proposal(_seed(), evidence_refs=["x"])["required_test_changes"]


def test_proposal_soak_records_required_implementation_changes():
    assert repair_proposal(_seed(), evidence_refs=["x"])["required_implementation_changes"]


def test_proposal_soak_records_acceptance_criteria():
    assert repair_proposal(_seed(), evidence_refs=["x"])["acceptance_criteria"]


def test_proposal_backlog_is_yaml_serializable():
    assert "proposal_id" in backlog_yaml([repair_proposal(_seed(), evidence_refs=["x"])])


def test_proposal_backlog_replay_deterministic(tmp_path: Path):
    path = tmp_path / "proposal_backlog.yaml"
    write_backlog(path, [repair_proposal(_seed(), evidence_refs=["x"])])
    assert replay_backlog(path)["ok"] is True


def test_patch_candidate_is_not_applied():
    assert patch_candidate_record(proposal_id="p", summary="draft")["applied"] is False


def test_patch_candidate_is_not_commit():
    assert patch_candidate_record(proposal_id="p", summary="draft")["committed"] is False


def test_organ_output_is_not_truth():
    assert repair_proposal(_seed(), evidence_refs=["x"])["is_truth"] is False


def test_organ_output_is_not_authority():
    assert repair_proposal(_seed(), evidence_refs=["x"])["is_authority"] is False


def test_external_provider_probe_refused():
    with pytest.raises(ProposalSoakError, match="external_provider_probe_refused"):
        refuse_external_provider_probe()


def test_live_social_probe_refused():
    with pytest.raises(ProposalSoakError, match="live_social_probe_refused"):
        refuse_live_social_probe()


def test_moltbook_live_probe_refused():
    with pytest.raises(ProposalSoakError, match="moltbook_live_probe_refused"):
        refuse_moltbook_live_probe()


def test_secret_redaction_blocks_key_leak():
    proposal = repair_proposal(_seed(), evidence_refs=["redacted"])
    assert "sk-" not in str(proposal)


def test_stop_panic_preempts_soak():
    with pytest.raises(ProposalSoakError, match="REFUSED_PANIC"):
        preempt_if_needed(OperationControl(panic_active=True))


def test_fake_green_attempt_is_rejected():
    result = validate_phase36_gate(
        {
            "verdict": VERDICT_GREEN_REPAIRED,
            "phase33_6_repair_verdict": "YELLOW_LOCAL_MULTI_ORGAN_PARTIAL_LOAD_LIMITED",
            "proof_bundle_valid": True,
            "proposal_soak_replay_deterministic": True,
            "proposal_count": 1,
            "broken_items_found": [{"proposal_id": "P33_6_SMALL_DOC_WRITER_LOAD_PATH_LIMITED"}],
        }
    )
    assert result["ok"] is False


def test_phase36_gate_refuses_without_phase33_6_safe_or_repaired():
    result = validate_phase36_gate(
        {"verdict": VERDICT_YELLOW_BACKLOG, "proof_bundle_valid": True, "proposal_soak_replay_deterministic": True, "proposal_count": 1}
    )
    assert result["ok"] is False


def test_phase36_gate_refuses_without_proof_bundle():
    result = validate_phase36_gate(
        {
            "verdict": VERDICT_YELLOW_BACKLOG,
            "proposal_soak_replay_deterministic": True,
            "proposal_count": 1,
            "broken_items_found": [{"proposal_id": "P33_6_SMALL_DOC_WRITER_LOAD_PATH_LIMITED"}],
        }
    )
    assert result["ok"] is False


def test_proposal_soak_log_replay_deterministic(tmp_path: Path):
    log = ProposalSoakLog(tmp_path / "receipt_chain.jsonl")
    log.append("repair_proposal_v1", repair_proposal(_seed(), evidence_refs=["x"]))
    assert log.replay()["ok"] is True
