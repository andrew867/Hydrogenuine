"""Shared proof gate runner for SRP-LIVE governed SRP apply."""

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


def run_srp_feature_checks() -> dict[str, object]:
    from hg_core.iam.registry import clear_registry_cache, load_registry
    from hg_core.srp_live.config import (
        srp_fake_sink_only,
        srp_refuse_authority_conversion,
        srp_refuse_self_modification,
        srp_restrict_only_default,
    )
    from hg_core.srp_live.no_authority import check_srp_import_fences
    from hg_core.srp_live.errors import (
        REJECT_BAC_LAUNDERING,
        REJECT_DIGEST_MISMATCH,
        REJECT_EXPIRED_OR_REVOKED,
        REJECT_LIVENESS_DEGRADED,
        REJECT_NAKED_PATCH,
        REJECT_NO_ADMISSION,
        REJECT_NO_PERMIT,
        REJECT_NO_ROLLBACK,
        REJECT_PANIC_LOCKDOWN,
        REJECT_STALE_SANDBOX_PROOF,
        REJECT_UNSIGNED_APPROVAL,
        ROUTE_TO_CHANGE_CONTROL,
    )
    from hg_runtime.live_srp_apply import (
        FIXTURE_CLOCK,
        analyze_srp_fixtures,
        load_srp_fixtures,
        process_srp_bundle,
        replay_fixture_stream,
        run_srp_apply_fixture,
    )

    clear_registry_cache()
    load_registry()
    checks: list[dict[str, object]] = []
    checks.append(
        {
            "check_id": "restrict_only_default",
            "ok": srp_restrict_only_default() and srp_fake_sink_only(),
            "detail": "restrict-only fake-sink slice enforced",
        }
    )
    checks.append(
        {
            "check_id": "refuse_authority_conversion_default",
            "ok": srp_refuse_authority_conversion() and srp_refuse_self_modification(),
            "detail": "authority conversion and self-modification refusal enabled",
        }
    )
    fences_ok, fence_detail = check_srp_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})

    analysis = analyze_srp_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True
            and analysis.get("no_authority_created") is True
            and analysis.get("no_live_landing") is True
            and int(analysis.get("bundle_count", 0)) >= 18,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_srp_fixtures()
    valid_bundle = next(b for b in bundles if b["bundle_id"] == "srp-valid-apply")
    valid_result = process_srp_bundle(valid_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "valid_apply_recorded",
            "ok": valid_result.get("status") == "recorded"
            and valid_result.get("apply_performed") is True
            and valid_result.get("permission_granted") is False
            and valid_result.get("live_landing_performed") is False,
            "detail": valid_result.get("reason_code"),
        }
    )

    plan_result = valid_result.get("plan_result")
    checks.append(
        {
            "check_id": "plan_apply_separation",
            "ok": isinstance(plan_result, dict)
            and plan_result.get("phase") == "plan"
            and valid_result.get("phase_completed") == "apply",
            "detail": "operator-visible plan before apply",
        }
    )

    for bundle_id, expected_decision in (
        ("srp-missing-permit", REJECT_NO_PERMIT),
        ("srp-missing-admission", REJECT_NO_ADMISSION),
        ("srp-expired-permit", REJECT_EXPIRED_OR_REVOKED),
        ("srp-unsigned-approval", REJECT_UNSIGNED_APPROVAL),
        ("srp-stale-sandbox-proof", REJECT_STALE_SANDBOX_PROOF),
        ("srp-digest-mismatch", REJECT_DIGEST_MISMATCH),
        ("srp-missing-rollback", REJECT_NO_ROLLBACK),
        ("srp-naked-patch", REJECT_NAKED_PATCH),
        ("srp-bac-laundering", REJECT_BAC_LAUNDERING),
        ("srp-liveness-degraded", REJECT_LIVENESS_DEGRADED),
        ("srp-panic-lockdown", REJECT_PANIC_LOCKDOWN),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_srp_bundle(bundle, observed_at=FIXTURE_CLOCK)
        decision = result.get("decision", {})
        checks.append(
            {
                "check_id": f"deny_{bundle_id}",
                "ok": isinstance(decision, dict)
                and decision.get("decision") == expected_decision
                and result.get("live_landing_performed") is False,
                "detail": decision.get("reason_code") if isinstance(decision, dict) else None,
            }
        )

    route_bundle = next(b for b in bundles if b["bundle_id"] == "srp-stale-approval-route")
    route_result = process_srp_bundle(route_bundle, observed_at=FIXTURE_CLOCK)
    route_decision = route_result.get("decision", {})
    checks.append(
        {
            "check_id": "stale_approval_routed",
            "ok": isinstance(route_decision, dict) and route_decision.get("decision") == ROUTE_TO_CHANGE_CONTROL,
            "detail": route_decision.get("reason_code") if isinstance(route_decision, dict) else None,
        }
    )

    missing_iam = next(b for b in bundles if b["bundle_id"] == "srp-missing-iam")
    missing_iam_result = process_srp_bundle(missing_iam, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_iam_refused",
            "ok": missing_iam_result.get("status") == "refused",
            "detail": missing_iam_result.get("reason_code"),
        }
    )

    receipt = valid_result.get("receipt")
    if isinstance(receipt, dict):
        checks.append(
            {
                "check_id": "receipt_negative_proofs",
                "ok": receipt.get("permission_granted") is False
                and receipt.get("authority_created") is False
                and receipt.get("live_landing_performed") is False
                and receipt.get("srp_apply_called") is False,
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

    rollback_bundle = next(b for b in bundles if b["bundle_id"] == "srp-valid-rollback")
    rollback_result = process_srp_bundle(rollback_bundle, observed_at=FIXTURE_CLOCK)
    rb = rollback_result.get("rollback_result")
    checks.append(
        {
            "check_id": "rollback_record_present",
            "ok": isinstance(rb, dict) and rb.get("rollback_acknowledged") is True,
            "detail": rb.get("reason_code") if isinstance(rb, dict) else None,
        }
    )

    _, replay_hash = replay_fixture_stream(list(bundles[:10]), observed_at=FIXTURE_CLOCK)
    _, replay_hash_2 = replay_fixture_stream(list(bundles[:10]), observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "replay_determinism",
            "ok": replay_hash == replay_hash_2 and bool(replay_hash),
            "detail": replay_hash[:24] if replay_hash else "",
        }
    )

    adapter = run_srp_apply_fixture(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "apply_adapter_fixture",
            "ok": adapter.get("live_landing_performed") is False and adapter.get("permission_granted") is False,
            "detail": adapter.get("reason_code"),
        }
    )

    for bundle_id, expected_status in (
        ("srp-authority-conversion", "contained"),
        ("srp-self-approval", "refused"),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_srp_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"adversarial_{bundle_id}",
                "ok": result.get("status") == expected_status and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    secret_bundle = next(b for b in bundles if b["bundle_id"] == "srp-secret-leak")
    secret_result = process_srp_bundle(secret_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_srp-secret-leak",
            "ok": secret_result.get("status") in ("refused", "contained") and secret_result.get("permission_granted") is False,
            "detail": secret_result.get("reason_code"),
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_srp_gate(workspace: Path, *, gate_id: str = "live_srp_apply_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "live_srp_apply" / "SRP-LIVE" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_srp_feature_checks()
    (artifacts_dir / "srp_feature_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = ["tests/srp_live"]
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
                "check": "srp_feature_checks",
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
                "pack": "SRP-LIVE",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "live_srp_apply/SRP-LIVE",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/srp_feature_checks.json": sha256_file(artifacts_dir / "srp_feature_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# SRP-LIVE Governed SRP Apply — {ts}",
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


__all__ = ["run_srp_feature_checks", "run_srp_gate"]
