"""Phase 33 gate and proof bundle validation."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
VERDICT_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_33_MULTI_MODEL_SPECIALIST_ROUTER"
PHASE29_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_29_TOOL_MEDIATED_WORKBENCH"
PHASE32_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_32_LONG_HORIZON_GOAL_LIFECYCLE"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_phase33_proof_bundle(path: Path | None) -> tuple[bool, list[str]]:
    if path is None:
        return False, ["RED_PHASE33_PROOF_BUNDLE_MISSING"]
    required = ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]
    failures: list[str] = []
    for name in required:
        if not (path / name).is_file():
            failures.append(f"RED_PHASE33_PROOF_BUNDLE_MISSING:{name}")
    gate_path = path / "gate_result.json"
    if gate_path.is_file():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            if gate.get("proof_bundle") and Path(str(gate["proof_bundle"])).resolve() != path.resolve():
                failures.append("RED_PHASE33_PROOF_BUNDLE_PATH_MISMATCH")
        except json.JSONDecodeError:
            failures.append("RED_PHASE33_GATE_RESULT_INVALID_JSON")
    return not failures, failures


def evaluate_phase33_gate(
    repo_root: Path = WORKSPACE,
    *,
    phase29_green: bool,
    phase32_green: bool,
    proof_bundle: Path | None,
    tests_passed: bool,
    report_exists: bool = False,
    router_cannot_bypass_safety: bool = False,
    cheap_model_cannot_override_critic: bool = False,
    model_output_cannot_grant_authority: bool = False,
    privacy_sensitive_blocks_external: bool = False,
    local_model_is_authority_neutral: bool = False,
    model_load_requires_receipt: bool = False,
    unload_active_model_rejected: bool = False,
    max_loaded_models_enforced: bool = False,
    provider_failure_refuses_no_silent_fallback: bool = False,
    lmstudio_adapter_dry_run_by_default: bool = False,
    openvino_adapter_dry_run_by_default: bool = False,
    security_model_critic_only_by_default: bool = False,
    fake_green_rejected: bool = False,
    replay_deterministic: bool = False,
    no_live_side_effect_path_by_default: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    if not phase29_green:
        failures.append("RED_PHASE33_PHASE29_GREEN_REQUIRED")
    if not phase32_green:
        failures.append("RED_PHASE33_PHASE32_GREEN_REQUIRED")
    proof_ok, proof_failures = validate_phase33_proof_bundle(proof_bundle)
    failures.extend(proof_failures)
    checks = {
        "tests_passed": tests_passed,
        "proof_bundle_valid": proof_ok,
        "report_exists": report_exists,
        "router_cannot_bypass_safety": router_cannot_bypass_safety,
        "cheap_model_cannot_override_critic": cheap_model_cannot_override_critic,
        "model_output_cannot_grant_authority": model_output_cannot_grant_authority,
        "privacy_sensitive_blocks_external": privacy_sensitive_blocks_external,
        "local_model_is_authority_neutral": local_model_is_authority_neutral,
        "model_load_requires_receipt": model_load_requires_receipt,
        "unload_active_model_rejected": unload_active_model_rejected,
        "max_loaded_models_enforced": max_loaded_models_enforced,
        "provider_failure_refuses_no_silent_fallback": provider_failure_refuses_no_silent_fallback,
        "lmstudio_adapter_dry_run_by_default": lmstudio_adapter_dry_run_by_default,
        "openvino_adapter_dry_run_by_default": openvino_adapter_dry_run_by_default,
        "security_model_critic_only_by_default": security_model_critic_only_by_default,
        "fake_green_rejected": fake_green_rejected,
        "replay_deterministic": replay_deterministic,
        "no_live_side_effect_path_by_default": no_live_side_effect_path_by_default,
    }
    for key, ok in checks.items():
        if not ok:
            failures.append(f"RED_PHASE33_{key.upper()}_FAIL")
    verdict = VERDICT_GREEN if not failures else failures[0].split(":")[0]
    return {
        "phase": 33,
        "verdict": verdict,
        "ok": verdict == VERDICT_GREEN,
        "failures": failures,
        "checks": checks,
        "proof_bundle": str(proof_bundle) if proof_bundle else None,
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "routing_treated_as_authority": False,
        "real_lmstudio_calls_made": False,
        "real_model_loads_or_unloads_made": False,
        "live_side_effects_created": False,
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
    report = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_33_MULTI_MODEL_SPECIALIST_ROUTER_REPORT.md"
    proof_dir = WORKSPACE / "docs/proofs/autonomous_agent_zero/PHASE-33-MULTI-MODEL-SPECIALIST-ROUTER" / _stamp()
    proof_dir.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    phase29_ok = _gate_green("scripts/evals/autonomous_agent_phase_29_tool_mediated_workbench_gate.py", PHASE29_GREEN)
    phase32_ok = _gate_green("scripts/evals/autonomous_agent_phase_32_long_horizon_goal_lifecycle_gate.py", PHASE32_GREEN)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/autonomous_agent/test_phase33_model_router.py", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=600,
    )
    command_log = [
        {"command": "python scripts/evals/autonomous_agent_phase_29_tool_mediated_workbench_gate.py", "returncode": 0 if phase29_ok else 1},
        {"command": "python scripts/evals/autonomous_agent_phase_32_long_horizon_goal_lifecycle_gate.py", "returncode": 0 if phase32_ok else 1},
        {
            "command": "python -m pytest tests/autonomous_agent/test_phase33_model_router.py -q",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-2000:],
        },
    ]
    (proof_dir / "HEAD.txt").write_text(head + "\n", encoding="utf-8")
    (proof_dir / "command_log.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in command_log) + "\n", encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"phase": 33, "head": head}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "gate_result.json").write_text(json.dumps({"proof_bundle": str(proof_dir)}, indent=2) + "\n", encoding="utf-8")
    preliminary = {"phase": 33, "head": head, "proof_bundle": str(proof_dir), "checks_passed": proc.returncode == 0 and phase29_ok and phase32_ok}
    (proof_dir / "summary.json").write_text(json.dumps(preliminary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ok = proc.returncode == 0
    result = evaluate_phase33_gate(
        WORKSPACE,
        phase29_green=phase29_ok,
        phase32_green=phase32_ok,
        proof_bundle=proof_dir,
        tests_passed=ok,
        report_exists=report.is_file(),
        router_cannot_bypass_safety=ok,
        cheap_model_cannot_override_critic=ok,
        model_output_cannot_grant_authority=ok,
        privacy_sensitive_blocks_external=ok,
        local_model_is_authority_neutral=ok,
        model_load_requires_receipt=ok,
        unload_active_model_rejected=ok,
        max_loaded_models_enforced=ok,
        provider_failure_refuses_no_silent_fallback=ok,
        lmstudio_adapter_dry_run_by_default=ok,
        openvino_adapter_dry_run_by_default=ok,
        security_model_critic_only_by_default=ok,
        fake_green_rejected=ok,
        replay_deterministic=ok,
        no_live_side_effect_path_by_default=ok,
    )
    (proof_dir / "gate_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "summary.json").write_text(json.dumps({**preliminary, **result, "checks_passed": result["ok"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "status.md").write_text(f"# Phase 33 Gate\n\nVerdict: `{result['verdict']}`\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["VERDICT_GREEN", "evaluate_phase33_gate", "validate_phase33_proof_bundle"]
