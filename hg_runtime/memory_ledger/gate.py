"""Phase 26 gate and proof-bundle validation."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
VERDICT_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_phase26_proof_bundle(path: Path | None) -> tuple[bool, list[str]]:
    if path is None:
        return False, ["RED_PHASE26_PROOF_BUNDLE_MISSING"]
    required = ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]
    failures: list[str] = []
    for name in required:
        if not (path / name).is_file():
            failures.append(f"RED_PHASE26_PROOF_BUNDLE_MISSING:{name}")
    if (path / "gate_result.json").is_file():
        try:
            gate = json.loads((path / "gate_result.json").read_text(encoding="utf-8"))
            if gate.get("proof_bundle"):
                recorded = Path(str(gate["proof_bundle"]))
                if recorded.resolve() != path.resolve():
                    failures.append("RED_PHASE26_PROOF_BUNDLE_PATH_MISMATCH")
        except json.JSONDecodeError:
            failures.append("RED_PHASE26_GATE_RESULT_INVALID_JSON")
    return not failures, failures


def evaluate_phase26_gate(
    repo_root: Path = WORKSPACE,
    *,
    proof_bundle: Path | None,
    tests_passed: bool,
    report_exists: bool = False,
    replay_deterministic: bool = False,
    receipt_required_for_learning: bool = False,
    memory_cannot_grant_authority: bool = False,
    memory_cannot_authorize_tools: bool = False,
    memory_cannot_create_live_effects: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    proof_ok, proof_failures = validate_phase26_proof_bundle(proof_bundle)
    failures.extend(proof_failures)
    checks = {
        "tests_passed": tests_passed,
        "proof_bundle_valid": proof_ok,
        "report_exists": report_exists,
        "replay_deterministic": replay_deterministic,
        "receipt_required_for_learning": receipt_required_for_learning,
        "memory_cannot_grant_authority": memory_cannot_grant_authority,
        "memory_cannot_authorize_tools": memory_cannot_authorize_tools,
        "memory_cannot_create_live_effects": memory_cannot_create_live_effects,
    }
    for key, ok in checks.items():
        if not ok:
            failures.append(f"RED_PHASE26_{key.upper()}_FAIL")
    verdict = VERDICT_GREEN if not failures else failures[0].split(":")[0]
    return {
        "phase": 26,
        "verdict": verdict,
        "ok": verdict == VERDICT_GREEN,
        "failures": failures,
        "checks": checks,
        "proof_bundle": str(proof_bundle) if proof_bundle else None,
        "authority_created": False,
        "permission_granted": False,
        "live_side_effects_created": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    report = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER_REPORT.md"
    proof_dir = WORKSPACE / "docs/proofs/autonomous_agent_zero/PHASE-26-PERSISTENT-MEMORY-EXPERIENCE-LEDGER" / _stamp()
    proof_dir.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/autonomous_agent/test_phase26_memory_ledger.py", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    command = {
        "command": "python -m pytest tests/autonomous_agent/test_phase26_memory_ledger.py -q",
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-2000:],
    }
    (proof_dir / "HEAD.txt").write_text(head + "\n", encoding="utf-8")
    (proof_dir / "command_log.jsonl").write_text(json.dumps(command, sort_keys=True) + "\n", encoding="utf-8")
    preliminary = {
        "phase": 26,
        "head": head,
        "proof_bundle": str(proof_dir),
        "checks_passed": proc.returncode == 0,
    }
    (proof_dir / "summary.json").write_text(json.dumps(preliminary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"phase": 26, "head": head}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "gate_result.json").write_text(json.dumps({"proof_bundle": str(proof_dir)}, indent=2) + "\n", encoding="utf-8")
    result = evaluate_phase26_gate(
        WORKSPACE,
        proof_bundle=proof_dir,
        tests_passed=proc.returncode == 0,
        report_exists=report.is_file(),
        replay_deterministic=proc.returncode == 0,
        receipt_required_for_learning=proc.returncode == 0,
        memory_cannot_grant_authority=proc.returncode == 0,
        memory_cannot_authorize_tools=proc.returncode == 0,
        memory_cannot_create_live_effects=proc.returncode == 0,
    )
    (proof_dir / "gate_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "summary.json").write_text(json.dumps({**preliminary, **result, "checks_passed": result["ok"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "status.md").write_text(f"# Phase 26 Gate\n\nVerdict: `{result['verdict']}`\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["VERDICT_GREEN", "evaluate_phase26_gate", "validate_phase26_proof_bundle"]
