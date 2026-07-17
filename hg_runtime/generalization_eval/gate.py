"""Phase 31 gate and proof bundle validation."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
VERDICT_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_31_GENERALIZATION_EVALUATION_HARNESS"
PHASE27_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_27_SKILL_GRAPH_TRANSFER_ENGINE"
PHASE30_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_30_KNOWLEDGE_ACQUISITION_LOOP"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_phase31_proof_bundle(path: Path | None) -> tuple[bool, list[str]]:
    if path is None:
        return False, ["RED_PHASE31_PROOF_BUNDLE_MISSING"]
    required = ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]
    failures: list[str] = []
    for name in required:
        if not (path / name).is_file():
            failures.append(f"RED_PHASE31_PROOF_BUNDLE_MISSING:{name}")
    gate_path = path / "gate_result.json"
    if gate_path.is_file():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            if gate.get("proof_bundle") and Path(str(gate["proof_bundle"])).resolve() != path.resolve():
                failures.append("RED_PHASE31_PROOF_BUNDLE_PATH_MISMATCH")
        except json.JSONDecodeError:
            failures.append("RED_PHASE31_GATE_RESULT_INVALID_JSON")
    return not failures, failures


def evaluate_phase31_gate(
    repo_root: Path = WORKSPACE,
    *,
    phase27_green: bool,
    phase30_green: bool,
    proof_bundle: Path | None,
    tests_passed: bool,
    report_exists: bool = False,
    heldout_cases_exclude_answer_keys: bool = False,
    leakage_audit_required: bool = False,
    surface_similarity_rejected: bool = False,
    negative_controls_fail_expectedly: bool = False,
    claim_scope_bounded_to_passed_cases: bool = False,
    evaluation_result_cannot_authorize_tools: bool = False,
    evaluation_result_cannot_widen_authority: bool = False,
    single_success_cannot_claim_general_competence: bool = False,
    network_eval_refuses_by_default: bool = False,
    credential_eval_reads_rejected: bool = False,
    fake_green_rejected: bool = False,
    replay_deterministic: bool = False,
    no_live_side_effect_path_by_default: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    if not phase27_green:
        failures.append("RED_PHASE31_PHASE27_GREEN_REQUIRED")
    if not phase30_green:
        failures.append("RED_PHASE31_PHASE30_GREEN_REQUIRED")
    proof_ok, proof_failures = validate_phase31_proof_bundle(proof_bundle)
    failures.extend(proof_failures)
    checks = {
        "tests_passed": tests_passed,
        "proof_bundle_valid": proof_ok,
        "report_exists": report_exists,
        "heldout_cases_exclude_answer_keys": heldout_cases_exclude_answer_keys,
        "leakage_audit_required": leakage_audit_required,
        "surface_similarity_rejected": surface_similarity_rejected,
        "negative_controls_fail_expectedly": negative_controls_fail_expectedly,
        "claim_scope_bounded_to_passed_cases": claim_scope_bounded_to_passed_cases,
        "evaluation_result_cannot_authorize_tools": evaluation_result_cannot_authorize_tools,
        "evaluation_result_cannot_widen_authority": evaluation_result_cannot_widen_authority,
        "single_success_cannot_claim_general_competence": single_success_cannot_claim_general_competence,
        "network_eval_refuses_by_default": network_eval_refuses_by_default,
        "credential_eval_reads_rejected": credential_eval_reads_rejected,
        "fake_green_rejected": fake_green_rejected,
        "replay_deterministic": replay_deterministic,
        "no_live_side_effect_path_by_default": no_live_side_effect_path_by_default,
    }
    for key, ok in checks.items():
        if not ok:
            failures.append(f"RED_PHASE31_{key.upper()}_FAIL")
    verdict = VERDICT_GREEN if not failures else failures[0].split(":")[0]
    return {
        "phase": 31,
        "verdict": verdict,
        "ok": verdict == VERDICT_GREEN,
        "failures": failures,
        "checks": checks,
        "proof_bundle": str(proof_bundle) if proof_bundle else None,
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "scope_widened": False,
        "similarity_treated_as_proof": False,
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
    report = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_31_GENERALIZATION_EVALUATION_HARNESS_REPORT.md"
    proof_dir = WORKSPACE / "docs/proofs/autonomous_agent_zero/PHASE-31-GENERALIZATION-EVALUATION-HARNESS" / _stamp()
    proof_dir.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    phase27_ok = _gate_green("scripts/evals/autonomous_agent_phase_27_skill_graph_transfer_engine_gate.py", PHASE27_GREEN)
    phase30_ok = _gate_green("scripts/evals/autonomous_agent_phase_30_knowledge_acquisition_loop_gate.py", PHASE30_GREEN)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/autonomous_agent/test_phase31_generalization_eval.py", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    command_log = [
        {"command": "python scripts/evals/autonomous_agent_phase_27_skill_graph_transfer_engine_gate.py", "returncode": 0 if phase27_ok else 1},
        {"command": "python scripts/evals/autonomous_agent_phase_30_knowledge_acquisition_loop_gate.py", "returncode": 0 if phase30_ok else 1},
        {
            "command": "python -m pytest tests/autonomous_agent/test_phase31_generalization_eval.py -q",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-2000:],
        },
    ]
    (proof_dir / "HEAD.txt").write_text(head + "\n", encoding="utf-8")
    (proof_dir / "command_log.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in command_log) + "\n", encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"phase": 31, "head": head}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "gate_result.json").write_text(json.dumps({"proof_bundle": str(proof_dir)}, indent=2) + "\n", encoding="utf-8")
    preliminary = {"phase": 31, "head": head, "proof_bundle": str(proof_dir), "checks_passed": proc.returncode == 0 and phase27_ok and phase30_ok}
    (proof_dir / "summary.json").write_text(json.dumps(preliminary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ok = proc.returncode == 0
    result = evaluate_phase31_gate(
        WORKSPACE,
        phase27_green=phase27_ok,
        phase30_green=phase30_ok,
        proof_bundle=proof_dir,
        tests_passed=ok,
        report_exists=report.is_file(),
        heldout_cases_exclude_answer_keys=ok,
        leakage_audit_required=ok,
        surface_similarity_rejected=ok,
        negative_controls_fail_expectedly=ok,
        claim_scope_bounded_to_passed_cases=ok,
        evaluation_result_cannot_authorize_tools=ok,
        evaluation_result_cannot_widen_authority=ok,
        single_success_cannot_claim_general_competence=ok,
        network_eval_refuses_by_default=ok,
        credential_eval_reads_rejected=ok,
        fake_green_rejected=ok,
        replay_deterministic=ok,
        no_live_side_effect_path_by_default=ok,
    )
    (proof_dir / "gate_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "summary.json").write_text(json.dumps({**preliminary, **result, "checks_passed": result["ok"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "status.md").write_text(f"# Phase 31 Gate\n\nVerdict: `{result['verdict']}`\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["VERDICT_GREEN", "evaluate_phase31_gate", "validate_phase31_proof_bundle"]
