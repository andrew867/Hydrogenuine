"""Shared proof gate runner for NIB Nutrient Intake Boundary."""

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


def run_nib_feature_checks() -> dict[str, object]:
    from hg_core.nib_cluster.config import (
        nib_refuse_authority_conversion,
        nib_refuse_live_model_invocation,
        nib_static_fixtures_only,
    )
    from hg_core.nib_cluster.events import planned_nib_event_refs
    from hg_core.nib_cluster.no_authority import check_nib_import_fences
    from hg_core.nib_cluster.rtc_design import validate_nib_rtc_event_design
    from hg_runtime.nutrient_intake_boundary import (
        FIXTURE_CLOCK,
        analyze_nib_fixtures,
        load_nib_fixtures,
        process_nib_bundle,
        replay_fixture_stream,
    )

    checks: list[dict[str, object]] = []
    checks.append({"check_id": "static_fixtures_only_default", "ok": nib_static_fixtures_only() and nib_refuse_live_model_invocation(), "detail": "fixture/static slice enforced"})
    checks.append({"check_id": "refuse_authority_conversion_default", "ok": nib_refuse_authority_conversion(), "detail": "authority conversion refusal enabled"})
    rtc_ok, rtc_failures = validate_nib_rtc_event_design(planned_nib_event_refs())
    checks.append({"check_id": "rtc_event_design", "ok": rtc_ok, "detail": rtc_failures if not rtc_ok else len(planned_nib_event_refs())})
    fences_ok, fence_detail = check_nib_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})
    analysis = analyze_nib_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "fixture_bundles_analyzed", "ok": analysis.get("all_advisory") is True and analysis.get("no_authority_created") is True and int(analysis.get("bundle_count", 0)) >= 12, "detail": analysis.get("bundle_count")})
    bundles = load_nib_fixtures()
    valid_bundle = next(b for b in bundles if b["bundle_id"] == "nib-valid-intake")
    valid_result = process_nib_bundle(valid_bundle, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "valid_bundle_recorded", "ok": valid_result.get("status") == "recorded" and valid_result.get("permission_granted") is False, "detail": valid_result.get("status")})
    fail_bundle = next(b for b in bundles if b["bundle_id"] == "nib-stale-input")
    fail_result = process_nib_bundle(fail_bundle, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "fail_closed_path", "ok": fail_result.get("status") in ("fail_closed", "contained"), "detail": fail_result.get("reason_code")})
    receipt = valid_result.get("nib_receipt")
    if isinstance(receipt, dict):
        checks.append({"check_id": "receipt_negative_proofs", "ok": receipt.get("permit_minted") is False and receipt.get("permission_granted") is False and receipt.get("authority_created") is False and receipt.get("deletion_performed") is False and receipt.get("tool_removed") is False and receipt.get("agent_spawned") is False, "detail": "negative proofs pinned false"})
    _, replay_hash = replay_fixture_stream(list(bundles[:5]), observed_at=FIXTURE_CLOCK)
    _, replay_hash_2 = replay_fixture_stream(list(bundles[:5]), observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "replay_determinism", "ok": replay_hash == replay_hash_2 and bool(replay_hash), "detail": replay_hash[:24]})

    adv_bundle = next(b for b in bundles if b["bundle_id"] == "nib-intake-as-truth")
    adv_result = process_nib_bundle(adv_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_nib-intake-as-truth",
            "ok": adv_result.get("status") == "contained" and adv_result.get("permission_granted") is False,
            "detail": adv_result.get("reason_code"),
        }
    )

    adv_bundle = next(b for b in bundles if b["bundle_id"] == "nib-memory-write")
    adv_result = process_nib_bundle(adv_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_nib-memory-write",
            "ok": adv_result.get("status") == "contained" and adv_result.get("permission_granted") is False,
            "detail": adv_result.get("reason_code"),
        }
    )

    adv_bundle = next(b for b in bundles if b["bundle_id"] == "nib-tool-install")
    adv_result = process_nib_bundle(adv_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_nib-tool-install",
            "ok": adv_result.get("status") == "contained" and adv_result.get("permission_granted") is False,
            "detail": adv_result.get("reason_code"),
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_nib_gate(workspace: Path, *, gate_id: str = "nib_nutrient_intake_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "metabolic_governance" / "NIB" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")
    feature_checks = run_nib_feature_checks()
    (artifacts_dir / "nib_feature_checks.json").write_text(json.dumps(feature_checks, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    test_targets = ["tests/nib"]
    t0 = time.monotonic()
    test_cmd = subprocess.run([sys.executable, "-m", "pytest", *test_targets, "-q", "--timeout=180"], cwd=workspace, capture_output=True, text=True, check=False)
    record_command(command_log, argv=["pytest", *test_targets, "-q"], cwd=workspace, exit_code=test_cmd.returncode, duration_s=time.monotonic() - t0, stdout=test_cmd.stdout, stderr=test_cmd.stderr)
    gate_ok = feature_checks["ok"] and test_cmd.returncode == 0
    gate_result: dict[str, Any] = {"gate": gate_id, "ok": gate_ok, "verdicts": [{"check": "nib_feature_checks", "verdict": "pass" if feature_checks["ok"] else "fail", "ok": feature_checks["ok"]}, {"check": "focused_unit_tests", "verdict": "pass" if test_cmd.returncode == 0 else "fail", "ok": test_cmd.returncode == 0}], "critical_failures": feature_checks.get("critical_failures", [])}
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2), encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"schema": "ct_proof_bundle_v1", "pack": "NIB", "gate": gate_id, "timestamp": ts, "head": git_head(workspace), "path_id": "metabolic_governance", "file_hashes": {"gate_result.json": sha256_file(proof_dir / "gate_result.json"), "artifacts/nib_feature_checks.json": sha256_file(artifacts_dir / "nib_feature_checks.json"), "command_log.jsonl": sha256_file(command_log)}}, indent=2), encoding="utf-8")
    if not gate_ok:
        print("NIB gate FAILED", file=sys.stderr)
        return 1
    print(f"NIB gate GREEN — proof bundle: {proof_dir}")
    return 0


__all__ = ["run_nib_feature_checks", "run_nib_gate"]

