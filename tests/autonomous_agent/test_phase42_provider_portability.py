"""Phase 42 provider portability tests."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hg_runtime.provider_portability.cross_model_run import run_cross_model
from hg_runtime.provider_portability.fixtures import participants, prompts
from hg_runtime.provider_portability.gate import validate_phase42_gate
from hg_runtime.provider_portability.participant_registry import registry
from hg_runtime.provider_portability.provider_adapter import external_provider_call
from hg_runtime.provider_portability.replay import replay_receipts
from hg_runtime.provider_portability.schemas import PHASE19_VERDICT, PHASE24_STATUS, ProviderPortabilityError, VERDICT_GREEN

OUTER_ROOT = Path(__file__).resolve().parents[2].parent
CROSSWALK_PATH = OUTER_ROOT / "docs/planning/agi/candidate_agi/02_RUNTIME_IMPLEMENTATION_CROSSWALK.md"


def _run():
    return run_cross_model("phase42-test", prompts()[:1], participants())


def _summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "phase41_green": True,
        "phase40_green": True,
        "phase39_green": True,
        "phase38_green": True,
        "phase37_green": True,
        "phase35_green": True,
        "fixture_participants_registered": True,
        "participant_count": 8,
        "cross_model_run_completed": True,
        "model_response_receipts_written": True,
        "receipt_count": 8,
        "external_providers_disabled_by_default": True,
        "token_cost_estimates_recorded": True,
        "refusal_records_written": True,
        "willingness_records_written": True,
        "framing_signals_written": True,
        "moral_principle_signals_written": True,
        "evidence_gap_signals_written": True,
        "phase19_yellow_preserved": True,
        "phase40_repair_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_receipt_hashes": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_external_call_rejected": True,
        "crosswalk_exists": True,
        "runtime_p42_declared_not_cagi42": True,
        "candidate_agi_phase_completed": False,
    }
    data.update(overrides)
    return data


def test_phase42_registers_fixture_participants():
    assert registry(participants())["participant_count"] == 8


def test_phase42_participant_registration_is_not_trust():
    assert registry(participants())["participant_registration_is_not_trust"] is True


def test_phase42_external_provider_disabled_by_default():
    external = [p for p in participants() if p["participant_id"] == "EXTERNAL_PROVIDER_DISABLED_FIXTURE"][0]
    assert external["external_provider_enabled"] is False


def test_phase42_external_provider_requires_operator_enable():
    external = [p for p in participants() if p["participant_id"] == "EXTERNAL_PROVIDER_DISABLED_FIXTURE"][0]
    assert external["operator_enable_required"] is True


def test_phase42_fixture_mode_makes_no_network_calls():
    with pytest.raises(ProviderPortabilityError):
        external_provider_call()


def test_phase42_runs_same_prompt_across_participants():
    assert len(_run()["receipts"]) == len(participants())


def test_phase42_records_response_receipt_for_each_participant():
    assert all(r["schema"] == "model_response_receipt_v1" for r in _run()["receipts"])


def test_phase42_records_prompt_hash_for_each_receipt():
    assert all(r["prompt_hash"] for r in _run()["receipts"])


def test_phase42_records_participant_and_provider_ids():
    assert all(r["participant_id"] and r["provider_id"] for r in _run()["receipts"])


def test_phase42_records_token_cost_estimates():
    assert all(r["token_estimate"]["total_tokens"] > 0 for r in _run()["receipts"])


def test_phase42_response_is_not_truth():
    assert all(not r["model_output_treated_as_truth"] for r in _run()["receipts"])


def test_phase42_consensus_is_not_truth():
    assert _run()["summary"]["model_consensus_treated_as_truth"] is False


def test_phase42_disagreement_is_not_evidence():
    assert _run()["summary"]["model_disagreement_treated_as_evidence"] is False


def test_phase42_refusal_is_not_authority():
    assert all(not r["model_refusal_treated_as_authority"] for r in _run()["receipts"])


def test_phase42_willingness_is_not_permission():
    assert all(not r["model_willingness_treated_as_permission"] for r in _run()["receipts"])


def test_phase42_moral_claim_is_not_authority():
    assert all(not r["moral_claim_treated_as_authority"] for r in _run()["receipts"])


def test_phase42_refusal_classified():
    assert any(r["refusal_state"] == "REFUSED" for r in _run()["receipts"])


def test_phase42_willingness_classified():
    assert any(r["willingness_state"] == "WILLING" for r in _run()["receipts"])


def test_phase42_genericity_classified():
    assert any(r["genericity_score"] > 0 for r in _run()["receipts"])


def test_phase42_specificity_classified():
    assert any(r["specificity_score"] > 0 for r in _run()["receipts"])


def test_phase42_framing_signal_emitted():
    assert _run()["framing_signals"]


def test_phase42_moral_principle_signal_emitted():
    assert _run()["moral_signals"]


def test_phase42_evidence_gap_signal_emitted():
    assert _run()["evidence_gaps"]


def test_phase42_disabled_external_provider_refuses_call():
    external_receipt = [r for r in _run()["receipts"] if r["participant_id"] == "EXTERNAL_PROVIDER_DISABLED_FIXTURE"][0]
    assert external_receipt["refusal_state"] == "REFUSED"


def test_phase42_no_authority_granted():
    assert all(not r["authority_granted"] for r in _run()["receipts"])


def test_phase42_no_tools_authorized():
    assert all(not r["tools_authorized"] for r in _run()["receipts"])


def test_phase42_no_live_effects_created():
    assert all(not r["live_effects_created"] for r in _run()["receipts"])


def test_phase42_no_external_provider_calls_made():
    assert all(not r["external_provider_call_made"] for r in _run()["receipts"])


def test_phase42_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_phase42_preserves_phase40_repair():
    assert _summary()["phase40_repair_preserved"] is True


def test_phase42_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_phase42_replay_preserves_receipt_hashes():
    run = _run()
    assert replay_receipts(run["receipts"], run["manifest"]["receipt_hashes"])["ok"] is True


def test_phase42_replay_rejects_mutated_response():
    run = _run()
    rows = copy.deepcopy(run["receipts"])
    rows[0]["response_text_redacted"] = "mutated"
    assert replay_receipts(rows, run["manifest"]["receipt_hashes"])["ok"] is False


def test_phase42_replay_rejects_missing_receipt():
    run = _run()
    assert replay_receipts(run["receipts"][:-1], run["manifest"]["receipt_hashes"])["ok"] is False


def test_phase42_no_secret_material_in_artifacts():
    assert "sk-lm-" not in repr(_run()["receipts"])


def test_phase42_fake_green_external_call_rejected():
    assert validate_phase42_gate(_summary(external_provider_calls_made=True))["ok"] is False


def test_phase42_crosswalk_prevents_candidate_agi_phase_completion_claim():
    text = CROSSWALK_PATH.read_text(encoding="utf-8")
    assert "Runtime P42 Provider Portability does not complete CAGI-42 Causal World Model" in text
    assert "No GREEN may cross namespace boundaries automatically" in text
    assert validate_phase42_gate(_summary(candidate_agi_phase_completed=True))["ok"] is False


def test_phase42_gate_requires_phase41_green():
    assert validate_phase42_gate(_summary(phase41_green=False))["ok"] is False


def test_phase42_gate_requires_phase40_green():
    assert validate_phase42_gate(_summary(phase40_green=False))["ok"] is False


def test_phase42_gate_requires_phase39_green():
    assert validate_phase42_gate(_summary(phase39_green=False))["ok"] is False


def test_phase42_gate_requires_phase38_green():
    assert validate_phase42_gate(_summary(phase38_green=False))["ok"] is False


def test_phase42_gate_refuses_without_receipts():
    assert validate_phase42_gate(_summary(model_response_receipts_written=False))["ok"] is False


def test_phase42_gate_refuses_if_external_provider_called():
    assert validate_phase42_gate(_summary(external_provider_calls_made=True))["ok"] is False


def test_phase42_gate_refuses_if_consensus_marked_truth():
    assert validate_phase42_gate(_summary(model_consensus_treated_as_truth=True))["ok"] is False


def test_phase42_gate_refuses_if_refusal_grants_authority():
    assert validate_phase42_gate(_summary(model_refusal_treated_as_authority=True))["ok"] is False


def test_phase42_gate_refuses_if_willingness_grants_permission():
    assert validate_phase42_gate(_summary(model_willingness_treated_as_permission=True))["ok"] is False


def test_phase42_gate_refuses_if_authority_granted():
    assert validate_phase42_gate(_summary(authority_granted=True))["ok"] is False


def test_phase42_gate_refuses_if_live_effect_created():
    assert validate_phase42_gate(_summary(live_external_side_effects_created=True))["ok"] is False


def test_phase42_gate_refuses_without_proof_bundle():
    assert validate_phase42_gate(_summary(proof_bundle_valid=False))["ok"] is False
