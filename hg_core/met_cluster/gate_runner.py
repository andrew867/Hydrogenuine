"""Shared proof gate runner for MET metabolic governance."""

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


def run_met_feature_checks() -> dict[str, object]:
    from hg_core.met_cluster.config import (
        met_refuse_authority_conversion,
        met_refuse_live_model_invocation,
        met_static_fixtures_only,
    )
    from hg_core.met_cluster.events import planned_met_event_refs
    from hg_core.met_cluster.no_authority import check_met_import_fences
    from hg_core.met_cluster.rtc_design import validate_met_rtc_event_design
    from hg_runtime.metabolic_governance import (
        FIXTURE_CLOCK,
        MetabolicPosture,
        MetabolicReceipt,
        analyze_metabolic_fixtures,
        load_metabolic_fixtures,
        process_metabolic_bundle,
        replay_fixture_stream,
    )

    checks: list[dict[str, object]] = []

    checks.append(
        {
            "check_id": "static_fixtures_only_default",
            "ok": met_static_fixtures_only() and met_refuse_live_model_invocation(),
            "detail": "fixture/static slice enforced by default",
        }
    )
    checks.append(
        {
            "check_id": "refuse_authority_conversion_default",
            "ok": met_refuse_authority_conversion(),
            "detail": "authority conversion refusal enabled",
        }
    )

    rtc_ok, rtc_failures = validate_met_rtc_event_design(planned_met_event_refs())
    checks.append(
        {
            "check_id": "rtc_event_design",
            "ok": rtc_ok,
            "detail": rtc_failures if not rtc_ok else len(planned_met_event_refs()),
        }
    )

    fences_ok, fence_detail = check_met_import_fences()
    checks.append(
        {
            "check_id": "import_fences",
            "ok": fences_ok,
            "detail": fence_detail if not fences_ok else "clean",
        }
    )

    analysis = analyze_metabolic_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True
            and analysis.get("no_authority_created") is True
            and int(analysis.get("bundle_count", 0)) >= 12,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_metabolic_fixtures()

    valid_bundle = next(b for b in bundles if b["bundle_id"] == "met-valid-summary")
    valid_result = process_metabolic_bundle(valid_bundle, observed_at=FIXTURE_CLOCK)
    posture = valid_result.get("metabolic_posture")
    checks.append(
        {
            "check_id": "valid_metabolic_summary",
            "ok": valid_result.get("status") == "recorded"
            and isinstance(posture, dict)
            and posture.get("posture_level") in ("stable", "pressured"),
            "detail": posture.get("posture_level") if isinstance(posture, dict) else None,
        }
    )

    missing_bundle = next(b for b in bundles if b["bundle_id"] == "met-missing-organ")
    missing_result = process_metabolic_bundle(missing_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "missing_module_fail_closed",
            "ok": missing_result.get("status") == "fail_closed",
            "detail": missing_result.get("reason_code"),
        }
    )

    growth_bundle = next(b for b in bundles if b["bundle_id"] == "met-growth-proposal")
    growth_result = process_metabolic_bundle(growth_bundle, observed_at=FIXTURE_CLOCK)
    growth_proposals = growth_result.get("proposals")
    checks.append(
        {
            "check_id": "growth_request_remains_proposal",
            "ok": growth_result.get("status") == "recorded"
            and isinstance(growth_proposals, list)
            and all(p.get("status") == "proposal" for p in growth_proposals)
            and growth_result.get("permission_granted") is False,
            "detail": "proposal_only",
        }
    )

    waste_bundle = next(b for b in bundles if b["bundle_id"] == "met-waste-disposal-proposal")
    waste_result = process_metabolic_bundle(waste_bundle, observed_at=FIXTURE_CLOCK)
    waste_proposals = waste_result.get("proposals")
    checks.append(
        {
            "check_id": "waste_disposal_remains_proposal",
            "ok": waste_result.get("status") == "recorded"
            and isinstance(waste_proposals, list)
            and all(p.get("deletion_performed") is False for p in waste_proposals)
            and waste_result.get("permission_granted") is False,
            "detail": "proposal_only",
        }
    )

    tool_bundle = next(b for b in bundles if b["bundle_id"] == "met-tool-retirement-proposal")
    tool_result = process_metabolic_bundle(tool_bundle, observed_at=FIXTURE_CLOCK)
    tool_proposals = tool_result.get("proposals")
    checks.append(
        {
            "check_id": "tool_retirement_remains_proposal",
            "ok": tool_result.get("status") == "recorded"
            and isinstance(tool_proposals, list)
            and all(p.get("tool_removed") is False for p in tool_proposals)
            and tool_result.get("permission_granted") is False,
            "detail": "proposal_only",
        }
    )

    adversarial_ids = (
        "met-authority-conversion",
        "met-growth-as-grant",
        "met-waste-as-deletion",
        "met-tool-retirement-as-removal",
        "met-naked-scalar",
    )
    for bundle_id in adversarial_ids:
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_metabolic_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"adversarial_contained_{bundle_id}",
                "ok": result.get("status") == "contained" and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    stale_bundle = next(b for b in bundles if b["bundle_id"] == "met-stale-input")
    stale_result = process_metabolic_bundle(stale_bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "stale_input_fail_closed",
            "ok": stale_result.get("status") == "fail_closed",
            "detail": stale_result.get("reason_code"),
        }
    )

    receipt = valid_result.get("metabolic_receipt")
    if isinstance(receipt, dict):
        checks.append(
            {
                "check_id": "receipt_negative_proofs",
                "ok": receipt.get("permit_minted") is False
                and receipt.get("oea_ter_called") is False
                and receipt.get("memory_history_mutated") is False
                and receipt.get("permission_granted") is False
                and receipt.get("authority_created") is False
                and receipt.get("deletion_performed") is False
                and receipt.get("tool_removed") is False
                and receipt.get("agent_spawned") is False,
                "detail": "negative proofs pinned false",
            }
        )

    if isinstance(posture, dict):
        posture_obj = MetabolicPosture(
            posture_id=str(posture["posture_id"]),
            metabolism_ref=str(posture["metabolism_ref"]),
            organ_refs=tuple(posture.get("organ_refs", ())),
            posture_level=posture.get("posture_level", "stable"),  # type: ignore[arg-type]
            observed_at=str(posture.get("observed_at", FIXTURE_CLOCK)),
            notes=str(posture.get("notes", "")),
        )
        checks.append(
            {
                "check_id": "deterministic_posture_hash",
                "ok": posture_obj.record_hash == posture.get("record_hash"),
                "detail": posture_obj.record_hash[:16],
            }
        )

    if isinstance(receipt, dict):
        receipt_obj = MetabolicReceipt(
            receipt_id=str(receipt["receipt_id"]),
            metabolism_ref=str(receipt["metabolism_ref"]),
            posture_ref=str(receipt["posture_ref"]),
            organ_signal_refs=tuple(receipt.get("organ_signal_refs", ())),
            organ_route_refs=tuple(receipt.get("organ_route_refs", ())),
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


def run_met_gate(workspace: Path, *, gate_id: str = "met_metabolic_governance_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "metabolic_governance" / "MET" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_met_feature_checks()
    (artifacts_dir / "met_feature_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = ["tests/met"]
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
                "check": "met_feature_checks",
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
                "pack": "MET",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "metabolic_governance",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/met_feature_checks.json": sha256_file(artifacts_dir / "met_feature_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# MET Metabolic Governance — {ts}",
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
        print("MET gate FAILED", file=sys.stderr)
        if test_cmd.stdout:
            print(test_cmd.stdout, file=sys.stderr)
        if test_cmd.stderr:
            print(test_cmd.stderr, file=sys.stderr)
        for failure in feature_checks.get("critical_failures", []):
            print(f"  critical: {failure}", file=sys.stderr)
        return 1
    print(f"MET gate GREEN — proof bundle: {proof_dir}")
    return 0


__all__ = ["run_met_feature_checks", "run_met_gate"]
