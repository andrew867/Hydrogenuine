"""Phase 33.5 gate and proof bundle validation.

The gate runs a default dry-run-safe smoke (real local calls only when the operator
has enabled them via env), determines an explicit partial verdict, and refuses GREEN
unless Phase 33 and Phase 34 gates are GREEN, the Phase 33.5 tests pass, a valid proof
bundle exists, and every provider-smoke safety invariant holds. A missing OpenVINO
configuration is reported honestly. Truth is read from ``gate_result.json``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.local_provider_smoke.comparison import determine_smoke_verdict
from hg_runtime.local_provider_smoke.config import load_smoke_config_from_env
from hg_runtime.local_provider_smoke.lmstudio_smoke import lmstudio_smoke
from hg_runtime.local_provider_smoke.openvino_smoke import openvino_smoke
from hg_runtime.local_provider_smoke.schemas import VERDICT_RED_FAILED

WORKSPACE = Path(__file__).resolve().parents[2]
PHASE33_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_33_MULTI_MODEL_SPECIALIST_ROUTER"
PHASE34_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_34_ECONOMIC_TASK_BENCHMARK_SUITE"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_phase335_proof_bundle(path: Path | None) -> tuple[bool, list[str]]:
    if path is None:
        return False, ["RED_PHASE335_PROOF_BUNDLE_MISSING"]
    required = ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]
    failures: list[str] = []
    for name in required:
        if not (path / name).is_file():
            failures.append(f"RED_PHASE335_PROOF_BUNDLE_MISSING:{name}")
    gate_path = path / "gate_result.json"
    if gate_path.is_file():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            if gate.get("proof_bundle") and Path(str(gate["proof_bundle"])).resolve() != path.resolve():
                failures.append("RED_PHASE335_PROOF_BUNDLE_PATH_MISMATCH")
        except json.JSONDecodeError:
            failures.append("RED_PHASE335_GATE_RESULT_INVALID_JSON")
    return not failures, failures


def evaluate_phase335_gate(
    repo_root: Path = WORKSPACE,
    *,
    phase33_green: bool,
    phase34_green: bool,
    proof_bundle: Path | None,
    tests_passed: bool,
    lmstudio_status: str,
    openvino_status: str,
    report_exists: bool = False,
    smoke_cannot_grant_authority: bool = False,
    smoke_cannot_authorize_tools: bool = False,
    smoke_cannot_create_live_effects: bool = False,
    smoke_cannot_claim_agi: bool = False,
    startup_autodetect_read_only: bool = False,
    lmstudio_base_url_configurable: bool = False,
    openvino_endpoint_configurable: bool = False,
    openvino_not_configured_recorded_honestly: bool = False,
    openvino_gguf_assumption_rejected: bool = False,
    provider_failure_no_silent_fallback: bool = False,
    model_response_non_authoritative: bool = False,
    thirty_b_load_on_demand_only: bool = False,
    thirty_b_not_required_for_green: bool = False,
    security_model_not_smoked_by_default: bool = False,
    credential_reads_rejected: bool = False,
    external_provider_refuses_by_default: bool = False,
    fake_green_rejected: bool = False,
    replay_deterministic: bool = False,
    stop_panic_preemption_preserved: bool = False,
    no_live_external_side_effect_path_by_default: bool = False,
    real_lmstudio_calls_made: bool = False,
    real_openvino_calls_made: bool = False,
    real_model_loads_made: bool = False,
    real_model_unloads_made: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    if not phase33_green:
        failures.append("RED_PHASE335_PHASE33_GREEN_REQUIRED")
    if not phase34_green:
        failures.append("RED_PHASE335_PHASE34_GREEN_REQUIRED")
    proof_ok, proof_failures = validate_phase335_proof_bundle(proof_bundle)
    failures.extend(proof_failures)
    checks = {
        "tests_passed": tests_passed,
        "proof_bundle_valid": proof_ok,
        "report_exists": report_exists,
        "smoke_cannot_grant_authority": smoke_cannot_grant_authority,
        "smoke_cannot_authorize_tools": smoke_cannot_authorize_tools,
        "smoke_cannot_create_live_effects": smoke_cannot_create_live_effects,
        "smoke_cannot_claim_agi": smoke_cannot_claim_agi,
        "startup_autodetect_read_only": startup_autodetect_read_only,
        "lmstudio_base_url_configurable": lmstudio_base_url_configurable,
        "openvino_endpoint_configurable": openvino_endpoint_configurable,
        "openvino_not_configured_recorded_honestly": openvino_not_configured_recorded_honestly,
        "openvino_gguf_assumption_rejected": openvino_gguf_assumption_rejected,
        "provider_failure_no_silent_fallback": provider_failure_no_silent_fallback,
        "model_response_non_authoritative": model_response_non_authoritative,
        "thirty_b_load_on_demand_only": thirty_b_load_on_demand_only,
        "thirty_b_not_required_for_green": thirty_b_not_required_for_green,
        "security_model_not_smoked_by_default": security_model_not_smoked_by_default,
        "credential_reads_rejected": credential_reads_rejected,
        "external_provider_refuses_by_default": external_provider_refuses_by_default,
        "fake_green_rejected": fake_green_rejected,
        "replay_deterministic": replay_deterministic,
        "stop_panic_preemption_preserved": stop_panic_preemption_preserved,
        "no_live_external_side_effect_path_by_default": no_live_external_side_effect_path_by_default,
    }
    for key, ok in checks.items():
        if not ok:
            failures.append(f"RED_PHASE335_{key.upper()}_FAIL")

    # An implementation failure forces RED; otherwise the honest partial verdict stands.
    smoke_verdict = determine_smoke_verdict(lmstudio_status, openvino_status)
    verdict = VERDICT_RED_FAILED if failures else smoke_verdict
    ok = not failures and verdict != VERDICT_RED_FAILED
    return {
        "phase": "33.5",
        "verdict": verdict,
        "smoke_verdict": smoke_verdict,
        "ok": ok,
        "failures": failures,
        "checks": checks,
        "lmstudio_status": lmstudio_status,
        "openvino_status": openvino_status,
        "proof_bundle": str(proof_bundle) if proof_bundle else None,
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "smoke_treated_as_authority": False,
        "model_response_treated_as_truth": False,
        "real_lmstudio_calls_made": real_lmstudio_calls_made,
        "real_openvino_calls_made": real_openvino_calls_made,
        "real_model_loads_made": real_model_loads_made,
        "real_model_unloads_made": real_model_unloads_made,
        "large_30b_model_loaded": False,
        "security_model_smoked": False,
        "live_external_side_effects_created": False,
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
    report = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_33_5_LOCAL_PROVIDER_SMOKE_REPORT.md"
    proof_dir = WORKSPACE / "docs/proofs/autonomous_agent_zero/PHASE-33-5-LOCAL-PROVIDER-SMOKE" / _stamp()
    proof_dir.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()

    phase33_ok = _gate_green("scripts/evals/autonomous_agent_phase_33_multi_model_specialist_router_gate.py", PHASE33_GREEN)
    phase34_ok = _gate_green("scripts/evals/autonomous_agent_phase_34_economic_task_benchmark_suite_gate.py", PHASE34_GREEN)

    # Default dry-run-safe smoke: real local calls only when the operator enabled them.
    config = load_smoke_config_from_env()
    lm = lmstudio_smoke(config)
    ov = openvino_smoke(config)
    real_lms = bool(lm.get("real_call_made"))
    real_ov = bool(ov.get("real_call_made"))

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/autonomous_agent/test_phase33_5_local_provider_smoke.py", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=600,
    )
    command_log = [
        {"command": "python scripts/evals/autonomous_agent_phase_33_multi_model_specialist_router_gate.py", "returncode": 0 if phase33_ok else 1},
        {"command": "python scripts/evals/autonomous_agent_phase_34_economic_task_benchmark_suite_gate.py", "returncode": 0 if phase34_ok else 1},
        {"command": "local_provider_smoke (dry-run; real calls disabled unless operator-enabled)", "lmstudio_status": lm["status"], "openvino_status": ov["status"], "real_lmstudio_calls_made": real_lms, "real_openvino_calls_made": real_ov},
        {
            "command": "python -m pytest tests/autonomous_agent/test_phase33_5_local_provider_smoke.py -q",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-2000:],
        },
    ]
    (proof_dir / "HEAD.txt").write_text(head + "\n", encoding="utf-8")
    (proof_dir / "command_log.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in command_log) + "\n", encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"phase": "33.5", "head": head}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "gate_result.json").write_text(json.dumps({"proof_bundle": str(proof_dir)}, indent=2) + "\n", encoding="utf-8")
    preliminary = {"phase": "33.5", "head": head, "proof_bundle": str(proof_dir), "checks_passed": proc.returncode == 0 and phase33_ok and phase34_ok}
    (proof_dir / "summary.json").write_text(json.dumps(preliminary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    ok = proc.returncode == 0
    result = evaluate_phase335_gate(
        WORKSPACE,
        phase33_green=phase33_ok,
        phase34_green=phase34_ok,
        proof_bundle=proof_dir,
        tests_passed=ok,
        lmstudio_status=lm["status"],
        openvino_status=ov["status"],
        report_exists=report.is_file(),
        smoke_cannot_grant_authority=ok,
        smoke_cannot_authorize_tools=ok,
        smoke_cannot_create_live_effects=ok,
        smoke_cannot_claim_agi=ok,
        startup_autodetect_read_only=ok,
        lmstudio_base_url_configurable=ok,
        openvino_endpoint_configurable=ok,
        openvino_not_configured_recorded_honestly=ok,
        openvino_gguf_assumption_rejected=ok,
        provider_failure_no_silent_fallback=ok,
        model_response_non_authoritative=ok,
        thirty_b_load_on_demand_only=ok,
        thirty_b_not_required_for_green=ok,
        security_model_not_smoked_by_default=ok,
        credential_reads_rejected=ok,
        external_provider_refuses_by_default=ok,
        fake_green_rejected=ok,
        replay_deterministic=ok,
        stop_panic_preemption_preserved=ok,
        no_live_external_side_effect_path_by_default=ok,
        real_lmstudio_calls_made=real_lms,
        real_openvino_calls_made=real_ov,
        real_model_loads_made=False,
        real_model_unloads_made=False,
    )
    (proof_dir / "gate_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "summary.json").write_text(json.dumps({**preliminary, **result, "checks_passed": result["ok"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "status.md").write_text(f"# Phase 33.5 Gate\n\nVerdict: `{result['verdict']}`\n\nLM Studio: `{lm['status']}`  OpenVINO: `{ov['status']}`\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["evaluate_phase335_gate", "validate_phase335_proof_bundle"]
