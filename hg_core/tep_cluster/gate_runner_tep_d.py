"""Shared proof gate runner for TEP-D organ emission migration."""

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


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items() if k not in ("claim", "envelope")}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "to_payload"):
        return value.to_payload(include_hash=True)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def run_tep_d_feature_checks() -> dict[str, object]:
    from hg_core.tep_cluster.config import (
        tep_refuse_authority_conversion,
        tep_refuse_naked_claims,
        tep_static_fixtures_only,
    )
    from hg_core.tep_cluster.no_authority import check_tep_import_fences
    from hg_runtime.translation_envelope_protocol.organ_emission import (
        FW_QUEUE_TEP_D_LIVE,
        list_fenced_paths,
        run_tep_d_organ_emission_path,
    )
    from hg_runtime.organism_coherence.replay import replay_fixture_stream
    from hg_runtime.organism_coherence import FIXTURE_CLOCK, load_organism_fixtures

    checks: list[dict[str, object]] = []

    checks.append(
        {
            "check_id": "static_fixtures_only_default",
            "ok": tep_static_fixtures_only() and tep_refuse_naked_claims(),
            "detail": "fixture/static slice enforced by default",
        }
    )
    checks.append(
        {
            "check_id": "refuse_authority_conversion_default",
            "ok": tep_refuse_authority_conversion(),
            "detail": "authority conversion refusal enabled",
        }
    )

    fences_ok, fence_detail = check_tep_import_fences()
    checks.append(
        {
            "check_id": "import_fences_no_oea_ter",
            "ok": fences_ok,
            "detail": fence_detail if not fences_ok else "clean",
        }
    )

    path = run_tep_d_organ_emission_path()
    for key in (
        "all_organs_wrapped",
        "naked_refused",
        "gpp_naked_rejected",
        "gpp_wrapped_reviewed",
        "ueak_naked_rejected",
        "ueak_not_admitted",
        "not_translatable_marked",
        "drb_integration_ok",
        "live_paths_fenced",
        "no_oea_ter_called",
    ):
        checks.append(
            {
                "check_id": key,
                "ok": bool(path[key]),
                "detail": path.get("details", {}).get(key, path[key]),
            }
        )

    organ_results = path.get("organ_results", {})
    if isinstance(organ_results, dict):
        for organ, result in organ_results.items():
            if isinstance(result, dict):
                checks.append(
                    {
                        "check_id": f"organ_{organ.lower().replace('-', '_')}_wrapped",
                        "ok": result.get("has_translation_envelope") is True
                        and result.get("authority_created") is False,
                        "detail": organ,
                    }
                )

    fences = list_fenced_paths()
    checks.append(
        {
            "check_id": "live_rtc_paths_fenced",
            "ok": len(fences) >= 12
            and all(f.get("future_work_id") == FW_QUEUE_TEP_D_LIVE for f in fences.values()),
            "detail": len(fences),
        }
    )

    bundles = load_organism_fixtures()
    _, replay_hash = replay_fixture_stream(list(bundles[:3]), observed_at=FIXTURE_CLOCK)
    _, replay_hash_2 = replay_fixture_stream(list(bundles[:3]), observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "replay_determinism",
            "ok": replay_hash == replay_hash_2 and bool(replay_hash),
            "detail": replay_hash[:24] if replay_hash else None,
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
        "path": path,
    }


def run_tep_d_gate(workspace: Path, *, gate_id: str = "tep_d_organ_emission_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "translation_envelope_protocol" / "TEP-D" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_tep_d_feature_checks()
    (artifacts_dir / "tep_d_feature_checks.json").write_text(
        json.dumps(_json_safe(feature_checks), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = [
        "tests/tep/test_tep_d_organ_emission.py",
        "tests/tep/test_boundary_integration.py",
    ]
    t0 = time.monotonic()
    test_cmd = subprocess.run(
        [sys.executable, "-m", "pytest", *test_targets, "-q", "--timeout=300"],
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
                "check": "tep_d_feature_checks",
                "verdict": "pass" if feature_checks["ok"] else "fail",
                "ok": feature_checks["ok"],
            },
            {
                "check": "focused_unit_tests",
                "verdict": "pass" if test_cmd.returncode == 0 else "fail",
                "ok": test_cmd.returncode == 0,
            },
        ],
        "critical_failures": feature_checks.get("critical_failures", []),
    }
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2), encoding="utf-8")
    (proof_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "ct_proof_bundle_v1",
                "pack": "TEP-D",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "translation_envelope_protocol/TEP-D",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/tep_d_feature_checks.json": sha256_file(
                        artifacts_dir / "tep_d_feature_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# TEP-D Organ Emission — {ts}",
        "",
        f"**Verdict:** {'GREEN' if gate_ok else 'RED'}",
        f"**HEAD:** `{git_head(workspace)}`",
        "",
        "## Feature checks",
    ]
    for check in feature_checks.get("checks", []):
        status_lines.append(
            f"- {check['check_id']}: {'pass' if check['ok'] else 'fail'} — {check['detail']}"
        )
    status_lines.extend(
        [
            "",
            "## Pytest",
            f"- exit_code: {test_cmd.returncode}",
        ]
    )
    (proof_dir / "status.md").write_text("\n".join(status_lines) + "\n", encoding="utf-8")

    if not gate_ok:
        print("TEP-D gate FAILED", file=sys.stderr)
        if test_cmd.stdout:
            print(test_cmd.stdout, file=sys.stderr)
        if test_cmd.stderr:
            print(test_cmd.stderr, file=sys.stderr)
        for failure in feature_checks.get("critical_failures", []):
            print(f"  critical: {failure}", file=sys.stderr)
        return 1
    print(f"TEP-D gate GREEN — proof bundle: {proof_dir}")
    return 0


__all__ = ["run_tep_d_feature_checks", "run_tep_d_gate"]
