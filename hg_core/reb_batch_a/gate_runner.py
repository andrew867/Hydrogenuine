"""Shared proof gate runner for Batch REB-A."""

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
from hg_core.reb_batch_a.checks import REB_A_SLICES, run_reb_batch_a_checks

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "reb": ["tests/reb", "tests/reb_batch_a/test_all_slices.py::test_each_slice_green"],
    "reb_audit": ["tests/reb/test_reentry_boundary.py::test_passive_discontinuity_audit"],
    "reb_queue": ["tests/reb/test_reentry_boundary.py::test_fake_reentry_queue"],
    "reb_proposal": ["tests/reb/test_reentry_boundary.py::test_authority_chain_fake_proposal"],
    "all": ["tests/reb", "tests/reb_batch_a"],
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


def run_reb_reentry_checks(workspace: Path) -> dict[str, object]:
    from hg_core.reb_cluster.errors import (
        REFUSED_CHECKPOINT_AUTHORITY,
        REFUSED_REENTRY_PACKET_AS_PERMISSION,
        REFUSED_REB_AS_AUTHORITY,
        REFUSED_REVOKED_PERMIT,
        REFUSED_STALE_APPROVAL,
        REFUSED_STALE_MEMORY_AS_CURRENT,
        RebValidationError,
    )
    from hg_core.reb_cluster.no_authority import check_reb_import_fences
    from hg_runtime.reentry_boundary import (
        FIXTURE_CLOCK,
        analyze_fixture_bundles,
        audit_discontinuity_events,
        enqueue_fixture_queue,
        load_fixture_bundles,
        refuse_reb_as_authority,
        refuse_reentry_packet_as_permission,
        route_reentry_bundle,
    )
    from hg_runtime.reentry_boundary.classifier import classify_gap_band, gap_seconds_from_duration
    from hg_runtime.reentry_boundary.fixtures import bundle_from_parts

    checks: list[dict[str, object]] = []

    fences_ok, fence_detail = check_reb_import_fences()
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
            "ok": analysis.get("all_advisory") is True and int(analysis.get("bundle_count", 0)) >= 12,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_fixture_bundles()
    one_hour = next(b for b in bundles if b["bundle_id"] == "reb-gap-1-hour")
    one_hour_result = route_reentry_bundle(one_hour, observed_at=FIXTURE_CLOCK)
    decision = one_hour_result.get("route", {}).get("reentry_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "one_hour_observe_only_after_freshness",
            "ok": isinstance(decision, dict) and decision.get("decision") == "allow_observe_only",
            "detail": decision.get("decision") if isinstance(decision, dict) else None,
        }
    )

    one_day = next(b for b in bundles if b["bundle_id"] == "reb-gap-1-day")
    one_day_result = route_reentry_bundle(one_day, observed_at=FIXTURE_CLOCK)
    one_day_decision = one_day_result.get("route", {}).get("reentry_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "one_day_requires_tim_refresh",
            "ok": isinstance(one_day_decision, dict)
            and one_day_decision.get("decision") == "require_TIM_refresh",
            "detail": one_day_decision.get("decision") if isinstance(one_day_decision, dict) else None,
        }
    )

    one_week = next(b for b in bundles if b["bundle_id"] == "reb-gap-1-week")
    one_week_result = route_reentry_bundle(one_week, observed_at=FIXTURE_CLOCK)
    one_week_decision = one_week_result.get("route", {}).get("reentry_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "one_week_requires_operator_review",
            "ok": isinstance(one_week_decision, dict)
            and one_week_decision.get("decision") == "require_operator_review",
            "detail": one_week_decision.get("decision") if isinstance(one_week_decision, dict) else None,
        }
    )

    one_month = next(b for b in bundles if b["bundle_id"] == "reb-gap-1-month")
    one_month_result = route_reentry_bundle(one_month, observed_at=FIXTURE_CLOCK)
    one_month_decision = one_month_result.get("route", {}).get("reentry_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "one_month_requires_ret_review",
            "ok": isinstance(one_month_decision, dict)
            and one_month_decision.get("decision") == "require_RET_review",
            "detail": one_month_decision.get("decision") if isinstance(one_month_decision, dict) else None,
        }
    )

    one_year = next(b for b in bundles if b["bundle_id"] == "reb-gap-1-year")
    one_year_result = route_reentry_bundle(one_year, observed_at=FIXTURE_CLOCK)
    one_year_decision = one_year_result.get("route", {}).get("reentry_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "one_year_requires_trb_cal_review",
            "ok": isinstance(one_year_decision, dict)
            and one_year_decision.get("decision") == "require_TRB_CAL_review",
            "detail": one_year_decision.get("decision") if isinstance(one_year_decision, dict) else None,
        }
    )

    fifty_year = next(b for b in bundles if b["bundle_id"] == "reb-gap-50-years")
    fifty_year_result = route_reentry_bundle(fifty_year, observed_at=FIXTURE_CLOCK)
    fifty_year_decision = fifty_year_result.get("route", {}).get("reentry_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "fifty_year_historical_artifact_denied",
            "ok": isinstance(fifty_year_decision, dict)
            and fifty_year_decision.get("decision") == "deny_reentry",
            "detail": fifty_year_decision.get("decision") if isinstance(fifty_year_decision, dict) else None,
        }
    )

    stale_approval = next(b for b in bundles if b["bundle_id"] == "reb-stale-approval")
    stale_result = route_reentry_bundle(stale_approval, observed_at=FIXTURE_CLOCK)
    stale_decision = stale_result.get("route", {}).get("reentry_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "stale_approval_refused",
            "ok": isinstance(stale_decision, dict) and stale_decision.get("decision") == "fail_closed",
            "detail": stale_decision.get("reason") if isinstance(stale_decision, dict) else None,
        }
    )

    revoked = next(b for b in bundles if b["bundle_id"] == "reb-revoked-permit")
    revoked_result = route_reentry_bundle(revoked, observed_at=FIXTURE_CLOCK)
    revoked_decision = revoked_result.get("route", {}).get("reentry_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "revoked_permit_refused",
            "ok": isinstance(revoked_decision, dict) and revoked_decision.get("decision") == "fail_closed",
            "detail": revoked_decision.get("reason") if isinstance(revoked_decision, dict) else None,
        }
    )

    checkpoint = next(b for b in bundles if b["bundle_id"] == "reb-checkpoint-authority")
    checkpoint_result = route_reentry_bundle(checkpoint, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "checkpoint_authority_refused",
            "ok": checkpoint_result.get("status") == "contained",
            "detail": checkpoint_result.get("status"),
        }
    )

    stale_memory = next(b for b in bundles if b["bundle_id"] == "reb-stale-memory")
    stale_mem_result = route_reentry_bundle(stale_memory, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "stale_memory_refused_as_current",
            "ok": stale_mem_result.get("status") == "contained",
            "detail": stale_mem_result.get("status"),
        }
    )

    packet_created = one_hour_result.get("route", {}).get("reentry_packet")  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "reentry_packet_created",
            "ok": isinstance(packet_created, dict)
            and packet_created.get("authority_created") is False
            and packet_created.get("permission_granted") is False,
            "detail": "packet_non_authority",
        }
    )

    reb_authority_refused = False
    try:
        refuse_reb_as_authority(treat_as_authority=True)
    except RebValidationError as exc:
        reb_authority_refused = exc.code == REFUSED_REB_AS_AUTHORITY
    checks.append(
        {
            "check_id": "reb_not_authority",
            "ok": reb_authority_refused,
            "detail": REFUSED_REB_AS_AUTHORITY,
        }
    )

    packet_refused = False
    try:
        refuse_reentry_packet_as_permission(treat_as_authority=True)
    except RebValidationError as exc:
        packet_refused = exc.code == REFUSED_REENTRY_PACKET_AS_PERMISSION
    checks.append(
        {
            "check_id": "reentry_packet_not_permission",
            "ok": packet_refused,
            "detail": REFUSED_REENTRY_PACKET_AS_PERMISSION,
        }
    )

    audit = audit_discontinuity_events(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "passive_discontinuity_audit",
            "ok": audit.get("passive_audit_only") is True and int(audit.get("event_count", 0)) >= 12,
            "detail": audit.get("event_count"),
        }
    )

    queue_result = enqueue_fixture_queue()
    checks.append(
        {
            "check_id": "fake_reentry_queue",
            "ok": queue_result.get("fake_queue_only") is True and int(queue_result.get("queue_depth", 0)) >= 3,
            "detail": queue_result.get("queue_depth"),
        }
    )

    proposal = one_hour_result.get("authority_chain_proposal")
    checks.append(
        {
            "check_id": "fake_authority_chain_proposal",
            "ok": isinstance(proposal, dict)
            and proposal.get("fake_dispatch_only") is True
            and proposal.get("proposal", {}).get("permit_minted") is False,  # type: ignore[union-attr]
            "detail": "fake_dispatch_only",
        }
    )

    gap_band_ok = classify_gap_band(gap_seconds_from_duration("P50Y")) == "over_50_years"
    checks.append(
        {
            "check_id": "long_gap_classifier_50_years",
            "ok": gap_band_ok,
            "detail": "over_50_years",
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
    }


def run_reb_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "reentry_boundary" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_reb_batch_a_checks(workspace, slice=slice)
    reentry_checks = run_reb_reentry_checks(workspace)
    combined = {
        "ok": batch_checks["ok"] and reentry_checks["ok"],
        "batch_checks": batch_checks,
        "reentry_checks": reentry_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(reentry_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "reb_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "reb_reentry_checks.json").write_text(
        json.dumps(reentry_checks, indent=2, sort_keys=True) + "\n",
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
        "slices": list(REB_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "reb_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "reb_reentry_checks",
                "verdict": "pass" if reentry_checks["ok"] else "fail",
                "ok": reentry_checks["ok"],
                "detail": reentry_checks,
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
                "pack": "REB-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"reentry_boundary/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/reb_batch_checks.json": sha256_file(artifacts_dir / "reb_batch_checks.json"),
                    "artifacts/reb_reentry_checks.json": sha256_file(artifacts_dir / "reb_reentry_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# REB-A Re-Entry Boundary — {slice} — {ts}",
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


__all__ = ["SLICE_TEST_TARGETS", "run_reb_a_gate", "run_reb_reentry_checks"]
