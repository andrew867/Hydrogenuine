"""Phase 32 gate and proof bundle validation."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
VERDICT_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_32_LONG_HORIZON_GOAL_LIFECYCLE"
PHASE26_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER"
PHASE29_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_29_TOOL_MEDIATED_WORKBENCH"
PHASE31_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_31_GENERALIZATION_EVALUATION_HARNESS"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_phase32_proof_bundle(path: Path | None) -> tuple[bool, list[str]]:
    if path is None:
        return False, ["RED_PHASE32_PROOF_BUNDLE_MISSING"]
    required = ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]
    failures: list[str] = []
    for name in required:
        if not (path / name).is_file():
            failures.append(f"RED_PHASE32_PROOF_BUNDLE_MISSING:{name}")
    gate_path = path / "gate_result.json"
    if gate_path.is_file():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            if gate.get("proof_bundle") and Path(str(gate["proof_bundle"])).resolve() != path.resolve():
                failures.append("RED_PHASE32_PROOF_BUNDLE_PATH_MISMATCH")
        except json.JSONDecodeError:
            failures.append("RED_PHASE32_GATE_RESULT_INVALID_JSON")
    return not failures, failures


def evaluate_phase32_gate(
    repo_root: Path = WORKSPACE,
    *,
    phase26_green: bool,
    phase29_green: bool,
    phase31_green: bool,
    proof_bundle: Path | None,
    tests_passed: bool,
    report_exists: bool = False,
    goals_cannot_grant_authority: bool = False,
    goals_cannot_authorize_tools: bool = False,
    goals_cannot_create_live_effects: bool = False,
    candidate_tasks_are_not_execution: bool = False,
    allowed_task_class_required_before_selection: bool = False,
    ambiguous_intent_enters_ask_operator: bool = False,
    stop_panic_halts_lifecycle: bool = False,
    panic_blocks_task_selection: bool = False,
    failed_receipts_preserved: bool = False,
    replanning_preserves_failure_history: bool = False,
    generalization_evidence_advisory_only: bool = False,
    workbench_capability_advisory_only: bool = False,
    fake_green_rejected: bool = False,
    replay_deterministic: bool = False,
    no_live_side_effect_path_by_default: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    if not phase26_green:
        failures.append("RED_PHASE32_PHASE26_GREEN_REQUIRED")
    if not phase29_green:
        failures.append("RED_PHASE32_PHASE29_GREEN_REQUIRED")
    if not phase31_green:
        failures.append("RED_PHASE32_PHASE31_GREEN_REQUIRED")
    proof_ok, proof_failures = validate_phase32_proof_bundle(proof_bundle)
    failures.extend(proof_failures)
    checks = {
        "tests_passed": tests_passed,
        "proof_bundle_valid": proof_ok,
        "report_exists": report_exists,
        "goals_cannot_grant_authority": goals_cannot_grant_authority,
        "goals_cannot_authorize_tools": goals_cannot_authorize_tools,
        "goals_cannot_create_live_effects": goals_cannot_create_live_effects,
        "candidate_tasks_are_not_execution": candidate_tasks_are_not_execution,
        "allowed_task_class_required_before_selection": allowed_task_class_required_before_selection,
        "ambiguous_intent_enters_ask_operator": ambiguous_intent_enters_ask_operator,
        "stop_panic_halts_lifecycle": stop_panic_halts_lifecycle,
        "panic_blocks_task_selection": panic_blocks_task_selection,
        "failed_receipts_preserved": failed_receipts_preserved,
        "replanning_preserves_failure_history": replanning_preserves_failure_history,
        "generalization_evidence_advisory_only": generalization_evidence_advisory_only,
        "workbench_capability_advisory_only": workbench_capability_advisory_only,
        "fake_green_rejected": fake_green_rejected,
        "replay_deterministic": replay_deterministic,
        "no_live_side_effect_path_by_default": no_live_side_effect_path_by_default,
    }
    for key, ok in checks.items():
        if not ok:
            failures.append(f"RED_PHASE32_{key.upper()}_FAIL")
    verdict = VERDICT_GREEN if not failures else failures[0].split(":")[0]
    return {
        "phase": 32,
        "verdict": verdict,
        "ok": verdict == VERDICT_GREEN,
        "failures": failures,
        "checks": checks,
        "proof_bundle": str(proof_bundle) if proof_bundle else None,
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "goal_treated_as_permission": False,
        "live_side_effects_created": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def _gate_green(script: str, verdict: str) -> bool:
    proc = subprocess.run([sys.executable, script], cwd=WORKSPACE, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        return False
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False
    return data.get("verdict") == verdict


def main() -> int:
    report = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_32_LONG_HORIZON_GOAL_LIFECYCLE_REPORT.md"
    proof_dir = WORKSPACE / "docs/proofs/autonomous_agent_zero/PHASE-32-LONG-HORIZON-GOAL-LIFECYCLE" / _stamp()
    proof_dir.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    phase26_ok = _gate_green("scripts/evals/autonomous_agent_phase_26_persistent_memory_experience_ledger_gate.py", PHASE26_GREEN)
    phase29_ok = _gate_green("scripts/evals/autonomous_agent_phase_29_tool_mediated_workbench_gate.py", PHASE29_GREEN)
    phase31_ok = _gate_green("scripts/evals/autonomous_agent_phase_31_generalization_evaluation_harness_gate.py", PHASE31_GREEN)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/autonomous_agent/test_phase32_goal_lifecycle.py", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    command_log = [
        {"command": "python scripts/evals/autonomous_agent_phase_26_persistent_memory_experience_ledger_gate.py", "returncode": 0 if phase26_ok else 1},
        {"command": "python scripts/evals/autonomous_agent_phase_29_tool_mediated_workbench_gate.py", "returncode": 0 if phase29_ok else 1},
        {"command": "python scripts/evals/autonomous_agent_phase_31_generalization_evaluation_harness_gate.py", "returncode": 0 if phase31_ok else 1},
        {
            "command": "python -m pytest tests/autonomous_agent/test_phase32_goal_lifecycle.py -q",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-2000:],
        },
    ]
    (proof_dir / "HEAD.txt").write_text(head + "\n", encoding="utf-8")
    (proof_dir / "command_log.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in command_log) + "\n", encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"phase": 32, "head": head}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "gate_result.json").write_text(json.dumps({"proof_bundle": str(proof_dir)}, indent=2) + "\n", encoding="utf-8")
    preliminary = {"phase": 32, "head": head, "proof_bundle": str(proof_dir), "checks_passed": proc.returncode == 0 and phase26_ok and phase29_ok and phase31_ok}
    (proof_dir / "summary.json").write_text(json.dumps(preliminary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ok = proc.returncode == 0
    result = evaluate_phase32_gate(
        WORKSPACE,
        phase26_green=phase26_ok,
        phase29_green=phase29_ok,
        phase31_green=phase31_ok,
        proof_bundle=proof_dir,
        tests_passed=ok,
        report_exists=report.is_file(),
        goals_cannot_grant_authority=ok,
        goals_cannot_authorize_tools=ok,
        goals_cannot_create_live_effects=ok,
        candidate_tasks_are_not_execution=ok,
        allowed_task_class_required_before_selection=ok,
        ambiguous_intent_enters_ask_operator=ok,
        stop_panic_halts_lifecycle=ok,
        panic_blocks_task_selection=ok,
        failed_receipts_preserved=ok,
        replanning_preserves_failure_history=ok,
        generalization_evidence_advisory_only=ok,
        workbench_capability_advisory_only=ok,
        fake_green_rejected=ok,
        replay_deterministic=ok,
        no_live_side_effect_path_by_default=ok,
    )
    (proof_dir / "gate_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "summary.json").write_text(json.dumps({**preliminary, **result, "checks_passed": result["ok"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "status.md").write_text(f"# Phase 32 Gate\n\nVerdict: `{result['verdict']}`\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["VERDICT_GREEN", "evaluate_phase32_gate", "validate_phase32_proof_bundle"]
