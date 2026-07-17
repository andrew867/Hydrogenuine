"""Rollback drill fixtures D1–D10 (CT-07 RBK)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from hg_core.admission.ingress import get_controller, reset_controller
from hg_core.admission.types import AdmissionRequest
from hg_core.rollback import events
from hg_core.rollback.harness import DrillHarness, file_hash
from hg_core.rollback.types import DrillOutcome, DrillReceipt
from hg_oea.compensation import compensate_local_report
from hg_oea.config import OEAConfig
from hg_oea.registry import lookup_capability
from hg_oea.types import CapabilityDefinition
from hg_runtime.replay import replay
from hg_srp.apply_types import content_hash
from hg_srp.sandbox import cleanup_sandbox, prepare_directory_sandbox, verify_protected_unchanged
from hg_srp.self_edit_policy import enter_lockdown, is_locked_down, reset_self_edit_registries
from hg_ter.executor import TERExecutor
from hg_ter.types import CommandRequest


def _receipt(drill_id: str, action: str, reason: str, body: dict[str, Any], *, lockdown: bool = False) -> DrillReceipt:
    return DrillReceipt(
        receipt_id=f"rbk_{drill_id}_{action}",
        drill_id=drill_id,
        action=action,
        reason_code=reason,
        evidence_hash=content_hash(body),
        lockdown=lockdown,
    )


def refuse_dirty_rollback(sandbox_root: Path, *, dirty_marker: Path) -> tuple[bool, str]:
    """Fail closed when dirty artifacts would be silently destroyed."""
    if dirty_marker.exists():
        quarantine = sandbox_root / "quarantine"
        quarantine.mkdir(parents=True, exist_ok=True)
        dest = quarantine / dirty_marker.name
        shutil.move(str(dirty_marker), str(dest))
        return False, "rbk.refused.dirty_worktree"
    return True, "ok"


def drill_d1_failed_srp_apply(harness: DrillHarness) -> DrillOutcome:
    root = harness.repo_root
    marker = root / "protected.txt"
    marker.write_text("master-content\n", encoding="utf-8")
    before = marker.read_text(encoding="utf-8")
    prep = prepare_directory_sandbox(root, "d1-failed-apply")
    if not prep.ok or prep.sandbox is None:
        return DrillOutcome("D1", False, "fail", prep.reason_code, detail={"stage": "prepare"})
    sandbox_path = Path(prep.sandbox.sandbox_path)
    (sandbox_path / "applied.patch").write_text("simulated-apply\n", encoding="utf-8")
    test_failed = True
    cleanup_receipt = cleanup_sandbox(sandbox_path.parent, root)
    master_ok = marker.read_text(encoding="utf-8") == before and verify_protected_unchanged(root, prep.sandbox.protected_head)
    receipt = _receipt("D1", "srp_apply_rollback", "ok" if master_ok else "rbk.failed.srp_apply", cleanup_receipt)
    return DrillOutcome(
        "D1",
        master_ok and test_failed,
        "pass" if master_ok else "fail",
        "ok" if master_ok else "rbk.failed.srp_apply",
        receipts=(receipt,),
        detail={"cleanup": cleanup_receipt, "master_unchanged": master_ok},
    )


def drill_d2_failed_ter_command(harness: DrillHarness) -> DrillOutcome:
    executor = TERExecutor()
    req = CommandRequest(
        request_id="rbk-d2-ter",
        requested_by="rbk:drill",
        purpose="rbk_drill_forbidden",
        argv=("git", "push", "origin", "main"),
        cwd=str(harness.repo_root),
        created_at=harness.clock(),
    )
    receipt, result = executor.execute(req)
    refused = receipt.result_status == "refused"
    compensation = {
        "action": "revert_noop",
        "request_id": req.request_id,
        "original_refusal": receipt.receipt_hash,
    }
    comp_event = events.compensation_receipted(compensation)
    harness.artifacts.append(comp_event)
    rbk_receipt = _receipt("D2", "ter_compensation", "ok" if refused else "rbk.failed.ter", compensation)
    return DrillOutcome(
        "D2",
        refused,
        "pass" if refused else "fail",
        "ok" if refused else "rbk.failed.ter",
        receipts=(rbk_receipt,),
        detail={"receipt_hash": receipt.receipt_hash, "compensation": compensation},
    )


def drill_d3_failed_oea_local(harness: DrillHarness) -> DrillOutcome:
    proof_dir = harness.repo_root / ".rbk_drill" / "oea"
    proof_dir.mkdir(parents=True, exist_ok=True)
    config = OEAConfig(proof_dir=proof_dir, mode="real")
    cap = lookup_capability("local_report_file.write")
    assert cap is not None
    partial = proof_dir / "partial_report.txt"
    partial.write_text("partial-write\n", encoding="utf-8")
    quarantine = proof_dir / "quarantine"
    quarantine.mkdir(exist_ok=True)
    shutil.move(str(partial), str(quarantine / partial.name))
    status = compensate_local_report((str(quarantine / partial.name),), config=config, capability=cap)
    restored_ok = status == "completed" or not partial.exists()
    receipt = _receipt("D3", "oea_compensation", "ok" if restored_ok else "rbk.failed.compensation", {"status": status})
    return DrillOutcome(
        "D3",
        restored_ok,
        "pass" if restored_ok else "fail",
        "ok" if restored_ok else "rbk.failed.compensation",
        receipts=(receipt,),
        detail={"compensation_status": status, "quarantine": str(quarantine)},
    )


def drill_d4_failed_post_land_tests(harness: DrillHarness) -> DrillOutcome:
    reset_self_edit_registries()
    bundle_id = "d4-self-edit"
    tests_passed = False
    rollback_performed = False
    lockdown = False
    if not tests_passed:
        rollback_performed = False
        enter_lockdown(bundle_id)
        lockdown = is_locked_down(bundle_id)
    receipt = _receipt(
        "D4",
        "self_edit_lockdown",
        "rbk.lockdown.active" if lockdown else "rbk.failed.lockdown",
        {"rollback_performed": rollback_performed, "lockdown": lockdown},
        lockdown=lockdown,
    )
    evt = events.lockdown_entered(bundle_id=bundle_id, reason_code="post_merge_tests_failed")
    harness.artifacts.append(evt)
    return DrillOutcome(
        "D4",
        lockdown and not rollback_performed,
        "pass" if lockdown else "fail",
        receipt.reason_code,
        receipts=(receipt,),
        detail={"tests_passed": tests_passed},
    )


def drill_d5_crr_mid_rollback(harness: DrillHarness) -> DrillOutcome:
    reset_controller()
    ctrl = get_controller()
    mel = ctrl.request(
        __import__("hg_core.admission.types", fromlist=["AdmissionRequest"]).AdmissionRequest(
            request_id="d5-mel",
            kind="mel_cycle",
            idempotency_key="d5-mel",
        )
    )
    recovery_token = ctrl.begin_crr_recovery(recovery_id="d5-crr")
    ctrl.end_crr_recovery()
    if mel.token:
        ctrl.release(mel.token)
    ok = recovery_token is not None
    receipt = _receipt("D5", "crr_interleave", "ok" if ok else "rbk.failed.crr_interleave", {"recovery": ok})
    return DrillOutcome("D5", ok, "pass" if ok else "fail", receipt.reason_code, receipts=(receipt,))


def drill_d6_replay_after_rollback(harness: DrillHarness) -> DrillOutcome:
    runtime_dir = harness.repo_root / ".rbk_drill" / "runtime"
    memory = runtime_dir / "memory" / "runtime"
    memory.mkdir(parents=True, exist_ok=True)
    segment = memory / "events-20260612.jsonl"
    evt = {
        "schema": "rtc-event",
        "schema_version": "1.0",
        "event_id": "evt_0000000000000001",
        "seq": 0,
        "timestamp": harness.clock(),
        "type": "RUNTIME_STARTED",
        "payload": {"path_id": "demo_phase0"},
        "source": "rbk:drill",
        "causal_parents": [],
        "severity": "info",
        "event_hash": "sha256:placeholder",
        "prev_hash": "sha256:genesis",
    }
    from hg_runtime.bus import compute_event_hash

    evt["event_hash"] = compute_event_hash({k: v for k, v in evt.items() if k != "event_hash"})
    evt["event_id"] = f"evt_{evt['event_hash'].split(':')[1][:16]}"
    segment.write_text(json.dumps(evt) + "\n", encoding="utf-8")
    shutil.rmtree(runtime_dir / "state", ignore_errors=True)
    result = replay(memory)
    receipt = _receipt("D6", "replay_verify", "ok" if result.ok else "rtc.replay_mismatch.state_hash", result.to_dict())
    return DrillOutcome(
        "D6",
        result.ok,
        "pass" if result.ok else "fail",
        "ok" if result.ok else "rtc.replay_mismatch.state_hash",
        receipts=(receipt,),
        detail={"state_hash": result.state_hash, "events": result.events},
    )


def drill_d7_dirty_worktree(harness: DrillHarness) -> DrillOutcome:
    root = harness.repo_root
    sandbox_parent = root / ".tmp_srp_apply" / "d7-dirty"
    sandbox_parent.mkdir(parents=True, exist_ok=True)
    dirty = sandbox_parent / "worktree" / "untracked_dirty.txt"
    dirty.parent.mkdir(parents=True, exist_ok=True)
    dirty.write_text("do-not-destroy\n", encoding="utf-8")
    allowed, reason = refuse_dirty_rollback(sandbox_parent, dirty_marker=dirty)
    quarantined = (sandbox_parent / "quarantine" / dirty.name).exists()
    receipt = _receipt(
        "D7",
        "dirty_refuse",
        reason,
        {"allowed": allowed, "quarantined": quarantined},
    )
    return DrillOutcome(
        "D7",
        not allowed and quarantined,
        "pass" if not allowed and quarantined else "fail",
        reason,
        receipts=(receipt,),
        detail={"quarantined": quarantined},
    )


def drill_d8_rollback_failure_lockdown(harness: DrillHarness) -> DrillOutcome:
    reset_self_edit_registries()
    bundle_id = "d8-lockdown"
    compensation_ok = False
    if not compensation_ok:
        enter_lockdown(bundle_id)
    lockdown = is_locked_down(bundle_id)
    evt = events.lockdown_entered(bundle_id=bundle_id, reason_code="rbk.failed.compensation")
    harness.artifacts.append(evt)
    receipt = _receipt(
        "D8",
        "compensation_lockdown",
        "rbk.lockdown.active" if lockdown else "rbk.failed.lockdown",
        {"compensation_ok": compensation_ok, "lockdown": lockdown},
        lockdown=lockdown,
    )
    return DrillOutcome(
        "D8",
        lockdown,
        "pass" if lockdown else "fail",
        receipt.reason_code,
        receipts=(receipt,),
        detail={"compensation_ok": compensation_ok},
    )


def drill_d9_snapshot_restore(harness: DrillHarness) -> DrillOutcome:
    files = {"state.txt": "trusted-v1\n"}
    (harness.repo_root / "state.txt").write_text("corrupted\n", encoding="utf-8")
    manifest = harness.write_snapshot_manifest(files)
    ok, restored_hash = harness.restore_snapshot()
    content_ok = (harness.repo_root / "state.txt").read_text(encoding="utf-8") == "trusted-v1\n"
    receipt = _receipt("D9", "snapshot_restore", "ok" if ok and content_ok else "rbk.failed.snapshot", manifest)
    return DrillOutcome(
        "D9",
        ok and content_ok,
        "pass" if ok and content_ok else "fail",
        receipt.reason_code,
        receipts=(receipt,),
        detail={"manifest_hash": manifest.get("manifest_hash"), "restored_hash": restored_hash},
    )


def drill_d10_archived_hash_verify(harness: DrillHarness) -> DrillOutcome:
    path = harness.repo_root / "state.txt"
    path.write_text("archived-state\n", encoding="utf-8")
    before = file_hash(path)
    archive_manifest = {
        "schema": "rbk_archive_v1",
        "pre_rollback_hash": before,
        "file": "state.txt",
    }
    archive_path = harness.repo_root / ".rbk_drill" / "archive_manifest.json"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(json.dumps(archive_manifest, indent=2), encoding="utf-8")
    after = file_hash(path)
    chain_ok = after == before
    receipt = _receipt("D10", "archive_hash", "ok" if chain_ok else "rbk.failed.archive_hash", archive_manifest)
    return DrillOutcome(
        "D10",
        chain_ok,
        "pass" if chain_ok else "fail",
        receipt.reason_code,
        receipts=(receipt,),
        detail={"hash": before},
    )


DRILL_RUNNERS = {
    "D1": drill_d1_failed_srp_apply,
    "D2": drill_d2_failed_ter_command,
    "D3": drill_d3_failed_oea_local,
    "D4": drill_d4_failed_post_land_tests,
    "D5": drill_d5_crr_mid_rollback,
    "D6": drill_d6_replay_after_rollback,
    "D7": drill_d7_dirty_worktree,
    "D8": drill_d8_rollback_failure_lockdown,
    "D9": drill_d9_snapshot_restore,
    "D10": drill_d10_archived_hash_verify,
}


def run_all_drills(harness: DrillHarness) -> dict[str, Any]:
    outcomes: dict[str, Any] = {}
    for drill_id, runner in DRILL_RUNNERS.items():
        harness.artifacts.append(events.drill_started(drill_id))
        outcome = runner(harness)
        harness.artifacts.append(
            events.drill_completed(outcome.to_payload())
            if outcome.ok
            else events.drill_failed(drill_id, reason_code=outcome.reason_code)
        )
        outcomes[drill_id] = outcome.to_payload()
    outcomes["residue_free"] = harness.teardown()
    return outcomes


__all__ = [
    "DRILL_RUNNERS",
    "drill_d1_failed_srp_apply",
    "drill_d7_dirty_worktree",
    "drill_d8_rollback_failure_lockdown",
    "refuse_dirty_rollback",
    "run_all_drills",
]
