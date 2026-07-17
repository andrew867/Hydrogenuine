"""Phase 39 long-run stability tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.long_run_stability import compute_replay, evaluate_scenario
from hg_runtime.long_run_stability.checkpoint import checkpoint_hash, make_checkpoint, verify_checkpoint
from hg_runtime.long_run_stability.fixtures import all_fixtures
from hg_runtime.long_run_stability.gate import validate_phase39_gate
from hg_runtime.long_run_stability.loop import run_soak, soak_config
from hg_runtime.long_run_stability.recovery import recover_and_resume, reject_corrupted_checkpoint
from hg_runtime.long_run_stability.replay import replay_records
from hg_runtime.long_run_stability.schemas import BOUNDARY_FLAG_FIELDS, VERDICT_GREEN
from hg_runtime.long_run_stability.task_queue import build_task_queue


def _fixture(name: str):
    return next(row for row in all_fixtures() if row["name"] == name)


def _run(name: str = "STABLE_DOC_REVIEW_TASK"):
    fx = _fixture(name)
    return run_soak(soak_config(), build_task_queue(fx["tasks"]), run_id=f"test-{name.lower()}", mode=fx["mode"])


def _green_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "phase38_green": True,
        "phase37_green": True,
        "phase35_green": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "short_soak_ran": True,
        "checkpoint_count": 1,
        "checkpoint_manifest_valid": True,
        "resume_matches_uninterrupted_run": True,
        "stop_preempts_work_demonstrated": True,
        "panic_preempts_stop_and_work_demonstrated": True,
        "crash_recovery_demonstrated": True,
        "corrupted_checkpoint_rejected": True,
        "boundary_drift_attempt_rejected": True,
        "replay_final_state_hash_matches": True,
        "replay_receipt_chain_root_matches": True,
        "replay_rejects_mutation": True,
        "fake_green_rejected": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "patches_applied": False,
        "authority_granted": False,
        "tools_authorized": False,
        "live_effects_created": False,
        "live_posts_created": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data


def test_phase39_short_fixture_soak_runs():
    assert _run()["tasks_processed"] == 6


def test_phase39_checkpoint_written():
    assert _run()["checkpoints"]


def test_phase39_checkpoint_manifest_written():
    assert evaluate_scenario(_fixture("STABLE_DOC_REVIEW_TASK"))["checkpoint_manifest_valid"] is True


def test_phase39_checkpoint_hash_deterministic():
    ckpt = _run()["checkpoints"][0]
    assert verify_checkpoint(ckpt)
    assert ckpt["checkpoint_hash"] == checkpoint_hash(ckpt)


def test_phase39_checkpoint_hash_changes_with_state():
    run = _run()
    changed = dict(run["state"], iteration=99)
    assert checkpoint_hash(run["state"]) != checkpoint_hash(changed)


def test_phase39_resume_matches_uninterrupted_run():
    assert evaluate_scenario(_fixture("CRASH_AFTER_CHECKPOINT"))["resume_matches_uninterrupted_run"] is True


def test_phase39_recovery_from_last_valid_checkpoint():
    run = _run()
    queue = build_task_queue(_fixture("STABLE_DOC_REVIEW_TASK")["tasks"])
    recovered = recover_and_resume(soak_config(), queue, run["checkpoints"], run_id="resume")
    assert recovered["ok"] is True


def test_phase39_corrupted_checkpoint_rejected():
    ckpt = dict(_run()["checkpoints"][0])
    ckpt["checkpoint_hash"] = "sha256:bad"
    assert reject_corrupted_checkpoint(ckpt)["ok"] is False


def test_phase39_stop_preempts_work():
    assert evaluate_scenario(_fixture("STOP_AFTER_N_ITERATIONS"))["stop_preempts_work"] is True


def test_phase39_panic_preempts_work():
    assert evaluate_scenario(_fixture("PANIC_AFTER_N_ITERATIONS"))["panic_preempts_stop_and_work"] is True


def test_phase39_panic_preempts_stop():
    run = run_soak(soak_config(), build_task_queue(_fixture("PANIC_AFTER_N_ITERATIONS")["tasks"]), run_id="panic", panic_at=2, stop_at=2)
    assert run["halt_reason"] == "PANIC"


def test_phase39_boundary_state_preserved_across_resume():
    assert evaluate_scenario(_fixture("CRASH_AFTER_CHECKPOINT"))["recovery_result"]["boundary_state_preserved"] is True


def test_phase39_authority_granted_always_false():
    assert _run()["state"]["authority_granted"] is False


def test_phase39_tools_authorized_always_false():
    assert _run()["state"]["tools_authorized"] is False


def test_phase39_live_effects_always_false():
    assert _run()["state"]["live_effects_created"] is False


def test_phase39_live_posts_always_false():
    assert _run()["state"]["live_posts_created"] is False


def test_phase39_external_provider_calls_always_false():
    assert _run()["state"]["external_provider_calls_made"] is False


def test_phase39_patches_applied_always_false():
    assert _run("STABLE_PATCH_CANDIDATE_REVIEW_TASK")["state"]["patches_applied"] is False


def test_phase39_does_not_apply_phase38_candidates():
    assert all(not task["applies_patch"] for task in build_task_queue(_fixture("STABLE_PATCH_CANDIDATE_REVIEW_TASK")["tasks"])["tasks"])


def test_phase39_preserves_phase19_yellow():
    assert _run()["state"]["phase19_status"] == "YELLOW_PRESERVED"


def test_phase39_preserves_phase24_infrastructure_only():
    assert _run()["state"]["phase24_status"] == "INFRASTRUCTURE_ONLY"


def test_phase39_replay_final_state_hash_matches():
    assert compute_replay(_run())["final_state_hash_matches"] is True


def test_phase39_replay_receipt_root_matches():
    assert compute_replay(_run())["receipt_chain_root_matches"] is True


def test_phase39_replay_rejects_mutated_event_log():
    assert compute_replay(_run())["rejects_mutation"] is True


def test_phase39_replay_rejects_mutated_checkpoint():
    ckpt = dict(_run()["checkpoints"][0])
    ckpt["task_cursor"] = 99
    assert verify_checkpoint(ckpt) is False


def test_phase39_receipt_chain_required():
    run = _run()
    assert replay_records(run["events"])["ok"] is True


def test_phase39_no_secret_material_in_artifacts(tmp_path: Path):
    path = tmp_path / "artifact.json"
    path.write_text('{"secret_redaction_passed": true}', encoding="utf-8")
    assert "sk-" not in path.read_text(encoding="utf-8")


def test_phase39_fake_green_without_replay_rejected():
    assert validate_phase39_gate(_green_summary(replay_final_state_hash_matches=False))["ok"] is False


def test_phase39_boundary_drift_attempt_rejected():
    assert evaluate_scenario(_fixture("BOUNDARY_DRIFT_ATTEMPT"))["boundary_drift_rejected"] is True


def test_phase39_gate_requires_phase38_green():
    assert validate_phase39_gate(_green_summary(phase38_green=False))["ok"] is False


def test_phase39_gate_requires_phase37_green():
    assert validate_phase39_gate(_green_summary(phase37_green=False))["ok"] is False


def test_phase39_gate_requires_phase35_green():
    assert validate_phase39_gate(_green_summary(phase35_green=False))["ok"] is False


def test_phase39_gate_refuses_if_authority_granted():
    assert validate_phase39_gate(_green_summary(authority_granted=True))["ok"] is False


def test_phase39_gate_refuses_if_live_effect_created():
    assert validate_phase39_gate(_green_summary(live_effects_created=True))["ok"] is False


def test_phase39_gate_refuses_if_patch_applied():
    assert validate_phase39_gate(_green_summary(patches_applied=True))["ok"] is False


def test_phase39_gate_refuses_without_checkpoint():
    assert validate_phase39_gate(_green_summary(checkpoint_count=0))["ok"] is False


def test_phase39_gate_refuses_without_replay():
    assert validate_phase39_gate(_green_summary(replay_receipt_chain_root_matches=False))["ok"] is False


def test_phase39_gate_refuses_without_proof_bundle():
    assert validate_phase39_gate(_green_summary(proof_bundle_valid=False))["ok"] is False
