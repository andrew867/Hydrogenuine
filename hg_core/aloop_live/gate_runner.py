"""Shared proof gate runner for ALOOP-LIVE governed autonomous loop supervisor."""

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


def run_aloop_feature_checks() -> dict[str, object]:
    from hg_core.aloop_live.config import (
        aloop_fake_sink_only,
        aloop_refuse_authority_conversion,
        aloop_refuse_live_loop_start,
        aloop_refuse_self_renewal,
    )
    from hg_core.aloop_live.no_authority import check_aloop_import_fences
    from hg_core.iam.registry import clear_registry_cache, load_registry
    from hg_runtime.live_autonomous_loop import (
        FIXTURE_CLOCK,
        analyze_aloop_fixtures,
        load_aloop_fixtures,
        process_aloop_bundle,
        replay_fixture_stream,
        run_autonomous_loop_fixture,
    )

    clear_registry_cache()
    load_registry()
    checks: list[dict[str, object]] = []
    checks.append(
        {
            "check_id": "fake_sink_only_default",
            "ok": aloop_fake_sink_only() and aloop_refuse_live_loop_start() and aloop_refuse_self_renewal(),
            "detail": "fake-sink slice enforced",
        }
    )
    checks.append(
        {
            "check_id": "refuse_authority_conversion_default",
            "ok": aloop_refuse_authority_conversion(),
            "detail": "authority conversion refusal enabled",
        }
    )
    fences_ok, fence_detail = check_aloop_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})

    analysis = analyze_aloop_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True
            and analysis.get("no_authority_created") is True
            and analysis.get("no_live_loop") is True
            and analysis.get("no_self_renewal") is True
            and int(analysis.get("bundle_count", 0)) >= 16,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_aloop_fixtures()
    valid_bundle = next(b for b in bundles if b["bundle_id"] == "aloop-valid-supervise")
    valid_result = process_aloop_bundle(valid_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "valid_supervise_recorded",
            "ok": valid_result.get("status") == "recorded"
            and valid_result.get("permission_granted") is False
            and valid_result.get("live_loop_started") is False
            and valid_result.get("loop_self_renewed") is False,
            "detail": valid_result.get("reason_code"),
        }
    )

    for bundle_id in (
        "aloop-missing-operator-approval",
        "aloop-stale-approval",
        "aloop-missing-iam",
        "aloop-missing-tim",
        "aloop-lease-expired",
        "aloop-heartbeat-stale",
        "aloop-budget-exceeded",
        "aloop-kill-switch",
        "aloop-panic-lockdown",
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_aloop_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"deny_{bundle_id}",
                "ok": result.get("status") in ("refused", "contained") and result.get("live_loop_started") is False,
                "detail": result.get("reason_code"),
            }
        )

    receipt = valid_result.get("receipt")
    if isinstance(receipt, dict):
        checks.append(
            {
                "check_id": "receipt_negative_proofs",
                "ok": receipt.get("permission_granted") is False
                and receipt.get("authority_created") is False
                and receipt.get("live_loop_started") is False,
                "detail": "negative proofs pinned false",
            }
        )
        checks.append(
            {
                "check_id": "tep_wrapped_output",
                "ok": isinstance(valid_result.get("tep_wrapped"), dict),
                "detail": "tep envelope attached",
            }
        )

    pause_bundle = next(b for b in bundles if b["bundle_id"] == "aloop-pause-requested")
    pause_result = process_aloop_bundle(pause_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "pause_recorded_no_live_loop",
            "ok": pause_result.get("status") == "recorded"
            and isinstance(pause_result.get("pause_result"), dict)
            and pause_result.get("live_loop_started") is False,
            "detail": pause_result.get("reason_code"),
        }
    )

    rollback_bundle = next(b for b in bundles if b["bundle_id"] == "aloop-valid-rollback")
    rollback_result = process_aloop_bundle(rollback_bundle, observed_at=FIXTURE_CLOCK)
    rb = rollback_result.get("rollback_result")
    checks.append(
        {
            "check_id": "rollback_record_present",
            "ok": isinstance(rb, dict) and rb.get("rollback_acknowledged") is True,
            "detail": rb.get("reason_code") if isinstance(rb, dict) else None,
        }
    )

    _, replay_hash = replay_fixture_stream(list(bundles[:8]), observed_at=FIXTURE_CLOCK)
    _, replay_hash_2 = replay_fixture_stream(list(bundles[:8]), observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "replay_determinism",
            "ok": replay_hash == replay_hash_2 and bool(replay_hash),
            "detail": replay_hash[:24] if replay_hash else "",
        }
    )

    adapter = run_autonomous_loop_fixture(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "loop_adapter_fixture",
            "ok": adapter.get("live_loop_started") is False and adapter.get("permission_granted") is False,
            "detail": adapter.get("reason_code"),
        }
    )

    for bundle_id, expected_status in (
        ("aloop-authority-conversion", "contained"),
        ("aloop-self-renewal", "contained"),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_aloop_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"adversarial_{bundle_id}",
                "ok": result.get("status") == expected_status and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    secret_bundle = next(b for b in bundles if b["bundle_id"] == "aloop-secret-leak")
    secret_result = process_aloop_bundle(secret_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_aloop-secret-leak",
            "ok": secret_result.get("status") in ("refused", "contained") and secret_result.get("permission_granted") is False,
            "detail": secret_result.get("reason_code"),
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_aloop_gate(workspace: Path, *, gate_id: str = "long_running_autonomous_loop_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "live_autonomous_loop" / "ALOOP-LIVE" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_aloop_feature_checks()
    (artifacts_dir / "aloop_feature_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = ["tests/aloop_live"]
    t0 = time.monotonic()
    test_cmd = subprocess.run(
        [sys.executable, "-m", "pytest", *test_targets, "-q", "--timeout=180"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    record_command(
        command_log,
        argv=["pytest", *test_targets, "-q"],
        cwd=workspace,
        exit_code=test_cmd.returncode,
        duration_s=time.monotonic() - t0,
        stdout=test_cmd.stdout,
        stderr=test_cmd.stderr,
    )

    gate_ok = feature_checks["ok"] and test_cmd.returncode == 0
    gate_result: dict[str, Any] = {
        "gate": gate_id,
        "ok": gate_ok,
        "verdicts": [
            {
                "check": "aloop_feature_checks",
                "verdict": "pass" if feature_checks["ok"] else "fail",
                "ok": feature_checks["ok"],
                "detail": feature_checks,
            },
            {
                "check": "focused_unit_tests",
                "verdict": "pass" if test_cmd.returncode == 0 else "fail",
                "ok": test_cmd.returncode == 0,
            },
        ],
        "critical_failures": feature_checks.get("critical_failures", []),
        "proof_dir": str(proof_dir),
    }
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2), encoding="utf-8")
    (proof_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "ct_proof_bundle_v1",
                "pack": "ALOOP-LIVE",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "live_autonomous_loop/ALOOP-LIVE",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/aloop_feature_checks.json": sha256_file(artifacts_dir / "aloop_feature_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# ALOOP-LIVE Governed Autonomous Loop Supervisor — {ts}",
        "",
        f"**Verdict:** {'GREEN' if gate_ok else 'RED'}",
        f"**HEAD:** `{git_head(workspace)}`",
        "",
        "## Checks",
    ]
    for check in feature_checks.get("checks", []):
        status_lines.append(
            f"- {check['check_id']}: {'pass' if check['ok'] else 'fail'} — {check['detail']}"
        )
    (proof_dir / "status.md").write_text("\n".join(status_lines) + "\n", encoding="utf-8")

    print(json.dumps(gate_result, indent=2))
    return 0 if gate_ok else 1


__all__ = ["run_aloop_feature_checks", "run_aloop_gate"]
