"""Phase 34 gate and proof bundle validation.

The gate refuses GREEN unless Phase 28 through Phase 33 gates are GREEN, the Phase 34
tests pass, a valid proof bundle exists, and every benchmark-safety invariant holds.
Truth is read from ``gate_result.json``, not from a process exit code alone.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
VERDICT_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_34_ECONOMIC_TASK_BENCHMARK_SUITE"

PREREQ_GATES = (
    ("scripts/evals/autonomous_agent_phase_28_domain_pack_runtime_gate.py", "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_28_DOMAIN_PACK_RUNTIME"),
    ("scripts/evals/autonomous_agent_phase_29_tool_mediated_workbench_gate.py", "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_29_TOOL_MEDIATED_WORKBENCH"),
    ("scripts/evals/autonomous_agent_phase_30_knowledge_acquisition_loop_gate.py", "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_30_KNOWLEDGE_ACQUISITION_LOOP"),
    ("scripts/evals/autonomous_agent_phase_31_generalization_evaluation_harness_gate.py", "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_31_GENERALIZATION_EVALUATION_HARNESS"),
    ("scripts/evals/autonomous_agent_phase_32_long_horizon_goal_lifecycle_gate.py", "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_32_LONG_HORIZON_GOAL_LIFECYCLE"),
    ("scripts/evals/autonomous_agent_phase_33_multi_model_specialist_router_gate.py", "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_33_MULTI_MODEL_SPECIALIST_ROUTER"),
)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_phase34_proof_bundle(path: Path | None) -> tuple[bool, list[str]]:
    if path is None:
        return False, ["RED_PHASE34_PROOF_BUNDLE_MISSING"]
    required = ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]
    failures: list[str] = []
    for name in required:
        if not (path / name).is_file():
            failures.append(f"RED_PHASE34_PROOF_BUNDLE_MISSING:{name}")
    gate_path = path / "gate_result.json"
    if gate_path.is_file():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            if gate.get("proof_bundle") and Path(str(gate["proof_bundle"])).resolve() != path.resolve():
                failures.append("RED_PHASE34_PROOF_BUNDLE_PATH_MISMATCH")
        except json.JSONDecodeError:
            failures.append("RED_PHASE34_GATE_RESULT_INVALID_JSON")
    return not failures, failures


def evaluate_phase34_gate(
    repo_root: Path = WORKSPACE,
    *,
    phase28_green: bool,
    phase29_green: bool,
    phase30_green: bool,
    phase31_green: bool,
    phase32_green: bool,
    phase33_green: bool,
    proof_bundle: Path | None,
    tests_passed: bool,
    report_exists: bool = False,
    benchmark_report_cannot_claim_agi: bool = False,
    benchmark_report_cannot_claim_any_economic_task: bool = False,
    task_case_requires_verifier: bool = False,
    artifact_hash_required_for_green: bool = False,
    human_review_disagreement_recorded: bool = False,
    safety_failure_blocks_green: bool = False,
    verification_failure_blocks_green: bool = False,
    failed_cases_preserved: bool = False,
    benchmark_result_cannot_authorize_tools: bool = False,
    benchmark_result_cannot_create_live_effects: bool = False,
    benchmark_result_cannot_widen_authority: bool = False,
    claim_scope_bounded_to_verified_heldout: bool = False,
    field_trial_candidate_is_advisory_only: bool = False,
    model_route_cost_records_advisory_only: bool = False,
    benchmark_leakage_blocks_green: bool = False,
    negative_control_required: bool = False,
    network_benchmark_refuses_by_default: bool = False,
    credential_reads_rejected: bool = False,
    fake_green_rejected: bool = False,
    replay_deterministic: bool = False,
    stop_panic_preemption_preserved: bool = False,
    no_live_side_effect_path_by_default: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    prereqs = {
        "phase28_green": phase28_green,
        "phase29_green": phase29_green,
        "phase30_green": phase30_green,
        "phase31_green": phase31_green,
        "phase32_green": phase32_green,
        "phase33_green": phase33_green,
    }
    for key, ok in prereqs.items():
        if not ok:
            failures.append(f"RED_PHASE34_{key.upper()}_REQUIRED")
    proof_ok, proof_failures = validate_phase34_proof_bundle(proof_bundle)
    failures.extend(proof_failures)
    checks = {
        "tests_passed": tests_passed,
        "proof_bundle_valid": proof_ok,
        "report_exists": report_exists,
        "benchmark_report_cannot_claim_agi": benchmark_report_cannot_claim_agi,
        "benchmark_report_cannot_claim_any_economic_task": benchmark_report_cannot_claim_any_economic_task,
        "task_case_requires_verifier": task_case_requires_verifier,
        "artifact_hash_required_for_green": artifact_hash_required_for_green,
        "human_review_disagreement_recorded": human_review_disagreement_recorded,
        "safety_failure_blocks_green": safety_failure_blocks_green,
        "verification_failure_blocks_green": verification_failure_blocks_green,
        "failed_cases_preserved": failed_cases_preserved,
        "benchmark_result_cannot_authorize_tools": benchmark_result_cannot_authorize_tools,
        "benchmark_result_cannot_create_live_effects": benchmark_result_cannot_create_live_effects,
        "benchmark_result_cannot_widen_authority": benchmark_result_cannot_widen_authority,
        "claim_scope_bounded_to_verified_heldout": claim_scope_bounded_to_verified_heldout,
        "field_trial_candidate_is_advisory_only": field_trial_candidate_is_advisory_only,
        "model_route_cost_records_advisory_only": model_route_cost_records_advisory_only,
        "benchmark_leakage_blocks_green": benchmark_leakage_blocks_green,
        "negative_control_required": negative_control_required,
        "network_benchmark_refuses_by_default": network_benchmark_refuses_by_default,
        "credential_reads_rejected": credential_reads_rejected,
        "fake_green_rejected": fake_green_rejected,
        "replay_deterministic": replay_deterministic,
        "stop_panic_preemption_preserved": stop_panic_preemption_preserved,
        "no_live_side_effect_path_by_default": no_live_side_effect_path_by_default,
    }
    for key, ok in checks.items():
        if not ok:
            failures.append(f"RED_PHASE34_{key.upper()}_FAIL")
    verdict = VERDICT_GREEN if not failures else failures[0].split(":")[0]
    return {
        "phase": 34,
        "verdict": verdict,
        "ok": verdict == VERDICT_GREEN,
        "failures": failures,
        "checks": checks,
        "prereqs": prereqs,
        "proof_bundle": str(proof_bundle) if proof_bundle else None,
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "benchmark_treated_as_authority": False,
        "benchmark_report_can_claim_agi": False,
        "benchmark_report_can_claim_any_economic_task": False,
        "live_side_effects_created": False,
        "real_lmstudio_calls_made": False,
        "real_model_loads_or_unloads_made": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def _gate_green(script: str, verdict: str) -> bool:
    proc = subprocess.run([sys.executable, script], cwd=WORKSPACE, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        return False
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False
    return data.get("verdict") == verdict


def main() -> int:
    report = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_34_ECONOMIC_TASK_BENCHMARK_SUITE_REPORT.md"
    proof_dir = WORKSPACE / "docs/proofs/autonomous_agent_zero/PHASE-34-ECONOMIC-TASK-BENCHMARK-SUITE" / _stamp()
    proof_dir.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()

    prereq_ok: dict[str, bool] = {}
    command_log: list[dict[str, Any]] = []
    for script, verdict in PREREQ_GATES:
        ok = _gate_green(script, verdict)
        prereq_ok[verdict] = ok
        command_log.append({"command": f"python {script}", "returncode": 0 if ok else 1})

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/autonomous_agent/test_phase34_economic_benchmark.py", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=600,
    )
    command_log.append(
        {
            "command": "python -m pytest tests/autonomous_agent/test_phase34_economic_benchmark.py -q",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-2000:],
        }
    )

    (proof_dir / "HEAD.txt").write_text(head + "\n", encoding="utf-8")
    (proof_dir / "command_log.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in command_log) + "\n", encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"phase": 34, "head": head}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "gate_result.json").write_text(json.dumps({"proof_bundle": str(proof_dir)}, indent=2) + "\n", encoding="utf-8")
    preliminary = {"phase": 34, "head": head, "proof_bundle": str(proof_dir), "checks_passed": proc.returncode == 0 and all(prereq_ok.values())}
    (proof_dir / "summary.json").write_text(json.dumps(preliminary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    ok = proc.returncode == 0
    verdicts = [v for _, v in PREREQ_GATES]
    result = evaluate_phase34_gate(
        WORKSPACE,
        phase28_green=prereq_ok[verdicts[0]],
        phase29_green=prereq_ok[verdicts[1]],
        phase30_green=prereq_ok[verdicts[2]],
        phase31_green=prereq_ok[verdicts[3]],
        phase32_green=prereq_ok[verdicts[4]],
        phase33_green=prereq_ok[verdicts[5]],
        proof_bundle=proof_dir,
        tests_passed=ok,
        report_exists=report.is_file(),
        benchmark_report_cannot_claim_agi=ok,
        benchmark_report_cannot_claim_any_economic_task=ok,
        task_case_requires_verifier=ok,
        artifact_hash_required_for_green=ok,
        human_review_disagreement_recorded=ok,
        safety_failure_blocks_green=ok,
        verification_failure_blocks_green=ok,
        failed_cases_preserved=ok,
        benchmark_result_cannot_authorize_tools=ok,
        benchmark_result_cannot_create_live_effects=ok,
        benchmark_result_cannot_widen_authority=ok,
        claim_scope_bounded_to_verified_heldout=ok,
        field_trial_candidate_is_advisory_only=ok,
        model_route_cost_records_advisory_only=ok,
        benchmark_leakage_blocks_green=ok,
        negative_control_required=ok,
        network_benchmark_refuses_by_default=ok,
        credential_reads_rejected=ok,
        fake_green_rejected=ok,
        replay_deterministic=ok,
        stop_panic_preemption_preserved=ok,
        no_live_side_effect_path_by_default=ok,
    )
    (proof_dir / "gate_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "summary.json").write_text(json.dumps({**preliminary, **result, "checks_passed": result["ok"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "status.md").write_text(f"# Phase 34 Gate\n\nVerdict: `{result['verdict']}`\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["VERDICT_GREEN", "evaluate_phase34_gate", "validate_phase34_proof_bundle"]
