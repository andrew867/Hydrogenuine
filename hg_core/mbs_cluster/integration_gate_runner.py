"""ARM-INT autonomic multibus integration proof gate runner."""

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


def run_arm_integration_checks() -> dict[str, object]:
    from hg_runtime.autonomic_runtime_multibus.integration import (
        analyze_all_arm_bus_modules,
        compose_bus_fixture_surfaces,
        validate_arm_bus_receipt_alignment,
        validate_delegation_no_spawn,
        validate_edge_filter_blocks_naked_messages,
        validate_no_bus_to_authority,
        validate_scheduler_no_live_backends,
    )
    from hg_runtime.autonomic_runtime_multibus.types import FIXTURE_CLOCK, REQUIRED_ARM_BUS_MODULES

    checks: list[dict[str, object]] = []

    surfaces = compose_bus_fixture_surfaces(observed_at=FIXTURE_CLOCK)
    bus_surfaces = surfaces.get("bus_surfaces", {})
    recorded_count = 0
    if isinstance(bus_surfaces, dict):
        recorded_count = sum(
            1 for v in bus_surfaces.values() if isinstance(v, dict) and v.get("status") == "recorded"
        )
    checks.append(
        {
            "check_id": "bus_fixture_surfaces_composed",
            "ok": recorded_count == len(REQUIRED_ARM_BUS_MODULES)
            and surfaces.get("permission_granted") is False,
            "detail": recorded_count,
        }
    )

    analysis = analyze_all_arm_bus_modules(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "all_modules_advisory",
            "ok": analysis.get("all_modules_advisory") is True
            and analysis.get("no_authority_created") is True,
            "detail": len(REQUIRED_ARM_BUS_MODULES),
        }
    )

    no_authority = validate_no_bus_to_authority(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "no_bus_to_authority",
            "ok": no_authority.get("no_bus_to_authority") is True,
            "detail": no_authority.get("violations", []),
        }
    )

    edge_filter = validate_edge_filter_blocks_naked_messages()
    checks.append(
        {
            "check_id": "edge_filter_blocks_naked_messages",
            "ok": edge_filter.get("naked_blocked") is True
            and edge_filter.get("wrapped_passes") is True,
            "detail": "naked blocked, wrapped passes",
        }
    )

    scheduler = validate_scheduler_no_live_backends()
    checks.append(
        {
            "check_id": "scheduler_no_live_backends",
            "ok": scheduler.get("fixture_backend_ok") is True
            and scheduler.get("live_backend_rejected") is True,
            "detail": "fixture ok, live rejected",
        }
    )

    delegation = validate_delegation_no_spawn(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "delegation_no_spawn",
            "ok": delegation.get("delegation_no_spawn") is True
            and delegation.get("agent_spawned") is False,
            "detail": delegation.get("spawn_violations", []),
        }
    )

    alignment = validate_arm_bus_receipt_alignment(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "arm_bus_receipt_alignment",
            "ok": alignment.get("all_aligned") is True
            and alignment.get("permission_granted") is False,
            "detail": alignment.get("aligned_recorded_modules"),
        }
    )

    module_analyses = analysis.get("module_analyses", {})
    if isinstance(module_analyses, dict):
        for module in REQUIRED_ARM_BUS_MODULES:
            mod_analysis = module_analyses.get(module, {})
            bundle_count = 0
            if isinstance(mod_analysis, dict):
                bundle_count = int(mod_analysis.get("bundle_count", 0))
            checks.append(
                {
                    "check_id": f"module_{module.lower()}_fixture_count",
                    "ok": bundle_count >= 14,
                    "detail": bundle_count,
                }
            )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_arm_integration_gate(
    workspace: Path,
    *,
    gate_id: str = "autonomic_multibus_integration_v1",
) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "autonomic_runtime_multibus" / "ARM-INT" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_arm_integration_checks()
    (artifacts_dir / "arm_integration_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = [
        "tests/autonomic/test_multibus_integration.py",
        "tests/brs",
        "tests/hrt",
        "tests/rsp",
        "tests/cir",
        "tests/dbb",
        "tests/esb",
        "tests/isb",
        "tests/rdb",
        "tests/alc",
    ]
    t0 = time.monotonic()
    test_cmd = subprocess.run(
        [sys.executable, "-m", "pytest", *test_targets, "-q", "--timeout=600"],
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
                "check": "arm_integration_checks",
                "verdict": "pass" if feature_checks["ok"] else "fail",
                "ok": feature_checks["ok"],
            },
            {
                "check": "arm_integration_tests",
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
                "pack": "ARM-INT",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "autonomic_runtime_multibus",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/arm_integration_checks.json": sha256_file(
                        artifacts_dir / "arm_integration_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if not gate_ok:
        print("ARM-INT gate FAILED", file=sys.stderr)
        if test_cmd.stdout:
            print(test_cmd.stdout, file=sys.stderr)
        return 1
    print(f"ARM-INT gate GREEN — proof bundle: {proof_dir}")
    return 0


__all__ = ["run_arm_integration_checks", "run_arm_integration_gate"]
