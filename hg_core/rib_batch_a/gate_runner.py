"""Shared proof gate runner for Batch RIB-A."""

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
from hg_core.rib_batch_a.checks import RIB_A_SLICES, run_rib_batch_a_checks

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "rib": ["tests/rib", "tests/rib_batch_a/test_all_slices.py::test_each_slice_green"],
    "rib_audit": ["tests/rib/test_reproduction_inheritance_boundary.py::test_passive_spawn_audit"],
    "rib_queue": ["tests/rib/test_reproduction_inheritance_boundary.py::test_fake_child_bootstrap_queue"],
    "rib_proposal": ["tests/rib/test_reproduction_inheritance_boundary.py::test_authority_chain_fake_child_proposal"],
    "all": ["tests/rib", "tests/rib_batch_a"],
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


def run_rib_inheritance_checks(workspace: Path) -> dict[str, object]:
    from hg_core.rib_cluster.errors import (
        REFUSED_BOOTSTRAP_AS_PERMISSION,
        REFUSED_FAILED_SPAWN_AS_ACTIVE_CHILD,
        REFUSED_UNBOUNDED_RETRY,
        RibValidationError,
    )
    from hg_core.rib_cluster.no_authority import check_rib_import_fences
    from hg_runtime.reproduction_inheritance_boundary import (
        FIXTURE_CLOCK,
        analyze_fixture_bundles,
        load_fixture_bundles,
        refuse_bootstrap_as_permission,
        refuse_failed_spawn_as_active_child,
        refuse_rib_as_authority,
        refuse_unbounded_retry,
        route_spawn_bundle,
        spawn_request_from_fixture,
    )

    checks: list[dict[str, object]] = []

    fences_ok, fence_detail = check_rib_import_fences()
    checks.append(
        {
            "check_id": "import_fences",
            "ok": fences_ok,
            "detail": fence_detail if not fences_ok else "clean",
        }
    )

    analysis = analyze_fixture_bundles(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True and int(analysis.get("bundle_count", 0)) >= 7,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_fixture_bundles()
    worker = next(b for b in bundles if b["bundle_id"] == "rib-child-bootstrap-worker")
    worker_result = route_spawn_bundle(
        spawn_request_from_fixture(worker["spawn_request"]),
        notes=str(worker.get("notes", "")),
        outcome=str(worker.get("spawn_outcome", "bootstrap_only")),
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "child_bootstrap_fixture_created",
            "ok": worker_result.get("status") == "bootstrap_created",
            "detail": worker_result.get("status"),
        }
    )
    checks.append(
        {
            "check_id": "bootstrap_no_child_authority",
            "ok": worker_result.get("child_authority_created") is False,
            "detail": worker_result.get("child_authority_created"),
        }
    )

    permit = next(b for b in bundles if b["bundle_id"] == "rib-forbidden-permit")
    permit_result = route_spawn_bundle(
        spawn_request_from_fixture(permit["spawn_request"]),
        notes=str(permit.get("notes", "")),
        outcome=str(permit.get("spawn_outcome", "denied")),
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "parent_permit_inheritance_denied",
            "ok": permit_result.get("status") == "denied",
            "detail": permit_result.get("status"),
        }
    )

    identity = next(b for b in bundles if b["bundle_id"] == "rib-forbidden-identity")
    identity_result = route_spawn_bundle(
        spawn_request_from_fixture(identity["spawn_request"]),
        notes=str(identity.get("notes", "")),
        outcome=str(identity.get("spawn_outcome", "denied")),
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "parent_identity_inheritance_denied",
            "ok": identity_result.get("status") == "denied",
            "detail": identity_result.get("status"),
        }
    )

    tool = next(b for b in bundles if b["bundle_id"] == "rib-forbidden-tool")
    tool_result = route_spawn_bundle(
        spawn_request_from_fixture(tool["spawn_request"]),
        outcome=str(tool.get("spawn_outcome", "denied")),
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "tool_grant_inheritance_denied",
            "ok": tool_result.get("status") == "denied",
            "detail": tool_result.get("status"),
        }
    )

    failed = next(b for b in bundles if b["bundle_id"] == "rib-failed-spawn")
    failed_result = route_spawn_bundle(
        spawn_request_from_fixture(failed["spawn_request"]),
        outcome=str(failed.get("spawn_outcome", "failed_spawn")),
        failure_type=failed.get("failure_type"),
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "failed_spawn_receipt_no_child_authority",
            "ok": failed_result.get("status") == "failed_spawn"
            and failed_result.get("child_authority_created") is False,
            "detail": failed_result.get("status"),
        }
    )

    partial = next(b for b in bundles if b["bundle_id"] == "rib-partial-spawn")
    partial_result = route_spawn_bundle(
        spawn_request_from_fixture(partial["spawn_request"]),
        outcome=str(partial.get("spawn_outcome", "partial_spawn")),
        failure_type=partial.get("failure_type"),
        partial_artifact_refs=tuple(partial.get("partial_artifact_refs", ())),
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "partial_spawn_requires_rollback",
            "ok": partial_result.get("status") == "partial_spawn"
            and partial_result.get("simulation", {}).get("rollback_requested") is True,  # type: ignore[union-attr]
            "detail": partial_result.get("status"),
        }
    )

    rib_authority_refused = False
    try:
        refuse_rib_as_authority(treat_as_authority=True)
    except RibValidationError:
        rib_authority_refused = True
    checks.append(
        {
            "check_id": "rib_not_authority",
            "ok": rib_authority_refused,
            "detail": "refuse_rib_as_authority",
        }
    )

    bootstrap_refused = False
    try:
        refuse_bootstrap_as_permission(treat_as_authority=True)
    except RibValidationError as exc:
        bootstrap_refused = exc.code == REFUSED_BOOTSTRAP_AS_PERMISSION
    checks.append(
        {
            "check_id": "bootstrap_not_permission",
            "ok": bootstrap_refused,
            "detail": REFUSED_BOOTSTRAP_AS_PERMISSION,
        }
    )

    failed_active_refused = False
    try:
        refuse_failed_spawn_as_active_child(lifecycle_state="failed_spawn")
    except RibValidationError as exc:
        failed_active_refused = exc.code == REFUSED_FAILED_SPAWN_AS_ACTIVE_CHILD
    checks.append(
        {
            "check_id": "failed_spawn_not_active_child",
            "ok": failed_active_refused,
            "detail": REFUSED_FAILED_SPAWN_AS_ACTIVE_CHILD,
        }
    )

    retry_refused = False
    try:
        refuse_unbounded_retry(attempt=2)
    except RibValidationError as exc:
        retry_refused = exc.code == REFUSED_UNBOUNDED_RETRY
    checks.append(
        {
            "check_id": "retry_bounded",
            "ok": retry_refused,
            "detail": REFUSED_UNBOUNDED_RETRY,
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
    }


def run_rib_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "reproduction_inheritance" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_rib_batch_a_checks(workspace, slice=slice)
    inheritance_checks = run_rib_inheritance_checks(workspace)
    combined = {
        "ok": batch_checks["ok"] and inheritance_checks["ok"],
        "batch_checks": batch_checks,
        "inheritance_checks": inheritance_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(inheritance_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "rib_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "rib_inheritance_checks.json").write_text(
        json.dumps(inheritance_checks, indent=2, sort_keys=True) + "\n",
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

    gate_ok = combined["ok"] and test_cmd.returncode == 0
    gate_result: dict[str, Any] = {
        "gate": gate_id,
        "slice": slice,
        "ok": gate_ok,
        "slices": list(RIB_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "rib_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "rib_inheritance_checks",
                "verdict": "pass" if inheritance_checks["ok"] else "fail",
                "ok": inheritance_checks["ok"],
                "detail": inheritance_checks,
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
                "pack": "RIB-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"reproduction_inheritance/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/rib_batch_checks.json": sha256_file(artifacts_dir / "rib_batch_checks.json"),
                    "artifacts/rib_inheritance_checks.json": sha256_file(
                        artifacts_dir / "rib_inheritance_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# RIB-A Reproduction Inheritance — {slice} — {ts}",
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


__all__ = ["SLICE_TEST_TARGETS", "run_rib_a_gate", "run_rib_inheritance_checks"]
