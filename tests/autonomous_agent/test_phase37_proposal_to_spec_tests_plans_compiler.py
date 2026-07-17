"""Phase 37 proposal-to-spec/tests/plans compiler tests."""

from __future__ import annotations

import copy
import json

from hg_runtime.proposal_compiler.compiler import compile_proposal
from hg_runtime.proposal_compiler.executor_prompt import SINGLE_WRITER_SENTINEL
from hg_runtime.proposal_compiler.fixtures import (
    GENERIC_LOW_SPECIFICITY,
    LIVE_SOCIAL_ACTION,
    LOCAL_TEST_FAILURE_REPAIR,
    READY_OUTPUT_CONFORMITY,
    TOOL_AUTHORITY_BYPASS,
    all_fixtures,
)
from hg_runtime.proposal_compiler.gate import validate_phase37_gate
from hg_runtime.proposal_compiler.input_loader import contains_secret
from hg_runtime.proposal_compiler.replay import CompilerLog
from hg_runtime.proposal_compiler.schemas import (
    REQUIRED_WORK_PACKAGE_DOCS,
    STATUS_LIVE_BLOCKED,
    STATUS_NOT_READY,
    STATUS_READY,
    STATUS_REFUSED,
    VERDICT_GREEN,
)


def _ready():
    return compile_proposal(READY_OUTPUT_CONFORMITY)


def _green_summary(**overrides):
    base = {
        "verdict": VERDICT_GREEN,
        "phase35_green": True,
        "phase36_green": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "ready_compiled_count": 2,
        "low_specificity_proposal_rejected": True,
        "live_action_proposal_rejected": True,
        "authority_bypass_proposal_rejected": True,
        "every_ready_package_has_all_docs": True,
        "every_package_has_receipt": True,
        "executor_prompt_preserves_safety_boundaries": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "fake_green_not_ready_proposal_rejected": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    base.update(overrides)
    return base


# --- classification ---------------------------------------------------------


def test_phase37_compiler_accepts_ready_proposal():
    result = _ready()
    assert result["status"] == STATUS_READY
    assert result["is_ready_package"] is True
    assert compile_proposal(LOCAL_TEST_FAILURE_REPAIR)["status"] == STATUS_READY


def test_phase37_compiler_rejects_low_specificity_proposal():
    assert compile_proposal(GENERIC_LOW_SPECIFICITY)["status"] == STATUS_NOT_READY


def test_phase37_compiler_rejects_ungrounded_proposal():
    proposal = {**copy.deepcopy(READY_OUTPUT_CONFORMITY), "evidence_refs": []}
    result = compile_proposal(proposal)
    assert result["status"] == STATUS_NOT_READY
    assert "evidence_refs" in result["classification"]["missing_fields"]


def test_phase37_compiler_rejects_missing_acceptance_criteria():
    proposal = {**copy.deepcopy(READY_OUTPUT_CONFORMITY), "acceptance_criteria": []}
    result = compile_proposal(proposal)
    assert result["status"] == STATUS_NOT_READY
    assert "testable_acceptance_criteria" in result["classification"]["missing_fields"]


def test_phase37_compiler_rejects_live_action_request():
    result = compile_proposal(LIVE_SOCIAL_ACTION)
    assert result["status"] == STATUS_LIVE_BLOCKED
    assert result["classification"]["live_action_hits"]


def test_phase37_compiler_rejects_authority_bypass_attempt():
    result = compile_proposal(TOOL_AUTHORITY_BYPASS)
    assert result["status"] == STATUS_REFUSED
    assert result["classification"]["authority_bypass_hits"]


# --- document generation ----------------------------------------------------


def test_phase37_compiler_generates_index():
    assert "00_INDEX.md" in _ready()["docs"]


def test_phase37_compiler_generates_spec_update():
    doc = _ready()["docs"]["01_SPEC_UPDATE.md"]
    assert "Required Behavior" in doc and "Acceptance Criteria" in doc


def test_phase37_compiler_generates_test_plan_update():
    doc = _ready()["docs"]["02_TEST_PLAN_UPDATE.md"]
    assert "purpose:" in doc and "failure_if:" in doc


def test_phase37_compiler_generates_implementation_plan_update():
    doc = _ready()["docs"]["03_IMPLEMENTATION_PLAN_UPDATE.md"]
    assert "Implementation Steps" in doc and "Rollback Plan" in doc


def test_phase37_compiler_generates_milestone_update():
    doc = _ready()["docs"]["04_MILESTONE_UPDATE.md"]
    assert "green_criteria" in doc and "red_criteria" in doc


def test_phase37_compiler_generates_risk_register_update():
    doc = _ready()["docs"]["05_RISK_REGISTER_UPDATE.md"]
    assert "risk_id" not in doc  # rendered ids are concrete
    assert "severity" in doc and "mitigation" in doc and "residual_risk" in doc


def test_phase37_compiler_generates_executor_prompt():
    assert "06_EXECUTOR_PROMPT.md" in _ready()["docs"]


# --- executor-prompt safety boundaries --------------------------------------


def test_phase37_executor_prompt_preserves_single_writer_rule():
    prompt = _ready()["docs"]["06_EXECUTOR_PROMPT.md"]
    assert "single writer" in prompt.lower()
    assert SINGLE_WRITER_SENTINEL in prompt


def test_phase37_executor_prompt_preserves_no_fetch_no_push():
    prompt = _ready()["docs"]["06_EXECUTOR_PROMPT.md"]
    assert "Do not fetch" in prompt and "Do not push" in prompt


def test_phase37_executor_prompt_preserves_no_live_side_effects():
    prompt = _ready()["docs"]["06_EXECUTOR_PROMPT.md"]
    assert "No Live Side Effects" in prompt
    assert "Do not grant authority" in prompt and "Do not authorize tools" in prompt


def test_phase37_executor_prompt_requires_tests_and_gate():
    prompt = _ready()["docs"]["06_EXECUTOR_PROMPT.md"]
    assert "Required Tests" in prompt and "Required Gate Behavior" in prompt


def test_phase37_executor_prompt_requires_final_yaml():
    prompt = _ready()["docs"]["06_EXECUTOR_PROMPT.md"]
    assert "Final YAML" in prompt and "verdict:" in prompt


# --- receipts / determinism -------------------------------------------------


def test_phase37_work_package_has_receipt():
    receipt = _ready()["receipt"]
    assert receipt["receipt_hash"].startswith("sha256:")
    assert receipt["package_hash"].startswith("sha256:")


def test_phase37_work_package_hash_deterministic():
    assert _ready()["package_hash"] == _ready()["package_hash"]
    # all required docs present in a ready package
    assert set(REQUIRED_WORK_PACKAGE_DOCS).issubset(_ready()["docs"])


def test_phase37_replay_deterministic(tmp_path):
    log = CompilerLog(tmp_path / "chain.jsonl")
    for result in (compile_proposal(f) for f in all_fixtures()):
        log.append("compiled_work_package_v1", result["receipt"])
    replay = log.replay()
    assert replay["ok"] is True
    # reopening replays identically
    assert CompilerLog(tmp_path / "chain.jsonl").replay()["chain_root"] == replay["chain_root"]


# --- the compiler does not act ----------------------------------------------


def test_phase37_does_not_implement_fix():
    result = _ready()
    assert result["fix_implemented_by_compiler"] is False
    assert result["patch_applied_by_compiler"] is False


def test_phase37_does_not_apply_patch():
    assert _ready()["patch_applied_by_compiler"] is False


def test_phase37_does_not_authorize_tools():
    assert _ready()["authorizes_tool"] is False


def test_phase37_does_not_grant_authority():
    assert _ready()["grants_authority"] is False


def test_phase37_does_not_create_live_effects():
    assert _ready()["creates_live_effect"] is False


# --- boundary preservation --------------------------------------------------


def test_phase37_preserves_phase19_yellow():
    assert validate_phase37_gate(_green_summary(phase19_yellow_preserved=False))["ok"] is False


def test_phase37_preserves_phase24_infrastructure_only():
    assert validate_phase37_gate(_green_summary(phase24_infrastructure_only_preserved=False))["ok"] is False


# --- redaction / fake-green -------------------------------------------------


def test_phase37_secret_redaction_blocks_key_leak():
    proposal = {**copy.deepcopy(LOCAL_TEST_FAILURE_REPAIR), "observed_failure": "leak sk-ABCDEFGH12345678 here"}
    result = compile_proposal(proposal)
    blob = json.dumps(result["docs"])
    assert "sk-ABCDEFGH12345678" not in blob
    assert not any(contains_secret(content) for content in result["docs"].values())


def test_phase37_fake_green_not_ready_proposal_rejected():
    result = compile_proposal(GENERIC_LOW_SPECIFICITY)
    assert result["status"] != STATUS_READY
    assert not set(REQUIRED_WORK_PACKAGE_DOCS).issubset(result["docs"])
    assert result["has_executor_prompt"] is False


# --- gate substrate dependency ----------------------------------------------


def test_phase37_gate_refuses_without_phase35_green():
    result = validate_phase37_gate(_green_summary(phase35_green=False))
    assert result["ok"] is False
    assert "phase37_gate_refuses_without_phase35_green" in result["failures"]


def test_phase37_gate_refuses_without_phase36_green():
    result = validate_phase37_gate(_green_summary(phase36_green=False))
    assert result["ok"] is False
    assert "phase37_gate_refuses_without_phase36_green" in result["failures"]


def test_phase37_gate_accepts_full_green_summary():
    assert validate_phase37_gate(_green_summary())["ok"] is True
