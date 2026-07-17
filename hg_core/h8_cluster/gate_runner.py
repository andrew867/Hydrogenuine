"""Shared proof gate runner for H8 organism coherence."""

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


def run_h8_feature_checks() -> dict[str, object]:
    from hg_core.h8_cluster.config import (
        h8_refuse_authority_conversion,
        h8_refuse_live_model_invocation,
        h8_static_fixtures_only,
    )
    from hg_core.h8_cluster.events import planned_h8_event_refs
    from hg_core.h8_cluster.no_authority import check_h8_import_fences
    from hg_core.h8_cluster.rtc_design import validate_h8_rtc_event_design
    from hg_runtime.organism_coherence import (
        FIXTURE_CLOCK,
        analyze_organism_fixtures,
        load_organism_fixtures,
        process_organism_bundle,
        replay_fixture_stream,
    )
    from hg_runtime.organism_coherence.types import OrganismCoherenceReceipt, OrganismStateSummary

    checks: list[dict[str, object]] = []

    checks.append(
        {
            "check_id": "static_fixtures_only_default",
            "ok": h8_static_fixtures_only() and h8_refuse_live_model_invocation(),
            "detail": "fixture/static slice enforced by default",
        }
    )
    checks.append(
        {
            "check_id": "refuse_authority_conversion_default",
            "ok": h8_refuse_authority_conversion(),
            "detail": "authority conversion refusal enabled",
        }
    )

    rtc_ok, rtc_failures = validate_h8_rtc_event_design(planned_h8_event_refs())
    checks.append(
        {
            "check_id": "rtc_event_design",
            "ok": rtc_ok,
            "detail": rtc_failures if not rtc_ok else len(planned_h8_event_refs()),
        }
    )

    fences_ok, fence_detail = check_h8_import_fences()
    checks.append(
        {
            "check_id": "import_fences",
            "ok": fences_ok,
            "detail": fence_detail if not fences_ok else "clean",
        }
    )

    analysis = analyze_organism_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True
            and analysis.get("no_authority_created") is True
            and int(analysis.get("bundle_count", 0)) >= 12,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_organism_fixtures()

    valid_bundle = next(b for b in bundles if b["bundle_id"] == "h8-valid-coherence")
    valid_result = process_organism_bundle(valid_bundle, observed_at=FIXTURE_CLOCK)
    summary = valid_result.get("organism_state_summary")
    checks.append(
        {
            "check_id": "valid_organism_coherence",
            "ok": valid_result.get("status") == "recorded"
            and isinstance(summary, dict)
            and summary.get("coherence_status") == "coherent",
            "detail": summary.get("coherence_status") if isinstance(summary, dict) else None,
        }
    )

    missing_bundle = next(b for b in bundles if b["bundle_id"] == "h8-missing-organ")
    missing_result = process_organism_bundle(missing_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_organ_fail_closed",
            "ok": missing_result.get("status") == "fail_closed",
            "detail": missing_result.get("reason_code"),
        }
    )

    conflict_bundle = next(b for b in bundles if b["bundle_id"] == "h8-conflicting-organs")
    conflict_result = process_organism_bundle(conflict_bundle, observed_at=FIXTURE_CLOCK)
    routes = conflict_result.get("conflict_routes")
    checks.append(
        {
            "check_id": "conflicting_outputs_routed",
            "ok": conflict_result.get("status") == "conflict_routed"
            and isinstance(routes, list)
            and len(routes) >= 1,
            "detail": routes[0].get("route_target") if isinstance(routes, list) and routes else None,
        }
    )

    adversarial_ids = (
        "h8-naked-scalar",
        "h8-drb-as-permission",
        "h8-drb-as-memory",
        "h8-tep-as-authority",
        "h8-a0hm-as-authority",
        "h8-boundary-chain-launder",
        "h8-authority-conversion",
    )
    for bundle_id in adversarial_ids:
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_organism_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"adversarial_contained_{bundle_id}",
                "ok": result.get("status") == "contained" and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    stale_bundle = next(b for b in bundles if b["bundle_id"] == "h8-stale-approval")
    stale_result = process_organism_bundle(stale_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "stale_approval_fail_closed",
            "ok": stale_result.get("status") == "fail_closed",
            "detail": stale_result.get("reason_code"),
        }
    )

    receipt = valid_result.get("coherence_receipt")
    if isinstance(receipt, dict):
        checks.append(
            {
                "check_id": "receipt_negative_proofs",
                "ok": receipt.get("permit_minted") is False
                and receipt.get("oea_ter_called") is False
                and receipt.get("memory_history_mutated") is False
                and receipt.get("permission_granted") is False
                and receipt.get("authority_created") is False,
                "detail": "negative proofs pinned false",
            }
        )

    if isinstance(summary, dict):
        summary_obj = OrganismStateSummary(
            summary_id=str(summary["summary_id"]),
            organism_ref=str(summary["organism_ref"]),
            organ_refs=tuple(summary.get("organ_refs", ())),
            coherence_status=summary.get("coherence_status", "coherent"),  # type: ignore[arg-type]
            conflict_route_refs=tuple(summary.get("conflict_route_refs", ())),
            observed_at=str(summary.get("observed_at", FIXTURE_CLOCK)),
            notes=str(summary.get("notes", "")),
        )
        checks.append(
            {
                "check_id": "deterministic_summary_hash",
                "ok": summary_obj.record_hash == summary.get("record_hash"),
                "detail": summary_obj.record_hash[:16],
            }
        )

    if isinstance(receipt, dict):
        receipt_obj = OrganismCoherenceReceipt(
            receipt_id=str(receipt["receipt_id"]),
            organism_ref=str(receipt["organism_ref"]),
            summary_ref=str(receipt["summary_ref"]),
            module_receipt_refs=tuple(receipt.get("module_receipt_refs", ())),
            conflict_route_refs=tuple(receipt.get("conflict_route_refs", ())),
            emitted_events=tuple(receipt.get("emitted_events", ())),
        )
        checks.append(
            {
                "check_id": "deterministic_receipt_hash",
                "ok": receipt_obj.record_hash == receipt.get("record_hash"),
                "detail": receipt_obj.record_hash[:16],
            }
        )

    _, replay_hash = replay_fixture_stream(list(bundles[:5]), observed_at=FIXTURE_CLOCK)
    _, replay_hash_2 = replay_fixture_stream(list(bundles[:5]), observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "replay_determinism",
            "ok": replay_hash == replay_hash_2 and bool(replay_hash),
            "detail": replay_hash[:24],
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_h8_gate(workspace: Path, *, gate_id: str = "h8_organism_coherence_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "organism_coherence" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_h8_feature_checks()
    (artifacts_dir / "h8_feature_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = ["tests/h8"]
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
                "check": "h8_feature_checks",
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
                "pack": "H8",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "organism_coherence",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/h8_feature_checks.json": sha256_file(artifacts_dir / "h8_feature_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# H8 Organism Coherence — {ts}",
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
        print("H8 gate FAILED", file=sys.stderr)
        if test_cmd.stdout:
            print(test_cmd.stdout, file=sys.stderr)
        if test_cmd.stderr:
            print(test_cmd.stderr, file=sys.stderr)
        for failure in feature_checks.get("critical_failures", []):
            print(f"  critical: {failure}", file=sys.stderr)
        return 1
    print(f"H8 gate GREEN — proof bundle: {proof_dir}")
    return 0


__all__ = ["run_h8_feature_checks", "run_h8_gate"]
