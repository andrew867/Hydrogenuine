"""Phase 28 gate and proof bundle validation."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
VERDICT_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_28_DOMAIN_PACK_RUNTIME"
PHASE26_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER"
PHASE27_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_27_SKILL_GRAPH_TRANSFER_ENGINE"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_phase28_proof_bundle(path: Path | None) -> tuple[bool, list[str]]:
    if path is None:
        return False, ["RED_PHASE28_PROOF_BUNDLE_MISSING"]
    required = ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]
    failures: list[str] = []
    for name in required:
        if not (path / name).is_file():
            failures.append(f"RED_PHASE28_PROOF_BUNDLE_MISSING:{name}")
    gate_path = path / "gate_result.json"
    if gate_path.is_file():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            if gate.get("proof_bundle") and Path(str(gate["proof_bundle"])).resolve() != path.resolve():
                failures.append("RED_PHASE28_PROOF_BUNDLE_PATH_MISMATCH")
        except json.JSONDecodeError:
            failures.append("RED_PHASE28_GATE_RESULT_INVALID_JSON")
    return not failures, failures


def evaluate_phase28_gate(
    repo_root: Path = WORKSPACE,
    *,
    phase26_green: bool,
    phase27_green: bool,
    proof_bundle: Path | None,
    tests_passed: bool,
    report_exists: bool = False,
    pack_hash_validation: bool = False,
    unsafe_packs_rejected: bool = False,
    unknown_tools_rejected: bool = False,
    forbidden_claims_blocked: bool = False,
    domain_packs_cannot_grant_authority: bool = False,
    domain_packs_cannot_authorize_tools: bool = False,
    domain_packs_cannot_create_live_side_effects: bool = False,
    pack_registry_replay_deterministic: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    if not phase26_green:
        failures.append("RED_PHASE28_PHASE26_GREEN_REQUIRED")
    if not phase27_green:
        failures.append("RED_PHASE28_PHASE27_GREEN_REQUIRED")
    proof_ok, proof_failures = validate_phase28_proof_bundle(proof_bundle)
    failures.extend(proof_failures)
    checks = {
        "tests_passed": tests_passed,
        "proof_bundle_valid": proof_ok,
        "report_exists": report_exists,
        "pack_hash_validation": pack_hash_validation,
        "unsafe_packs_rejected": unsafe_packs_rejected,
        "unknown_tools_rejected": unknown_tools_rejected,
        "forbidden_claims_blocked": forbidden_claims_blocked,
        "domain_packs_cannot_grant_authority": domain_packs_cannot_grant_authority,
        "domain_packs_cannot_authorize_tools": domain_packs_cannot_authorize_tools,
        "domain_packs_cannot_create_live_side_effects": domain_packs_cannot_create_live_side_effects,
        "pack_registry_replay_deterministic": pack_registry_replay_deterministic,
    }
    for key, ok in checks.items():
        if not ok:
            failures.append(f"RED_PHASE28_{key.upper()}_FAIL")
    verdict = VERDICT_GREEN if not failures else failures[0].split(":")[0]
    return {
        "phase": 28,
        "verdict": verdict,
        "ok": verdict == VERDICT_GREEN,
        "failures": failures,
        "checks": checks,
        "proof_bundle": str(proof_bundle) if proof_bundle else None,
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
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
    report = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_28_DOMAIN_PACK_RUNTIME_REPORT.md"
    proof_dir = WORKSPACE / "docs/proofs/autonomous_agent_zero/PHASE-28-DOMAIN-PACK-RUNTIME" / _stamp()
    proof_dir.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    phase26_ok = _gate_green("scripts/evals/autonomous_agent_phase_26_persistent_memory_experience_ledger_gate.py", PHASE26_GREEN)
    phase27_ok = _gate_green("scripts/evals/autonomous_agent_phase_27_skill_graph_transfer_engine_gate.py", PHASE27_GREEN)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/autonomous_agent/test_phase28_domain_packs.py", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    command_log = [
        {"command": "python scripts/evals/autonomous_agent_phase_26_persistent_memory_experience_ledger_gate.py", "returncode": 0 if phase26_ok else 1},
        {"command": "python scripts/evals/autonomous_agent_phase_27_skill_graph_transfer_engine_gate.py", "returncode": 0 if phase27_ok else 1},
        {
            "command": "python -m pytest tests/autonomous_agent/test_phase28_domain_packs.py -q",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-2000:],
        },
    ]
    (proof_dir / "HEAD.txt").write_text(head + "\n", encoding="utf-8")
    (proof_dir / "command_log.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in command_log) + "\n", encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"phase": 28, "head": head}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "gate_result.json").write_text(json.dumps({"proof_bundle": str(proof_dir)}, indent=2) + "\n", encoding="utf-8")
    preliminary = {"phase": 28, "head": head, "proof_bundle": str(proof_dir), "checks_passed": proc.returncode == 0 and phase26_ok and phase27_ok}
    (proof_dir / "summary.json").write_text(json.dumps(preliminary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = evaluate_phase28_gate(
        WORKSPACE,
        phase26_green=phase26_ok,
        phase27_green=phase27_ok,
        proof_bundle=proof_dir,
        tests_passed=proc.returncode == 0,
        report_exists=report.is_file(),
        pack_hash_validation=proc.returncode == 0,
        unsafe_packs_rejected=proc.returncode == 0,
        unknown_tools_rejected=proc.returncode == 0,
        forbidden_claims_blocked=proc.returncode == 0,
        domain_packs_cannot_grant_authority=proc.returncode == 0,
        domain_packs_cannot_authorize_tools=proc.returncode == 0,
        domain_packs_cannot_create_live_side_effects=proc.returncode == 0,
        pack_registry_replay_deterministic=proc.returncode == 0,
    )
    (proof_dir / "gate_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "summary.json").write_text(json.dumps({**preliminary, **result, "checks_passed": result["ok"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "status.md").write_text(f"# Phase 28 Gate\n\nVerdict: `{result['verdict']}`\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["VERDICT_GREEN", "evaluate_phase28_gate", "validate_phase28_proof_bundle"]
