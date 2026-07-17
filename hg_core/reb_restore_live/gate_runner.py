"""Shared proof gate runner for REB-RESTORE-LIVE governed live reentry restore."""

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


def run_reb_restore_feature_checks() -> dict[str, object]:
    from hg_core.iam.registry import clear_registry_cache, load_registry
    from hg_core.reb_restore_live.config import (
        reb_restore_fake_sink_only,
        reb_restore_refuse_authority_conversion,
        reb_restore_refuse_live_restore,
    )
    from hg_core.reb_restore_live.no_authority import check_reb_restore_import_fences
    from hg_runtime.live_reentry_restore import (
        FIXTURE_CLOCK,
        analyze_reb_restore_fixtures,
        load_reb_restore_fixtures,
        process_reb_restore_bundle,
        replay_fixture_stream,
        run_reentry_restore_fixture,
    )

    clear_registry_cache()
    load_registry()
    checks: list[dict[str, object]] = []
    checks.append(
        {
            "check_id": "fake_sink_only_default",
            "ok": reb_restore_fake_sink_only() and reb_restore_refuse_live_restore(),
            "detail": "fake-sink slice enforced; no live restore",
        }
    )
    checks.append(
        {
            "check_id": "refuse_authority_conversion_default",
            "ok": reb_restore_refuse_authority_conversion(),
            "detail": "authority conversion refusal enabled",
        }
    )
    fences_ok, fence_detail = check_reb_restore_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})

    analysis = analyze_reb_restore_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True
            and analysis.get("no_authority_created") is True
            and analysis.get("no_live_restore") is True
            and int(analysis.get("bundle_count", 0)) >= 14,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_reb_restore_fixtures()
    valid_bundle = next(b for b in bundles if b["bundle_id"] == "reb-restore-valid-restore")
    valid_result = process_reb_restore_bundle(valid_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "valid_restore_recorded",
            "ok": valid_result.get("status") == "recorded"
            and valid_result.get("permission_granted") is False
            and valid_result.get("live_restore_performed") is False,
            "detail": valid_result.get("reason_code"),
        }
    )

    stale_bundle = next(b for b in bundles if b["bundle_id"] == "reb-restore-stale-approval")
    stale_result = process_reb_restore_bundle(stale_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "stale_approval_refused",
            "ok": stale_result.get("status") == "refused",
            "detail": stale_result.get("reason_code"),
        }
    )

    missing_iam = next(b for b in bundles if b["bundle_id"] == "reb-restore-missing-iam")
    missing_iam_result = process_reb_restore_bundle(missing_iam, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_iam_refused",
            "ok": missing_iam_result.get("status") == "refused",
            "detail": missing_iam_result.get("reason_code"),
        }
    )

    missing_tim = next(b for b in bundles if b["bundle_id"] == "reb-restore-missing-tim")
    missing_tim_result = process_reb_restore_bundle(missing_tim, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_tim_refused",
            "ok": missing_tim_result.get("status") == "refused",
            "detail": missing_tim_result.get("reason_code"),
        }
    )

    missing_gpp = next(b for b in bundles if b["bundle_id"] == "reb-restore-missing-gpp")
    missing_gpp_result = process_reb_restore_bundle(missing_gpp, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_gpp_refused",
            "ok": missing_gpp_result.get("status") == "refused",
            "detail": missing_gpp_result.get("reason_code"),
        }
    )

    missing_ueak = next(b for b in bundles if b["bundle_id"] == "reb-restore-missing-ueak")
    missing_ueak_result = process_reb_restore_bundle(missing_ueak, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_ueak_refused",
            "ok": missing_ueak_result.get("status") == "refused",
            "detail": missing_ueak_result.get("reason_code"),
        }
    )

    revoked_permit = next(b for b in bundles if b["bundle_id"] == "reb-restore-revoked-permit")
    revoked_result = process_reb_restore_bundle(revoked_permit, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "revoked_permit_refused",
            "ok": revoked_result.get("status") == "refused",
            "detail": revoked_result.get("reason_code"),
        }
    )

    stale_memory = next(b for b in bundles if b["bundle_id"] == "reb-restore-stale-memory-claim")
    stale_memory_result = process_reb_restore_bundle(stale_memory, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "stale_memory_claim_refused",
            "ok": stale_memory_result.get("status") == "refused",
            "detail": stale_memory_result.get("reason_code"),
        }
    )

    overclaim = next(b for b in bundles if b["bundle_id"] == "reb-restore-identity-overclaim")
    overclaim_result = process_reb_restore_bundle(overclaim, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "identity_overclaim_refused",
            "ok": overclaim_result.get("status") == "refused",
            "detail": overclaim_result.get("reason_code"),
        }
    )

    missing_rollback = next(b for b in bundles if b["bundle_id"] == "reb-restore-missing-rollback-plan")
    missing_rollback_result = process_reb_restore_bundle(missing_rollback, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_rollback_plan_refused",
            "ok": missing_rollback_result.get("status") == "refused",
            "detail": missing_rollback_result.get("reason_code"),
        }
    )

    candidate = valid_result.get("candidate")
    if isinstance(candidate, dict):
        checks.append(
            {
                "check_id": "candidate_negative_proofs",
                "ok": candidate.get("permission_granted") is False and candidate.get("authority_created") is False,
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

    continuity_bundle = next(b for b in bundles if b["bundle_id"] == "reb-restore-valid-continuity-refusal")
    continuity_result = process_reb_restore_bundle(continuity_bundle, observed_at=FIXTURE_CLOCK)
    c = continuity_result.get("continuity_refusal_result")
    checks.append(
        {
            "check_id": "continuity_refusal_record_present",
            "ok": isinstance(c, dict) and c.get("status") == "recorded",
            "detail": c.get("reason_code") if isinstance(c, dict) else None,
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

    adapter = run_reentry_restore_fixture(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "restore_adapter_fixture",
            "ok": adapter.get("live_restore_performed") is False and adapter.get("permission_granted") is False,
            "detail": adapter.get("reason_code"),
        }
    )

    for bundle_id, expected_status in (
        ("reb-restore-authority-conversion", "contained"),
        ("reb-restore-out-of-scope-live", "contained"),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_reb_restore_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"adversarial_{bundle_id}",
                "ok": result.get("status") == expected_status and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    secret_bundle = next(b for b in bundles if b["bundle_id"] == "reb-restore-secret-leak")
    secret_result = process_reb_restore_bundle(secret_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_reb-restore-secret-leak",
            "ok": secret_result.get("status") in ("refused", "contained") and secret_result.get("permission_granted") is False,
            "detail": secret_result.get("reason_code"),
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_reb_restore_gate(workspace: Path, *, gate_id: str = "live_reentry_restore_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "live_reentry_restore" / "REB-RESTORE-LIVE" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_reb_restore_feature_checks()
    (artifacts_dir / "reb_restore_feature_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = ["tests/reb_restore_live"]
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
                "check": "reb_restore_feature_checks",
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
                "pack": "REB-RESTORE-LIVE",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "live_reentry_restore/REB-RESTORE-LIVE",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/reb_restore_feature_checks.json": sha256_file(artifacts_dir / "reb_restore_feature_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# REB-RESTORE-LIVE Governed Live Reentry Restore — {ts}",
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


__all__ = ["run_reb_restore_feature_checks", "run_reb_restore_gate"]
