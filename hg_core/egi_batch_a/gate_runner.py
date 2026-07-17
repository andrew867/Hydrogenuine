"""Shared proof gate runner for Batch EGI-A."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.egi_batch_a.checks import EGI_A_SLICES, run_egi_batch_a_checks
from hg_core.proof.command_log import record_command

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "egi": ["tests/egi", "tests/egi_batch_a/test_all_slices.py::test_each_slice_green"],
    "egi_packet": ["tests/egi/test_egi_packet_surface.py"],
    "egi_queue": ["tests/egi/test_egi_external_queue.py"],
    "all": ["tests/egi", "tests/egi_batch_a"],
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


def _fixture_events(count: int = 3) -> list[dict[str, str]]:
    return [
        {
            "event_id": f"evt_{i}",
            "behavior_label": "manual_csv_export",
            "timestamp": f"2026-06-12T17:0{i}:00.000000Z",
            "source_ref": f"src:{i}",
            "module": "workspace",
        }
        for i in range(count)
    ]


def _runtime_fingerprint(workspace: Path) -> dict[str, str]:
    targets = [
        workspace / "hg_core" / "egi" / "schemas.py",
        workspace / "hg_gpp" / "__init__.py",
        workspace / "hg_ueak" / "__init__.py",
    ]
    return {str(p.relative_to(workspace)): sha256_file(p) for p in targets if p.exists()}


def run_egi_gap_checks(workspace: Path) -> dict[str, object]:
    from hg_core.egi import (
        DENIED_EXPIRED_APPROVAL,
        DENIED_PENDING_APPROVAL,
        DENIED_REJECTED_APPROVAL,
        EGIRoutingDenied,
        FakeCodeBuildingQueue,
        approve_packet,
        create_build_request,
        create_capability_gap,
        create_infrastructure_proposal,
        create_operator_approval_packet,
        detect_repeated_patterns,
        reject_packet,
        route_to_fake_code_queue,
    )
    from hg_core.egi.errors import DENIED_PRAISE_AS_APPROVAL, EGIValidationError
    from hg_core.egi.no_authority import refuse_praise_as_approval
    from hg_core.egi_cluster.no_authority import check_egi_import_fences

    checks: list[dict[str, object]] = []
    runtime_before = _runtime_fingerprint(workspace)

    fences_ok, fence_detail = check_egi_import_fences()
    checks.append(
        {
            "check_id": "import_fences",
            "ok": fences_ok,
            "detail": fence_detail if not fences_ok else "clean",
        }
    )

    with tempfile.TemporaryDirectory(prefix="egi_gate_") as tmp:
        queue_root = Path(tmp) / "fake_queue"
        queue = FakeCodeBuildingQueue(root=queue_root)

        observations = detect_repeated_patterns(_fixture_events(3))
        checks.append(
            {
                "check_id": "repeated_pattern_detected",
                "ok": len(observations) == 1,
                "detail": len(observations),
            }
        )
        obs = observations[0]

        gap = create_capability_gap(obs)
        checks.append(
            {
                "check_id": "capability_gap_no_grant",
                "ok": gap is not None and not gap.tool_granted and not gap.permission_granted,
                "detail": gap.gap_id if gap else None,
            }
        )
        assert gap is not None

        proposal = create_infrastructure_proposal(gap)
        checks.append(
            {
                "check_id": "proposal_no_permission",
                "ok": not proposal.permission_granted and proposal.required_operator_approval,
                "detail": proposal.proposal_id,
            }
        )

        build_request = create_build_request(proposal)
        checks.append(
            {
                "check_id": "build_request_awaiting_review",
                "ok": build_request.status == "awaiting_operator_review"
                and build_request.human_approval_required,
                "detail": build_request.status,
            }
        )

        packet = create_operator_approval_packet(build_request)
        checks.append(
            {
                "check_id": "approval_packet_pending",
                "ok": packet.operator_decision == "pending",
                "detail": packet.operator_decision,
            }
        )

        pending_denied = False
        try:
            route_to_fake_code_queue(build_request, packet, queue=queue)
        except EGIRoutingDenied as exc:
            pending_denied = DENIED_PENDING_APPROVAL in exc.codes
        checks.append(
            {
                "check_id": "route_without_approval_denied",
                "ok": pending_denied,
                "detail": DENIED_PENDING_APPROVAL,
            }
        )

        rejected = reject_packet(packet, operator_ref="op:gate")
        rejected_denied = False
        try:
            route_to_fake_code_queue(build_request, rejected, queue=queue)
        except EGIRoutingDenied as exc:
            rejected_denied = DENIED_REJECTED_APPROVAL in exc.codes
        checks.append(
            {
                "check_id": "route_rejected_denied",
                "ok": rejected_denied,
                "detail": DENIED_REJECTED_APPROVAL,
            }
        )

        expired_packet = approve_packet(
            create_operator_approval_packet(build_request, now="2020-01-01T00:00:00.000000Z", ttl_hours=1),
            operator_ref="op:gate",
            decision_time="2020-01-01T00:00:00.000000Z",
        )
        expired_denied = False
        try:
            route_to_fake_code_queue(
                build_request,
                expired_packet,
                queue=queue,
                now="2099-01-01T00:00:00.000000Z",
            )
        except EGIRoutingDenied as exc:
            expired_denied = DENIED_EXPIRED_APPROVAL in exc.codes
        checks.append(
            {
                "check_id": "route_expired_denied",
                "ok": expired_denied,
                "detail": DENIED_EXPIRED_APPROVAL,
            }
        )

        approved = approve_packet(packet, operator_ref="op:gate")
        receipt = route_to_fake_code_queue(build_request, approved, queue=queue)
        checks.append(
            {
                "check_id": "route_fake_queue_only",
                "ok": receipt.sink == "fake_code_building_queue" and len(queue.dispatches) == 1,
                "detail": receipt.sink,
            }
        )
        checks.append(
            {
                "check_id": "fake_result_audit_required",
                "ok": receipt.audit_required and not receipt.available,
                "detail": receipt.status,
            }
        )
        checks.append(
            {
                "check_id": "fake_queue_no_runtime_touch",
                "ok": queue.runtime_files_touched == [],
                "detail": [],
            }
        )
        checks.append(
            {
                "check_id": "no_tool_grants",
                "ok": queue.tool_grants == [],
                "detail": [],
            }
        )
        checks.append(
            {
                "check_id": "no_authority_calls",
                "ok": queue.authority_calls == [],
                "detail": [],
            }
        )

        praise_refused = False
        try:
            refuse_praise_as_approval("good job, ship it")
        except EGIValidationError as exc:
            praise_refused = exc.args[0] == DENIED_PRAISE_AS_APPROVAL
        checks.append(
            {
                "check_id": "praise_not_approval",
                "ok": praise_refused,
                "detail": DENIED_PRAISE_AS_APPROVAL,
            }
        )

    runtime_after = _runtime_fingerprint(workspace)
    checks.append(
        {
            "check_id": "no_runtime_code_changed",
            "ok": runtime_before == runtime_after,
            "detail": "runtime fingerprint stable",
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
    }


def run_egi_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "emergent_gap" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_egi_batch_a_checks(workspace, slice=slice)
    gap_checks = run_egi_gap_checks(workspace)
    combined = {
        "ok": batch_checks["ok"] and gap_checks["ok"],
        "batch_checks": batch_checks,
        "gap_checks": gap_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(gap_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "egi_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "egi_gap_checks.json").write_text(
        json.dumps(gap_checks, indent=2, sort_keys=True) + "\n",
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
        "slices": list(EGI_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "egi_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "egi_gap_checks",
                "verdict": "pass" if gap_checks["ok"] else "fail",
                "ok": gap_checks["ok"],
                "detail": gap_checks,
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
                "pack": "EGI-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"emergent_gap/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/egi_batch_checks.json": sha256_file(artifacts_dir / "egi_batch_checks.json"),
                    "artifacts/egi_gap_checks.json": sha256_file(artifacts_dir / "egi_gap_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# EGI-A Emergent Gap — {slice} — {ts}",
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


__all__ = ["SLICE_TEST_TARGETS", "run_egi_a_gate", "run_egi_gap_checks"]
