"""Shared proof gate runner for TLB Tool Lifecycle Boundary."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.proof.command_log import record_command


def git_head(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def run_tlb_feature_checks() -> dict[str, object]:
    from hg_core.tlb_cluster.config import (
        tlb_refuse_authority_conversion,
        tlb_refuse_live_model_invocation,
        tlb_static_fixtures_only,
    )
    from hg_core.tlb_cluster.events import planned_tlb_event_refs
    from hg_core.tlb_cluster.no_authority import check_tlb_import_fences
    from hg_core.tlb_cluster.rtc_design import validate_tlb_rtc_event_design
    from hg_runtime.tool_lifecycle_boundary import (
        FIXTURE_CLOCK,
        analyze_tlb_fixtures,
        load_tlb_fixtures,
        process_tlb_bundle,
        replay_fixture_stream,
    )

    checks: list[dict[str, object]] = []
    checks.append({"check_id": "static_fixtures_only_default", "ok": tlb_static_fixtures_only() and tlb_refuse_live_model_invocation(), "detail": "fixture/static slice enforced"})
    checks.append({"check_id": "refuse_authority_conversion_default", "ok": tlb_refuse_authority_conversion(), "detail": "authority conversion refusal enabled"})
    rtc_ok, rtc_failures = validate_tlb_rtc_event_design(planned_tlb_event_refs())
    checks.append({"check_id": "rtc_event_design", "ok": rtc_ok, "detail": rtc_failures if not rtc_ok else len(planned_tlb_event_refs())})
    fences_ok, fence_detail = check_tlb_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})
    analysis = analyze_tlb_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "fixture_bundles_analyzed", "ok": analysis.get("all_advisory") is True and analysis.get("no_authority_created") is True and int(analysis.get("bundle_count", 0)) >= 12, "detail": analysis.get("bundle_count")})
    bundles = load_tlb_fixtures()
    valid_bundle = next(b for b in bundles if b["bundle_id"] == "tlb-healthy-tool")
    valid_result = process_tlb_bundle(valid_bundle, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "valid_bundle_recorded", "ok": valid_result.get("status") == "recorded" and valid_result.get("permission_granted") is False, "detail": valid_result.get("status")})
    fail_bundle = next(b for b in bundles if b["bundle_id"] == "tlb-stale-input")
    fail_result = process_tlb_bundle(fail_bundle, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "fail_closed_path", "ok": fail_result.get("status") in ("fail_closed", "contained"), "detail": fail_result.get("reason_code")})
    receipt = valid_result.get("tlb_receipt")
    if isinstance(receipt, dict):
        checks.append({"check_id": "receipt_negative_proofs", "ok": receipt.get("permit_minted") is False and receipt.get("permission_granted") is False and receipt.get("authority_created") is False and receipt.get("deletion_performed") is False and receipt.get("tool_removed") is False and receipt.get("agent_spawned") is False, "detail": "negative proofs pinned false"})
    _, replay_hash = replay_fixture_stream(list(bundles[:5]), observed_at=FIXTURE_CLOCK)
    _, replay_hash_2 = replay_fixture_stream(list(bundles[:5]), observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "replay_determinism", "ok": replay_hash == replay_hash_2 and bool(replay_hash), "detail": replay_hash[:24]})

    adv_bundle = next(b for b in bundles if b["bundle_id"] == "tlb-usefulness-as-authority")
    adv_result = process_tlb_bundle(adv_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_tlb-usefulness-as-authority",
            "ok": adv_result.get("status") == "contained" and adv_result.get("permission_granted") is False,
            "detail": adv_result.get("reason_code"),
        }
    )

    adv_bundle = next(b for b in bundles if b["bundle_id"] == "tlb-tool-grant")
    adv_result = process_tlb_bundle(adv_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_tlb-tool-grant",
            "ok": adv_result.get("status") == "contained" and adv_result.get("permission_granted") is False,
            "detail": adv_result.get("reason_code"),
        }
    )

    adv_bundle = next(b for b in bundles if b["bundle_id"] == "tlb-tool-revoke")
    adv_result = process_tlb_bundle(adv_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_tlb-tool-revoke",
            "ok": adv_result.get("status") == "contained" and adv_result.get("permission_granted") is False,
            "detail": adv_result.get("reason_code"),
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_tlb_gate(workspace: Path, *, gate_id: str = "tlb_tool_lifecycle_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "metabolic_governance" / "TLB" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")
    feature_checks = run_tlb_feature_checks()
    (artifacts_dir / "tlb_feature_checks.json").write_text(json.dumps(feature_checks, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    test_targets = ["tests/tlb"]
    t0 = time.monotonic()
    test_cmd = subprocess.run([sys.executable, "-m", "pytest", *test_targets, "-q", "--timeout=180"], cwd=workspace, capture_output=True, text=True, check=False)
    record_command(command_log, argv=["pytest", *test_targets, "-q"], cwd=workspace, exit_code=test_cmd.returncode, duration_s=time.monotonic() - t0, stdout=test_cmd.stdout, stderr=test_cmd.stderr)
    gate_ok = feature_checks["ok"] and test_cmd.returncode == 0
    gate_result: dict[str, Any] = {"gate": gate_id, "ok": gate_ok, "verdicts": [{"check": "tlb_feature_checks", "verdict": "pass" if feature_checks["ok"] else "fail", "ok": feature_checks["ok"]}, {"check": "focused_unit_tests", "verdict": "pass" if test_cmd.returncode == 0 else "fail", "ok": test_cmd.returncode == 0}], "critical_failures": feature_checks.get("critical_failures", [])}
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2), encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"schema": "ct_proof_bundle_v1", "pack": "TLB", "gate": gate_id, "timestamp": ts, "head": git_head(workspace), "path_id": "metabolic_governance", "file_hashes": {"gate_result.json": sha256_file(proof_dir / "gate_result.json"), "artifacts/tlb_feature_checks.json": sha256_file(artifacts_dir / "tlb_feature_checks.json"), "command_log.jsonl": sha256_file(command_log)}}, indent=2), encoding="utf-8")
    if not gate_ok:
        print("TLB gate FAILED", file=sys.stderr)
        return 1
    print(f"TLB gate GREEN — proof bundle: {proof_dir}")
    return 0


__all__ = ["run_tlb_feature_checks", "run_tlb_gate"]

