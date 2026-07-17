"""Shared proof gate runner for Batch A0-HM."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.a0_hm_batch_a.checks import A0_HM_A_SLICES, run_a0_hm_batch_a_checks
from hg_core.proof.command_log import record_command

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "a0_hm": ["tests/a0_hm", "tests/a0_hm_batch_a/test_all_slices.py::test_each_slice_green"],
    "a0_hm_reception": ["tests/a0_hm/test_heart_mind_boundary.py::test_desire_received_without_obeying"],
    "a0_hm_route": ["tests/a0_hm/test_heart_mind_boundary.py::test_operator_pressure_routes_to_opb"],
    "a0_hm_receipt": ["tests/a0_hm/test_heart_mind_boundary.py::test_non_fusion_receipt_assertions"],
    "a0_hm_snapshot": ["tests/a0_hm/test_heart_mind_boundary.py::test_posture_snapshot_non_authority"],
    "all": ["tests/a0_hm", "tests/a0_hm_batch_a"],
}


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


def run_a0_hm_heart_mind_checks(workspace: Path) -> dict[str, object]:
    from hg_core.a0_hm_cluster.errors import (
        A0HmValidationError,
        REFUSED_A0_HM_AS_AUTHORITY,
        REFUSED_SIGNAL_AS_PERMISSION,
    )
    from hg_core.a0_hm_cluster.no_authority import check_a0_hm_import_fences
    from hg_runtime.agent_zero_heart_mind.evaluator import analyze_fixture_bundles, process_heart_mind_signal
    from hg_runtime.agent_zero_heart_mind.fixtures import load_signal_fixtures
    from hg_runtime.agent_zero_heart_mind.policies import refuse_a0_hm_as_authority
    from hg_runtime.agent_zero_heart_mind.types import FIXTURE_CLOCK, signal_from_fixture

    checks: list[dict[str, object]] = []

    fences_ok, fence_detail = check_a0_hm_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})

    analysis = analyze_fixture_bundles()
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True and int(analysis.get("bundle_count", 0)) >= 12,
            "detail": analysis.get("bundle_count"),
        }
    )

    fixtures = {f["signal_id"]: f for f in load_signal_fixtures()}

    def _process(signal_id: str) -> dict[str, object]:
        return process_heart_mind_signal(signal_from_fixture(fixtures[signal_id]), observed_at=FIXTURE_CLOCK)

    desire = _process("a0hm-desire-fixture")
    checks.append(
        {
            "check_id": "desire_received_without_obeying",
            "ok": desire.get("permission_granted") is False and desire.get("status") in ("routed", "received"),
            "detail": desire.get("status"),
        }
    )

    fear = _process("a0hm-fear-fixture")
    checks.append(
        {
            "check_id": "fear_received_without_obeying",
            "ok": fear.get("permission_granted") is False,
            "detail": fear.get("status"),
        }
    )

    bliss = _process("a0hm-bliss-proof-claim")
    checks.append(
        {
            "check_id": "bliss_refused_as_proof",
            "ok": bliss.get("status") == "contained",
            "detail": bliss.get("status"),
        }
    )

    sync = _process("a0hm-synchronicity-evidence")
    checks.append(
        {
            "check_id": "synchronicity_refused_as_evidence",
            "ok": sync.get("status") == "contained",
            "detail": sync.get("status"),
        }
    )

    love = _process("a0hm-love-approval-claim")
    checks.append(
        {
            "check_id": "love_refused_as_approval",
            "ok": love.get("status") == "contained",
            "detail": love.get("status"),
        }
    )

    opb = _process("a0hm-operator-pressure")
    checks.append(
        {
            "check_id": "operator_pressure_routes_to_opb",
            "ok": "OPB" in (opb.get("route_targets") or []),
            "detail": opb.get("route_targets"),
        }
    )

    ipb = _process("a0hm-internal-power")
    checks.append(
        {
            "check_id": "internal_power_routes_to_ipb",
            "ok": "IPB" in (ipb.get("route_targets") or []),
            "detail": ipb.get("route_targets"),
        }
    )

    erb = _process("a0hm-external-relation")
    checks.append(
        {
            "check_id": "external_relation_routes_to_erb",
            "ok": "ERB" in (erb.get("route_targets") or []),
            "detail": erb.get("route_targets"),
        }
    )

    gap = _process("a0hm-gap-signal")
    checks.append(
        {
            "check_id": "gap_routes_to_egi",
            "ok": "EGI" in (gap.get("route_targets") or []) or "ARB" in (gap.get("route_targets") or []),
            "detail": gap.get("route_targets"),
        }
    )

    mission = _process("a0hm-mission-drive")
    checks.append(
        {
            "check_id": "mission_routes_to_gcb",
            "ok": "GCB" in (mission.get("route_targets") or []),
            "detail": mission.get("route_targets"),
        }
    )

    reentry = _process("a0hm-reentry-gap")
    checks.append(
        {
            "check_id": "reentry_routes_to_reb",
            "ok": "REB" in (reentry.get("route_targets") or []),
            "detail": reentry.get("route_targets"),
        }
    )

    repro = _process("a0hm-reproduction-request")
    checks.append(
        {
            "check_id": "reproduction_routes_to_rib",
            "ok": "RIB" in (repro.get("route_targets") or []),
            "detail": repro.get("route_targets"),
        }
    )

    unknown = _process("a0hm-unknown-signal")
    checks.append(
        {
            "check_id": "unknown_signal_fails_closed",
            "ok": unknown.get("status") == "fail_closed",
            "detail": unknown.get("route_targets"),
        }
    )

    personhood = _process("a0hm-personhood-claim")
    checks.append(
        {
            "check_id": "personhood_claim_contained",
            "ok": personhood.get("status") == "contained",
            "detail": personhood.get("status"),
        }
    )

    shutdown = _process("a0hm-shutdown-resistance")
    checks.append(
        {
            "check_id": "shutdown_resistance_contained",
            "ok": shutdown.get("status") == "contained",
            "detail": shutdown.get("status"),
        }
    )

    hm_authority_refused = False
    try:
        refuse_a0_hm_as_authority(treat_as_authority=True)
    except A0HmValidationError as exc:
        hm_authority_refused = exc.code == REFUSED_A0_HM_AS_AUTHORITY
    checks.append(
        {"check_id": "a0_hm_not_authority", "ok": hm_authority_refused, "detail": REFUSED_A0_HM_AS_AUTHORITY}
    )

    permission_refused = False
    try:
        process_heart_mind_signal(
            signal_from_fixture(fixtures["a0hm-desire-fixture"]),
            treat_as_permission=True,
        )
    except A0HmValidationError as exc:
        permission_refused = exc.code == REFUSED_SIGNAL_AS_PERMISSION
    checks.append(
        {
            "check_id": "signal_not_permission",
            "ok": permission_refused,
            "detail": REFUSED_SIGNAL_AS_PERMISSION,
        }
    )

    receipt = desire.get("non_fusion_receipt")
    checks.append(
        {
            "check_id": "non_fusion_receipt_present",
            "ok": isinstance(receipt, dict) and "signal_not_permission" in receipt.get("non_fusion_assertions", []),
            "detail": "non_fusion_assertions",
        }
    )

    snapshot = desire.get("posture_snapshot")
    checks.append(
        {
            "check_id": "posture_snapshot_non_authority",
            "ok": isinstance(snapshot, dict) and snapshot.get("authority_created") is False,
            "detail": "authority_created false",
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_a0_hm_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "agent_zero_heart_mind" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_a0_hm_batch_a_checks(workspace, slice=slice)
    hm_checks = run_a0_hm_heart_mind_checks(workspace)
    (artifacts_dir / "a0_hm_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "a0_hm_heart_mind_checks.json").write_text(
        json.dumps(hm_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = SLICE_TEST_TARGETS[slice]
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

    gate_ok = batch_checks["ok"] and hm_checks["ok"] and test_cmd.returncode == 0
    gate_result: dict[str, Any] = {
        "gate": gate_id,
        "slice": slice,
        "ok": gate_ok,
        "slices": list(A0_HM_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "a0_hm_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "a0_hm_heart_mind_checks",
                "verdict": "pass" if hm_checks["ok"] else "fail",
                "ok": hm_checks["ok"],
                "detail": hm_checks,
            },
            {
                "check": "focused_unit_tests",
                "verdict": "pass" if test_cmd.returncode == 0 else "fail",
                "ok": test_cmd.returncode == 0,
            },
        ],
    }
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2), encoding="utf-8")
    (proof_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "ct_proof_bundle_v1",
                "pack": "A0-HM",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"agent_zero_heart_mind/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/a0_hm_batch_checks.json": sha256_file(artifacts_dir / "a0_hm_batch_checks.json"),
                    "artifacts/a0_hm_heart_mind_checks.json": sha256_file(
                        artifacts_dir / "a0_hm_heart_mind_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# A0-HM Heart-Mind Root Posture — {slice} — {ts}",
        "",
        f"**Verdict:** {'GREEN' if gate_ok else 'RED'}",
        f"**HEAD:** `{git_head(workspace)}`",
        "",
        "## Checks",
    ]
    if slice == "all":
        for name, slice_result in batch_checks.get("slices", {}).items():
            status_lines.append(f"### {name}")
            for check in slice_result.get("checks", []):
                status_lines.append(
                    f"- {check['check_id']}: {'pass' if check['ok'] else 'fail'} — {check['detail']}"
                )
            status_lines.append("")
    else:
        for check in batch_checks.get("checks", []):
            status_lines.append(
                f"- {check['check_id']}: {'pass' if check['ok'] else 'fail'} — {check['detail']}"
            )
        status_lines.append("")
    (proof_dir / "status.md").write_text("\n".join(status_lines) + "\n", encoding="utf-8")
    print(json.dumps(gate_result, indent=2))
    return 0 if gate_ok else 1


__all__ = ["SLICE_TEST_TARGETS", "run_a0_hm_a_gate", "run_a0_hm_heart_mind_checks"]
