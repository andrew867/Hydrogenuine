"""MET-INT metabolic integration proof gate runner."""

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


def run_metabolic_integration_checks() -> dict[str, object]:
    from hg_runtime.metabolic_governance.integration import (
        analyze_all_metabolic_organs,
        compose_organ_fixture_surfaces,
        validate_met_organ_receipt_alignment,
    )
    from hg_runtime.metabolic_governance.types import FIXTURE_CLOCK, REQUIRED_METABOLIC_ORGANS

    checks: list[dict[str, object]] = []

    surfaces = compose_organ_fixture_surfaces(observed_at=FIXTURE_CLOCK)
    organ_surfaces = surfaces.get("organ_surfaces", {})
    recorded_count = 0
    if isinstance(organ_surfaces, dict):
        recorded_count = sum(
            1 for v in organ_surfaces.values() if isinstance(v, dict) and v.get("status") == "recorded"
        )
    checks.append(
        {
            "check_id": "organ_fixture_surfaces_composed",
            "ok": recorded_count == len(REQUIRED_METABOLIC_ORGANS)
            and surfaces.get("permission_granted") is False,
            "detail": recorded_count,
        }
    )

    analysis = analyze_all_metabolic_organs(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "all_organs_advisory",
            "ok": analysis.get("all_organs_advisory") is True
            and analysis.get("no_authority_created") is True,
            "detail": len(REQUIRED_METABOLIC_ORGANS),
        }
    )

    alignment = validate_met_organ_receipt_alignment(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "met_organ_receipt_alignment",
            "ok": alignment.get("all_aligned") is True
            and alignment.get("met_permission_granted") is False,
            "detail": alignment.get("aligned_recorded_organs"),
        }
    )

    organ_analyses = analysis.get("organ_analyses", {})
    if isinstance(organ_analyses, dict):
        for organ in REQUIRED_METABOLIC_ORGANS:
            organ_analysis = organ_analyses.get(organ, {})
            bundle_count = 0
            if isinstance(organ_analysis, dict):
                bundle_count = int(organ_analysis.get("bundle_count", 0))
            checks.append(
                {
                    "check_id": f"organ_{organ.lower()}_fixture_count",
                    "ok": bundle_count >= 12,
                    "detail": bundle_count,
                }
            )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_metabolic_integration_gate(
    workspace: Path,
    *,
    gate_id: str = "metabolic_integration_v1",
) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "metabolic_governance" / "MET-INT" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_metabolic_integration_checks()
    (artifacts_dir / "metabolic_integration_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = [
        "tests/met/test_metabolic_integration.py",
        "tests/brb",
        "tests/nib",
        "tests/dab",
        "tests/wdb",
        "tests/tlb",
        "tests/dcd",
        "tests/gxb",
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
                "check": "metabolic_integration_checks",
                "verdict": "pass" if feature_checks["ok"] else "fail",
                "ok": feature_checks["ok"],
            },
            {
                "check": "metabolic_integration_tests",
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
                "pack": "MET-INT",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "metabolic_governance",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/metabolic_integration_checks.json": sha256_file(
                        artifacts_dir / "metabolic_integration_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if not gate_ok:
        print("MET-INT gate FAILED", file=sys.stderr)
        if test_cmd.stdout:
            print(test_cmd.stdout, file=sys.stderr)
        return 1
    print(f"MET-INT gate GREEN — proof bundle: {proof_dir}")
    return 0


__all__ = ["run_metabolic_integration_checks", "run_metabolic_integration_gate"]
