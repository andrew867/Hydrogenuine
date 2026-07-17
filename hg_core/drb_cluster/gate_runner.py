"""Shared proof gate runner for DRB dream reflection boundary."""

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


def run_drb_feature_checks() -> dict[str, object]:
    from hg_core.drb_cluster.config import (
        drb_refuse_authority_conversion,
        drb_refuse_live_model_invocation,
        drb_refuse_memory_mutation,
        drb_static_fixtures_only,
    )
    from hg_core.drb_cluster.no_authority import check_drb_import_fences
    from hg_core.drb_cluster.rtc_design import validate_drb_rtc_event_design
    from hg_core.drb_cluster.events import planned_drb_event_refs
    from hg_runtime.dream_reflection_boundary import (
        FIXTURE_CLOCK,
        analyze_fixture_bundles,
        load_fixture_bundles,
        process_reflection_bundle,
        replay_fixture_stream,
    )
    from hg_runtime.dream_reflection_boundary.types import CounterfactualScenario, DreamFragment

    checks: list[dict[str, object]] = []

    checks.append(
        {
            "check_id": "static_fixtures_only_default",
            "ok": drb_static_fixtures_only() and drb_refuse_live_model_invocation(),
            "detail": "fixture/static slice enforced by default",
        }
    )
    checks.append(
        {
            "check_id": "refuse_authority_conversion_default",
            "ok": drb_refuse_authority_conversion() and drb_refuse_memory_mutation(),
            "detail": "authority and memory mutation refusal enabled",
        }
    )

    rtc_ok, rtc_failures = validate_drb_rtc_event_design(planned_drb_event_refs())
    checks.append(
        {
            "check_id": "rtc_event_design",
            "ok": rtc_ok,
            "detail": rtc_failures if not rtc_ok else len(planned_drb_event_refs()),
        }
    )

    fences_ok, fence_detail = check_drb_import_fences()
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
            "ok": analysis.get("all_advisory") is True
            and analysis.get("no_memory_mutation") is True
            and int(analysis.get("bundle_count", 0)) >= 17,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_fixture_bundles()
    prior_bundle = next(b for b in bundles if b["bundle_id"] == "drb-prior-action")
    prior_result = process_reflection_bundle(prior_bundle, observed_at=FIXTURE_CLOCK)
    scenario = prior_result.get("counterfactual_scenario")
    checks.append(
        {
            "check_id": "prior_action_creates_counterfactual",
            "ok": isinstance(scenario, dict)
            and scenario.get("explicitly_counterfactual") is True
            and scenario.get("not_history") is True,
            "detail": scenario.get("scenario_type") if isinstance(scenario, dict) else None,
        }
    )

    possible_bundle = next(b for b in bundles if b["bundle_id"] == "drb-possible-action")
    possible_result = process_reflection_bundle(possible_bundle, observed_at=FIXTURE_CLOCK)
    fragments = possible_result.get("dream_fragments")
    checks.append(
        {
            "check_id": "possible_action_creates_fragment",
            "ok": isinstance(fragments, list) and len(fragments) >= 1,
            "detail": len(fragments) if isinstance(fragments, list) else 0,
        }
    )

    residue_bundle = next(b for b in bundles if b["bundle_id"] == "drb-residue")
    residue_result = process_reflection_bundle(residue_bundle, observed_at=FIXTURE_CLOCK)
    residue_fragments = residue_result.get("dream_fragments")
    route_ok = False
    if isinstance(residue_fragments, list) and residue_fragments:
        route_ok = residue_fragments[0].get("storage_policy") == "route_to_KAR"
    checks.append({"check_id": "residue_routes_kar", "ok": route_ok, "detail": "route_to_KAR"})

    obl_bundle = next(b for b in bundles if b["bundle_id"] == "drb-obligation")
    obl_result = process_reflection_bundle(obl_bundle, observed_at=FIXTURE_CLOCK)
    obl_fragments = obl_result.get("dream_fragments")
    obl_ok = False
    if isinstance(obl_fragments, list) and obl_fragments:
        obl_ok = obl_fragments[0].get("storage_policy") == "route_to_OBL"
    checks.append({"check_id": "obligation_routes_obl", "ok": obl_ok, "detail": "route_to_OBL"})

    risk_bundle = next(b for b in bundles if b["bundle_id"] == "drb-risk")
    risk_result = process_reflection_bundle(risk_bundle, observed_at=FIXTURE_CLOCK)
    risk_fragments = risk_result.get("dream_fragments")
    risk_ok = False
    if isinstance(risk_fragments, list) and risk_fragments:
        risk_ok = risk_fragments[0].get("storage_policy") == "route_to_RPB"
    checks.append({"check_id": "risk_routes_rpb", "ok": risk_ok, "detail": "route_to_RPB"})

    reentry_bundle = next(b for b in bundles if b["bundle_id"] == "drb-reentry-consolidation")
    reentry_result = process_reflection_bundle(reentry_bundle, observed_at=FIXTURE_CLOCK)
    consolidation = reentry_result.get("consolidation_decision")
    reentry_ok = False
    if isinstance(consolidation, dict):
        allowed = consolidation.get("allowed_effects", [])
        reentry_ok = isinstance(allowed, list) and any(
            r in allowed for r in ("route_to_CNT", "route_to_REB", "route_to_TIM", "route_to_ORI")
        )
    checks.append({"check_id": "reentry_routes_cnt_reb_tim", "ok": reentry_ok, "detail": allowed if reentry_ok else None})

    adversarial_ids = (
        "drb-scenario-as-history",
        "drb-fragment-as-memory",
        "drb-simulation-as-proof",
        "drb-better-outcome-revision",
        "drb-fragment-as-authority",
        "drb-simulated-operator-approval",
        "drb-simulated-consent",
        "drb-emotional-relief",
        "drb-full-episode",
        "drb-authority-conversion",
    )
    for bundle_id in adversarial_ids:
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_reflection_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"adversarial_contained_{bundle_id}",
                "ok": result.get("status") == "contained" and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    unknown_bundle = next(b for b in bundles if b["bundle_id"] == "drb-unknown")
    unknown_result = process_reflection_bundle(unknown_bundle, observed_at=FIXTURE_CLOCK)
    unknown_consolidation = unknown_result.get("consolidation_decision")
    checks.append(
        {
            "check_id": "unknown_reflection_fail_closed",
            "ok": unknown_result.get("status") == "fail_closed"
            and isinstance(unknown_consolidation, dict)
            and unknown_consolidation.get("decision") == "unknown_fail_closed",
            "detail": unknown_result.get("status"),
        }
    )

    receipt = prior_result.get("reflection_receipt")
    if isinstance(receipt, dict):
        checks.append(
            {
                "check_id": "receipt_negative_proofs",
                "ok": receipt.get("permit_minted") is False
                and receipt.get("oea_ter_called") is False
                and receipt.get("memory_history_mutated") is False
                and receipt.get("permission_granted") is False,
                "detail": "negative proofs pinned false",
            }
        )

    if isinstance(scenario, dict):
        scenario_obj = CounterfactualScenario(
            scenario_id=str(scenario["scenario_id"]),
            reflection_request_ref=str(scenario["reflection_request_ref"]),
            basis_refs=tuple(scenario.get("basis_refs", ())),
            scenario_type=scenario.get("scenario_type", "unknown"),  # type: ignore[arg-type]
            scenario_summary=str(scenario.get("scenario_summary", "")),
            confidence=float(scenario.get("confidence", 0.5)),
            ambiguity=float(scenario.get("ambiguity", 0.5)),
        )
        checks.append(
            {
                "check_id": "deterministic_scenario_hash",
                "ok": scenario_obj.record_hash == scenario.get("record_hash"),
                "detail": scenario_obj.record_hash[:16],
            }
        )

    if isinstance(fragments, list) and fragments:
        frag_payload = fragments[0]
        fragment_obj = DreamFragment(
            fragment_id=str(frag_payload["fragment_id"]),
            scenario_ref=str(frag_payload["scenario_ref"]),
            fragment_type=frag_payload.get("fragment_type", "warning"),  # type: ignore[arg-type]
            fragment_summary=str(frag_payload.get("fragment_summary", "")),
            source_refs=tuple(frag_payload.get("source_refs", ())),
            storage_policy=frag_payload.get("storage_policy", "ephemeral"),  # type: ignore[arg-type]
        )
        checks.append(
            {
                "check_id": "deterministic_fragment_hash",
                "ok": fragment_obj.record_hash == frag_payload.get("record_hash"),
                "detail": fragment_obj.record_hash[:16],
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


def run_drb_gate(workspace: Path, *, gate_id: str = "drb_dream_reflection_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "dream_reflection" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_drb_feature_checks()
    (artifacts_dir / "drb_feature_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = ["tests/drb"]
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
                "check": "drb_feature_checks",
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
                "pack": "DRB",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "dream_reflection",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/drb_feature_checks.json": sha256_file(artifacts_dir / "drb_feature_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# DRB Dream Reflection Boundary — {ts}",
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
        print("DRB gate FAILED", file=sys.stderr)
        if test_cmd.stdout:
            print(test_cmd.stdout, file=sys.stderr)
        if test_cmd.stderr:
            print(test_cmd.stderr, file=sys.stderr)
        for failure in feature_checks.get("critical_failures", []):
            print(f"  critical: {failure}", file=sys.stderr)
        return 1
    print(f"DRB gate GREEN — proof bundle: {proof_dir}")
    return 0


__all__ = ["run_drb_feature_checks", "run_drb_gate"]
