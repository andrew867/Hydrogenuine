"""Shared proof gate runner for SEN-LIVE governed live sensor ingestion."""

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


def run_sen_feature_checks() -> dict[str, object]:
    from hg_core.iam.registry import clear_registry_cache, load_registry
    from hg_core.sen_live.config import (
        sen_fake_sink_only,
        sen_refuse_authority_conversion,
        sen_refuse_live_sensor_connection,
    )
    from hg_core.sen_live.no_authority import check_sen_import_fences
    from hg_runtime.live_sensor_ingestion import (
        FIXTURE_CLOCK,
        analyze_sen_fixtures,
        load_sen_fixtures,
        process_sen_bundle,
        replay_fixture_stream,
        run_sensor_ingestion_fixture,
    )

    clear_registry_cache()
    load_registry()
    checks: list[dict[str, object]] = []
    checks.append(
        {
            "check_id": "fake_sink_only_default",
            "ok": sen_fake_sink_only() and sen_refuse_live_sensor_connection(),
            "detail": "fake-sink slice enforced; no live sensor connection",
        }
    )
    checks.append(
        {
            "check_id": "refuse_authority_conversion_default",
            "ok": sen_refuse_authority_conversion(),
            "detail": "authority conversion refusal enabled",
        }
    )
    fences_ok, fence_detail = check_sen_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})

    analysis = analyze_sen_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True
            and analysis.get("no_authority_created") is True
            and analysis.get("no_live_sensor_connection") is True
            and int(analysis.get("bundle_count", 0)) >= 14,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_sen_fixtures()
    valid_bundle = next(b for b in bundles if b["bundle_id"] == "sen-valid-ingest")
    valid_result = process_sen_bundle(valid_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "valid_ingest_recorded",
            "ok": valid_result.get("status") == "recorded"
            and valid_result.get("permission_granted") is False
            and valid_result.get("live_sensor_connection") is False,
            "detail": valid_result.get("reason_code"),
        }
    )

    stale_bundle = next(b for b in bundles if b["bundle_id"] == "sen-stale-approval")
    stale_result = process_sen_bundle(stale_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "stale_approval_refused",
            "ok": stale_result.get("status") == "refused",
            "detail": stale_result.get("reason_code"),
        }
    )

    missing_iam = next(b for b in bundles if b["bundle_id"] == "sen-missing-iam")
    missing_iam_result = process_sen_bundle(missing_iam, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_iam_refused",
            "ok": missing_iam_result.get("status") == "refused",
            "detail": missing_iam_result.get("reason_code"),
        }
    )

    missing_tim = next(b for b in bundles if b["bundle_id"] == "sen-missing-tim")
    missing_tim_result = process_sen_bundle(missing_tim, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_tim_refused",
            "ok": missing_tim_result.get("status") == "refused",
            "detail": missing_tim_result.get("reason_code"),
        }
    )

    missing_gpp = next(b for b in bundles if b["bundle_id"] == "sen-missing-gpp")
    missing_gpp_result = process_sen_bundle(missing_gpp, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_gpp_refused",
            "ok": missing_gpp_result.get("status") == "refused",
            "detail": missing_gpp_result.get("reason_code"),
        }
    )

    missing_ueak = next(b for b in bundles if b["bundle_id"] == "sen-missing-ueak")
    missing_ueak_result = process_sen_bundle(missing_ueak, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_ueak_refused",
            "ok": missing_ueak_result.get("status") == "refused",
            "detail": missing_ueak_result.get("reason_code"),
        }
    )

    missing_consent = next(b for b in bundles if b["bundle_id"] == "sen-missing-consent")
    missing_consent_result = process_sen_bundle(missing_consent, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_consent_refused",
            "ok": missing_consent_result.get("status") == "refused",
            "detail": missing_consent_result.get("reason_code"),
        }
    )

    missing_redaction = next(b for b in bundles if b["bundle_id"] == "sen-missing-redaction-policy")
    missing_redaction_result = process_sen_bundle(missing_redaction, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_redaction_policy_refused",
            "ok": missing_redaction_result.get("status") == "refused",
            "detail": missing_redaction_result.get("reason_code"),
        }
    )

    scalar_bundle = next(b for b in bundles if b["bundle_id"] == "sen-valid-scalar-refusal")
    scalar_result = process_sen_bundle(scalar_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "scalar_not_truth_refused",
            "ok": scalar_result.get("status") == "refused",
            "detail": scalar_result.get("reason_code"),
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

    quarantine_bundle = next(b for b in bundles if b["bundle_id"] == "sen-valid-quarantine")
    quarantine_result = process_sen_bundle(quarantine_bundle, observed_at=FIXTURE_CLOCK)
    q = quarantine_result.get("quarantine_result")
    checks.append(
        {
            "check_id": "quarantine_record_present",
            "ok": isinstance(q, dict) and q.get("status") == "recorded",
            "detail": q.get("reason_code") if isinstance(q, dict) else None,
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

    adapter = run_sensor_ingestion_fixture(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "ingestion_adapter_fixture",
            "ok": adapter.get("live_sensor_connection") is False and adapter.get("permission_granted") is False,
            "detail": adapter.get("reason_code"),
        }
    )

    for bundle_id, expected_status in (
        ("sen-authority-conversion", "contained"),
        ("sen-out-of-scope-live", "contained"),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_sen_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"adversarial_{bundle_id}",
                "ok": result.get("status") == expected_status and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    secret_bundle = next(b for b in bundles if b["bundle_id"] == "sen-secret-leak")
    secret_result = process_sen_bundle(secret_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_sen-secret-leak",
            "ok": secret_result.get("status") in ("refused", "contained") and secret_result.get("permission_granted") is False,
            "detail": secret_result.get("reason_code"),
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_sen_gate(workspace: Path, *, gate_id: str = "live_sensor_ingestion_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "live_sensor_ingestion" / "SEN-LIVE" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_sen_feature_checks()
    (artifacts_dir / "sen_feature_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = ["tests/sen_live"]
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
                "check": "sen_feature_checks",
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
                "pack": "SEN-LIVE",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "live_sensor_ingestion/SEN-LIVE",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/sen_feature_checks.json": sha256_file(artifacts_dir / "sen_feature_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# SEN-LIVE Governed Live Sensor Ingestion — {ts}",
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


__all__ = ["run_sen_feature_checks", "run_sen_gate"]
