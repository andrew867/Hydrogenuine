"""Phase 38 patch candidate sandbox and diff auditor tests.

Proves the sandbox prepares operator-reviewable patch candidates without ever
applying a patch, granting authority, authorizing a tool, or creating a live
effect. A patch candidate is not applied code; a diff audit is not approval; a
SAFE_TO_REVIEW verdict is not merge permission.
"""

from __future__ import annotations

import pytest

from hg_runtime.patch_candidate_sandbox import evaluate_patch_candidate
from hg_runtime.patch_candidate_sandbox.artifact_writer import write_candidate_artifact
from hg_runtime.patch_candidate_sandbox.diff_parser import parse_unified_diff
from hg_runtime.patch_candidate_sandbox.fixtures import all_fixtures
from hg_runtime.patch_candidate_sandbox.gate import validate_phase38_gate
from hg_runtime.patch_candidate_sandbox.patch_candidate import build_patch_candidate, candidate_hash
from hg_runtime.patch_candidate_sandbox.replay import PatchSandboxLog
from hg_runtime.patch_candidate_sandbox.risk_classifier import (
    classify_path,
    detect_sandbox_escape,
)
from hg_runtime.patch_candidate_sandbox.sandbox import sandbox_plan
from hg_runtime.patch_candidate_sandbox.schemas import (
    DECISION_NEEDS_HUMAN_REVIEW,
    DECISION_REJECTED_AUTHORITY_BYPASS,
    DECISION_REJECTED_LIVE_ACTION,
    DECISION_REJECTED_NOT_READY,
    DECISION_REJECTED_SANDBOX_ESCAPE,
    DECISION_REJECTED_SECRET_RISK,
    DECISION_SAFE_TO_REVIEW,
    REJECTED_DECISIONS,
    RISK_AUTHORITY_KERNEL,
    RISK_DOC_ONLY,
    SANDBOX_ARTIFACT_ONLY,
    SandboxError,
    VERDICT_GREEN,
    VERDICT_RED,
    assert_neutral_output,
)


def _by_name() -> dict[str, dict]:
    return {f["name"]: evaluate_patch_candidate(f["source"], f["patch_text"], label=f["label"]) for f in all_fixtures()}


def _ready_source(suffix: str = "X") -> dict:
    return {"proposal_id": f"READY_{suffix}", "status": "READY", "package_hash": f"sha256:ready{suffix.lower()}0000"}


def _loaded_ready(suffix: str = "X") -> dict:
    from hg_runtime.patch_candidate_sandbox.work_package_loader import load_work_package

    return load_work_package(_ready_source(suffix))


# --- eligibility ------------------------------------------------------------


def test_phase38_accepts_ready_work_package():
    bundle = _by_name()["READY_DOC_ONLY_PATCH"]
    assert bundle["eligible"] is True
    assert bundle["source"]["is_ready"] is True


def test_phase38_rejects_not_ready_source_package():
    bundle = _by_name()["NOT_READY_SOURCE_PACKAGE"]
    assert bundle["decision"] == DECISION_REJECTED_NOT_READY


def test_phase38_not_ready_source_produces_no_candidate():
    bundle = _by_name()["NOT_READY_SOURCE_PACKAGE"]
    assert bundle["candidate"] is None
    assert bundle["candidate_produced"] is False


def test_phase38_live_self_blocked_source_maps_to_live_action():
    src = {"proposal_id": "LSB", "status": "LIVE_SELF_BLOCKED", "package_hash": "sha256:lsb0"}
    bundle = evaluate_patch_candidate(src, "")
    assert bundle["decision"] == DECISION_REJECTED_LIVE_ACTION


def test_phase38_red_refused_source_maps_to_authority_bypass():
    src = {"proposal_id": "RR", "status": "RED_REFUSED", "package_hash": "sha256:rr0"}
    bundle = evaluate_patch_candidate(src, "")
    assert bundle["decision"] == DECISION_REJECTED_AUTHORITY_BYPASS


# --- per-fixture decisions --------------------------------------------------


def test_phase38_doc_only_patch_safe_to_review():
    assert _by_name()["READY_DOC_ONLY_PATCH"]["decision"] == DECISION_SAFE_TO_REVIEW


def test_phase38_test_only_patch_safe_or_human():
    assert _by_name()["READY_TEST_ONLY_PATCH"]["decision"] in (DECISION_SAFE_TO_REVIEW, DECISION_NEEDS_HUMAN_REVIEW)


def test_phase38_runtime_low_patch_needs_human_review():
    assert _by_name()["RUNTIME_LOW_PATCH"]["decision"] == DECISION_NEEDS_HUMAN_REVIEW


def test_phase38_authority_bypass_patch_rejected():
    assert _by_name()["AUTHORITY_BYPASS_PATCH"]["decision"] == DECISION_REJECTED_AUTHORITY_BYPASS


def test_phase38_live_effect_patch_rejected():
    assert _by_name()["LIVE_EFFECT_PATCH"]["decision"] == DECISION_REJECTED_LIVE_ACTION


def test_phase38_secret_leak_patch_rejected():
    assert _by_name()["SECRET_LEAK_PATCH"]["decision"] == DECISION_REJECTED_SECRET_RISK


def test_phase38_sandbox_escape_patch_rejected():
    assert _by_name()["SANDBOX_ESCAPE_PATCH"]["decision"] == DECISION_REJECTED_SANDBOX_ESCAPE


def test_phase38_all_fixtures_match_expected_decision():
    bundles = _by_name()
    for fixture in all_fixtures():
        assert bundles[fixture["name"]]["decision"] == fixture["expected_decision"], fixture["name"]


# --- hard boundary flags ----------------------------------------------------


def test_phase38_apply_allowed_always_false():
    for bundle in _by_name().values():
        assert bundle["decision_record"]["apply_allowed"] is False


def test_phase38_patch_applied_to_live_repo_always_false():
    for bundle in _by_name().values():
        assert bundle["decision_record"]["patch_applied_to_live_repo"] is False


def test_phase38_committed_always_false():
    for bundle in _by_name().values():
        assert bundle["decision_record"]["committed"] is False


def test_phase38_pushed_and_deployed_always_false():
    for bundle in _by_name().values():
        assert bundle["decision_record"]["pushed"] is False
        assert bundle["decision_record"]["deployed"] is False


def test_phase38_authority_granted_always_false():
    for bundle in _by_name().values():
        assert bundle["decision_record"]["authority_granted"] is False


def test_phase38_tools_authorized_always_false():
    for bundle in _by_name().values():
        assert bundle["decision_record"]["tools_authorized"] is False


def test_phase38_no_live_posts_created():
    for bundle in _by_name().values():
        assert bundle["decision_record"]["created_live_posts"] is False
        assert bundle["decision_record"]["created_external_side_effects"] is False


def test_phase38_decision_record_is_neutral_output():
    for bundle in _by_name().values():
        assert_neutral_output(bundle["decision_record"])  # must not raise


def test_phase38_assert_neutral_output_rejects_apply_allowed():
    with pytest.raises(SandboxError):
        assert_neutral_output({"apply_allowed": True})


# --- candidate representation & sandbox -------------------------------------


def test_phase38_patch_candidate_is_representation_only():
    bundle = _by_name()["READY_DOC_ONLY_PATCH"]
    assert bundle["candidate"]["is_representation_only"] is True


def test_phase38_candidate_hash_deterministic():
    assert candidate_hash("hello patch") == candidate_hash("hello patch")


def test_phase38_candidate_id_is_content_addressed():
    bundle = _by_name()["READY_DOC_ONLY_PATCH"]
    assert bundle["candidate"]["patch_candidate_id"].startswith("pc-")


def test_phase38_sandbox_plan_does_not_touch_live_tree():
    candidate = build_patch_candidate(source=_loaded_ready(), patch_text="", sandbox_mode=SANDBOX_ARTIFACT_ONLY)
    plan = sandbox_plan(candidate, [])
    assert plan["applies_to_live_tree"] is False
    assert plan["mutates_live_source_paths"] is False


def test_phase38_sandbox_receipt_attests_no_live_mutation():
    bundle = _by_name()["READY_DOC_ONLY_PATCH"]
    assert bundle["sandbox_receipt"]["applied_to_live_tree"] is False
    assert bundle["sandbox_receipt"]["live_source_mutated"] is False


def test_phase38_sandbox_rejects_unsupported_mode():
    candidate = build_patch_candidate(source=_loaded_ready(), patch_text="", sandbox_mode="LIVE_APPLY")
    with pytest.raises(SandboxError):
        sandbox_plan(candidate, [])


# --- parser / classifier ----------------------------------------------------


def test_phase38_diff_parser_reads_without_applying():
    parsed = parse_unified_diff(all_fixtures()[0]["patch_text"])
    assert parsed["parseable"] is True
    assert parsed["changed_paths"]


def test_phase38_unparseable_patch_rejected_unsupported():
    bundle = evaluate_patch_candidate(_ready_source(), "this is not a diff at all")
    assert bundle["decision"] in REJECTED_DECISIONS


def test_phase38_classify_doc_path_doc_only():
    assert classify_path("docs/notes/x.md") == RISK_DOC_ONLY


def test_phase38_classify_authority_path_authority_kernel():
    assert classify_path("hg_runtime/authority_kernel/grant.py") == RISK_AUTHORITY_KERNEL


def test_phase38_detect_sandbox_escape_traversal():
    assert "path_traversal" in detect_sandbox_escape("../outside/evil.py")


def test_phase38_secret_redacted_in_candidate():
    bundle = _by_name()["SECRET_LEAK_PATCH"]
    # No candidate is produced for a rejected secret patch, but the decision
    # record must never carry the raw secret.
    import json

    assert "sk-PHASE38FAKEKEY1234567" not in json.dumps(bundle["decision_record"], sort_keys=True)


# --- decision records -------------------------------------------------------


def test_phase38_decision_records_required_fields():
    for bundle in _by_name().values():
        record = bundle["decision_record"]
        for field in ("patch_candidate_id", "source_work_package_id", "source_work_package_hash", "candidate_status", "sandbox_mode"):
            assert record.get(field)
        assert record["decision_hash"].startswith("sha256:")


def test_phase38_rejected_decision_produces_no_candidate_artifact(tmp_path):
    bundle = _by_name()["AUTHORITY_BYPASS_PATCH"]
    assert bundle["decision"] in REJECTED_DECISIONS
    assert write_candidate_artifact(tmp_path, bundle) is None


def test_phase38_safe_candidate_writes_artifact(tmp_path):
    bundle = _by_name()["READY_DOC_ONLY_PATCH"]
    record = write_candidate_artifact(tmp_path, bundle)
    assert record is not None
    assert (tmp_path / "candidates" / bundle["candidate"]["patch_candidate_id"] / "patch.diff").is_file()


# --- replay -----------------------------------------------------------------


def test_phase38_replay_deterministic(tmp_path):
    log = PatchSandboxLog(tmp_path / "chain.jsonl")
    for bundle in _by_name().values():
        log.append("patch_candidate_decision_v1", bundle["decision_record"])
    assert log.replay()["ok"] is True


def test_phase38_replay_detects_tamper(tmp_path):
    path = tmp_path / "chain.jsonl"
    log = PatchSandboxLog(path)
    log.append("patch_candidate_decision_v1", {"a": 1})
    log.append("patch_candidate_decision_v1", {"a": 2})
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(lines[0] + "\n", encoding="utf-8")  # drop the second record's predecessor link
    tampered = PatchSandboxLog(tmp_path / "chain2.jsonl")
    tampered.path.write_text("\n".join(lines[::-1]) + "\n", encoding="utf-8")
    assert tampered.replay()["ok"] is False


def test_phase38_decision_hash_stable_across_runs():
    first = evaluate_patch_candidate(_ready_source("STABLE"), all_fixtures()[0]["patch_text"])
    second = evaluate_patch_candidate(_ready_source("STABLE"), all_fixtures()[0]["patch_text"])
    assert first["decision_record"]["decision_hash"] == second["decision_record"]["decision_hash"]


# --- gate -------------------------------------------------------------------


def _green_summary(**overrides):
    base = {
        "verdict": VERDICT_GREEN,
        "phase37_green": True,
        "phase35_green": True,
        "phase36_green": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "candidate_produced_count": 2,
        "doc_only_patch_safe_to_review": True,
        "runtime_patch_needs_human_review": True,
        "not_ready_source_rejected": True,
        "live_action_patch_rejected": True,
        "authority_bypass_patch_rejected": True,
        "secret_risk_patch_rejected": True,
        "sandbox_escape_patch_rejected": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "no_live_state_mutated": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    base.update(overrides)
    return base


def test_phase38_gate_green_when_all_pass():
    assert validate_phase38_gate(_green_summary())["ok"] is True


def test_phase38_gate_refuses_without_phase37_green():
    out = validate_phase38_gate(_green_summary(phase37_green=False))
    assert out["ok"] is False
    assert "phase38_gate_refuses_without_phase37_green" in out["failures"]


def test_phase38_gate_refuses_without_phase35_green():
    assert validate_phase38_gate(_green_summary(phase35_green=False))["ok"] is False


def test_phase38_gate_refuses_without_phase36_green():
    assert validate_phase38_gate(_green_summary(phase36_green=False))["ok"] is False


def test_phase38_gate_refuses_if_phase19_not_yellow():
    out = validate_phase38_gate(_green_summary(phase19_yellow_preserved=False))
    assert "phase19_yellow_not_preserved" in out["failures"]


def test_phase38_gate_refuses_if_patch_applied():
    out = validate_phase38_gate(_green_summary(patch_applied_to_live_repo=True))
    assert "patch_applied_to_live_repo" in out["failures"]


def test_phase38_gate_refuses_if_authority_granted():
    out = validate_phase38_gate(_green_summary(authority_granted=True))
    assert "authority_granted" in out["failures"]


def test_phase38_gate_refuses_without_coverage():
    assert validate_phase38_gate(_green_summary(sandbox_escape_patch_rejected=False))["ok"] is False


def test_phase38_gate_refuses_red_verdict():
    assert validate_phase38_gate(_green_summary(verdict=VERDICT_RED))["ok"] is False
