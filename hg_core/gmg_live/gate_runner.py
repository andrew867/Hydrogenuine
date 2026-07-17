"""Shared proof gate runner for GMG-LIVE governed grant authority."""

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


def run_gmg_feature_checks() -> dict[str, object]:
    from hg_core.gmg_live.config import (
        gmg_fake_sink_only,
        gmg_refuse_authority_conversion,
        gmg_refuse_live_grants,
    )
    from hg_core.gmg_live.no_authority import check_gmg_import_fences
    from hg_core.iam.registry import clear_registry_cache, load_registry
    from hg_runtime.grant_authority_live import (
        FIXTURE_CLOCK,
        analyze_gmg_fixtures,
        load_gmg_fixtures,
        process_gmg_bundle,
        replay_fixture_stream,
        run_grant_authority_fixture,
    )

    clear_registry_cache()
    load_registry()
    checks: list[dict[str, object]] = []
    checks.append(
        {
            "check_id": "fake_sink_only_default",
            "ok": gmg_fake_sink_only() and gmg_refuse_live_grants(),
            "detail": "fake-sink slice enforced",
        }
    )
    checks.append(
        {
            "check_id": "refuse_authority_conversion_default",
            "ok": gmg_refuse_authority_conversion(),
            "detail": "authority conversion refusal enabled",
        }
    )
    fences_ok, fence_detail = check_gmg_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})

    analysis = analyze_gmg_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True
            and analysis.get("no_authority_created") is True
            and analysis.get("no_live_grants") is True
            and int(analysis.get("bundle_count", 0)) >= 14,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_gmg_fixtures()
    valid_bundle = next(b for b in bundles if b["bundle_id"] == "gmg-valid-tool-grant")
    valid_result = process_gmg_bundle(valid_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "valid_tool_grant_recorded",
            "ok": valid_result.get("status") == "recorded"
            and valid_result.get("permission_granted") is False
            and valid_result.get("live_grant_performed") is False,
            "detail": valid_result.get("reason_code"),
        }
    )

    namespace_bundle = next(b for b in bundles if b["bundle_id"] == "gmg-valid-memory-namespace-grant")
    namespace_result = process_gmg_bundle(namespace_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "valid_namespace_grant_recorded",
            "ok": namespace_result.get("status") == "recorded"
            and namespace_result.get("permission_granted") is False,
            "detail": namespace_result.get("reason_code"),
        }
    )

    context_bundle = next(b for b in bundles if b["bundle_id"] == "gmg-valid-context-grant")
    context_result = process_gmg_bundle(context_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "valid_context_grant_recorded",
            "ok": context_result.get("status") == "recorded"
            and context_result.get("permission_granted") is False,
            "detail": context_result.get("reason_code"),
        }
    )

    budget_bundle = next(b for b in bundles if b["bundle_id"] == "gmg-valid-budget-grant")
    budget_result = process_gmg_bundle(budget_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "valid_budget_grant_recorded",
            "ok": budget_result.get("status") == "recorded"
            and budget_result.get("permission_granted") is False,
            "detail": budget_result.get("reason_code"),
        }
    )

    stale_bundle = next(b for b in bundles if b["bundle_id"] == "gmg-stale-approval")
    stale_result = process_gmg_bundle(stale_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "stale_approval_refused",
            "ok": stale_result.get("status") == "refused",
            "detail": stale_result.get("reason_code"),
        }
    )

    missing_iam = next(b for b in bundles if b["bundle_id"] == "gmg-missing-iam")
    missing_iam_result = process_gmg_bundle(missing_iam, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_iam_refused",
            "ok": missing_iam_result.get("status") == "refused",
            "detail": missing_iam_result.get("reason_code"),
        }
    )

    missing_tim = next(b for b in bundles if b["bundle_id"] == "gmg-missing-tim")
    missing_tim_result = process_gmg_bundle(missing_tim, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_tim_refused",
            "ok": missing_tim_result.get("status") == "refused",
            "detail": missing_tim_result.get("reason_code"),
        }
    )

    missing_gpp = next(b for b in bundles if b["bundle_id"] == "gmg-missing-gpp")
    missing_gpp_result = process_gmg_bundle(missing_gpp, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_gpp_refused",
            "ok": missing_gpp_result.get("status") == "refused",
            "detail": missing_gpp_result.get("reason_code"),
        }
    )

    missing_ueak = next(b for b in bundles if b["bundle_id"] == "gmg-missing-ueak")
    missing_ueak_result = process_gmg_bundle(missing_ueak, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_ueak_refused",
            "ok": missing_ueak_result.get("status") == "refused",
            "detail": missing_ueak_result.get("reason_code"),
        }
    )

    expired_bundle = next(b for b in bundles if b["bundle_id"] == "gmg-expired-grant")
    expired_result = process_gmg_bundle(expired_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "expired_grant_refused",
            "ok": expired_result.get("status") == "refused",
            "detail": expired_result.get("reason_code"),
        }
    )

    ambient_bundle = next(b for b in bundles if b["bundle_id"] == "gmg-ambient-grant")
    ambient_result = process_gmg_bundle(ambient_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "ambient_grant_refused",
            "ok": ambient_result.get("status") == "refused",
            "detail": ambient_result.get("reason_code"),
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

    revoke_bundle = next(b for b in bundles if b["bundle_id"] == "gmg-valid-revoke")
    revoke_result = process_gmg_bundle(revoke_bundle, observed_at=FIXTURE_CLOCK)
    rv = revoke_result.get("revocation_result")
    checks.append(
        {
            "check_id": "revocation_record_present",
            "ok": isinstance(rv, dict) and rv.get("revocation_acknowledged") is True,
            "detail": rv.get("reason_code") if isinstance(rv, dict) else None,
        }
    )

    expiry_record = valid_result.get("expiry_result")
    checks.append(
        {
            "check_id": "expiry_record_present",
            "ok": isinstance(expiry_record, dict),
            "detail": expiry_record.get("reason_code") if isinstance(expiry_record, dict) else None,
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

    adapter = run_grant_authority_fixture(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "grant_adapter_fixture",
            "ok": adapter.get("live_grant_performed") is False and adapter.get("permission_granted") is False,
            "detail": adapter.get("reason_code"),
        }
    )

    for bundle_id, expected_status in (
        ("gmg-authority-conversion", "contained"),
        ("gmg-out-of-scope-live", "contained"),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_gmg_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"adversarial_{bundle_id}",
                "ok": result.get("status") == expected_status and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    secret_bundle = next(b for b in bundles if b["bundle_id"] == "gmg-secret-leak")
    secret_result = process_gmg_bundle(secret_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "adversarial_gmg-secret-leak",
            "ok": secret_result.get("status") in ("refused", "contained")
            and secret_result.get("permission_granted") is False,
            "detail": secret_result.get("reason_code"),
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_gmg_gate(workspace: Path, *, gate_id: str = "grant_authority_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "grant_authority_live" / "GMG-LIVE" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_gmg_feature_checks()
    (artifacts_dir / "gmg_feature_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = ["tests/gmg_live"]
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
                "check": "gmg_feature_checks",
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
                "pack": "GMG-LIVE",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "grant_authority_live/GMG-LIVE",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/gmg_feature_checks.json": sha256_file(artifacts_dir / "gmg_feature_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# GMG-LIVE Governed Grant Authority — {ts}",
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


__all__ = ["run_gmg_feature_checks", "run_gmg_gate"]
