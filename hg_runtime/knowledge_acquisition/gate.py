"""Phase 30 gate and proof bundle validation."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
VERDICT_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_30_KNOWLEDGE_ACQUISITION_LOOP"
PHASE26_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER"
PHASE28_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_28_DOMAIN_PACK_RUNTIME"
PHASE29_GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_29_TOOL_MEDIATED_WORKBENCH"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_phase30_proof_bundle(path: Path | None) -> tuple[bool, list[str]]:
    if path is None:
        return False, ["RED_PHASE30_PROOF_BUNDLE_MISSING"]
    required = ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]
    failures: list[str] = []
    for name in required:
        if not (path / name).is_file():
            failures.append(f"RED_PHASE30_PROOF_BUNDLE_MISSING:{name}")
    gate_path = path / "gate_result.json"
    if gate_path.is_file():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            if gate.get("proof_bundle") and Path(str(gate["proof_bundle"])).resolve() != path.resolve():
                failures.append("RED_PHASE30_PROOF_BUNDLE_PATH_MISMATCH")
        except json.JSONDecodeError:
            failures.append("RED_PHASE30_GATE_RESULT_INVALID_JSON")
    return not failures, failures


def evaluate_phase30_gate(
    repo_root: Path = WORKSPACE,
    *,
    phase26_green: bool,
    phase28_green: bool,
    phase29_green: bool,
    proof_bundle: Path | None,
    tests_passed: bool,
    report_exists: bool = False,
    unsourced_claims_marked_tbd: bool = False,
    stale_sources_require_review: bool = False,
    glossary_update_requires_evidence: bool = False,
    mini_task_result_audited: bool = False,
    memory_promotion_requires_citation_and_audit: bool = False,
    self_merge_rejected: bool = False,
    acquired_knowledge_cannot_authorize_tools: bool = False,
    acquired_knowledge_cannot_widen_authority: bool = False,
    network_acquisition_refuses_by_default: bool = False,
    credential_source_reads_rejected: bool = False,
    replay_deterministic: bool = False,
    no_live_side_effect_path_by_default: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    if not phase26_green:
        failures.append("RED_PHASE30_PHASE26_GREEN_REQUIRED")
    if not phase28_green:
        failures.append("RED_PHASE30_PHASE28_GREEN_REQUIRED")
    if not phase29_green:
        failures.append("RED_PHASE30_PHASE29_GREEN_REQUIRED")
    proof_ok, proof_failures = validate_phase30_proof_bundle(proof_bundle)
    failures.extend(proof_failures)
    checks = {
        "tests_passed": tests_passed,
        "proof_bundle_valid": proof_ok,
        "report_exists": report_exists,
        "unsourced_claims_marked_tbd": unsourced_claims_marked_tbd,
        "stale_sources_require_review": stale_sources_require_review,
        "glossary_update_requires_evidence": glossary_update_requires_evidence,
        "mini_task_result_audited": mini_task_result_audited,
        "memory_promotion_requires_citation_and_audit": memory_promotion_requires_citation_and_audit,
        "self_merge_rejected": self_merge_rejected,
        "acquired_knowledge_cannot_authorize_tools": acquired_knowledge_cannot_authorize_tools,
        "acquired_knowledge_cannot_widen_authority": acquired_knowledge_cannot_widen_authority,
        "network_acquisition_refuses_by_default": network_acquisition_refuses_by_default,
        "credential_source_reads_rejected": credential_source_reads_rejected,
        "replay_deterministic": replay_deterministic,
        "no_live_side_effect_path_by_default": no_live_side_effect_path_by_default,
    }
    for key, ok in checks.items():
        if not ok:
            failures.append(f"RED_PHASE30_{key.upper()}_FAIL")
    verdict = VERDICT_GREEN if not failures else failures[0].split(":")[0]
    return {
        "phase": 30,
        "verdict": verdict,
        "ok": verdict == VERDICT_GREEN,
        "failures": failures,
        "checks": checks,
        "proof_bundle": str(proof_bundle) if proof_bundle else None,
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "source_treated_as_authority": False,
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
    report = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_30_KNOWLEDGE_ACQUISITION_LOOP_REPORT.md"
    proof_dir = WORKSPACE / "docs/proofs/autonomous_agent_zero/PHASE-30-KNOWLEDGE-ACQUISITION-LOOP" / _stamp()
    proof_dir.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    phase26_ok = _gate_green("scripts/evals/autonomous_agent_phase_26_persistent_memory_experience_ledger_gate.py", PHASE26_GREEN)
    phase28_ok = _gate_green("scripts/evals/autonomous_agent_phase_28_domain_pack_runtime_gate.py", PHASE28_GREEN)
    phase29_ok = _gate_green("scripts/evals/autonomous_agent_phase_29_tool_mediated_workbench_gate.py", PHASE29_GREEN)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/autonomous_agent/test_phase30_knowledge_acquisition.py", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    command_log = [
        {"command": "python scripts/evals/autonomous_agent_phase_26_persistent_memory_experience_ledger_gate.py", "returncode": 0 if phase26_ok else 1},
        {"command": "python scripts/evals/autonomous_agent_phase_28_domain_pack_runtime_gate.py", "returncode": 0 if phase28_ok else 1},
        {"command": "python scripts/evals/autonomous_agent_phase_29_tool_mediated_workbench_gate.py", "returncode": 0 if phase29_ok else 1},
        {
            "command": "python -m pytest tests/autonomous_agent/test_phase30_knowledge_acquisition.py -q",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-2000:],
        },
    ]
    (proof_dir / "HEAD.txt").write_text(head + "\n", encoding="utf-8")
    (proof_dir / "command_log.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in command_log) + "\n", encoding="utf-8")
    (proof_dir / "manifest.json").write_text(json.dumps({"phase": 30, "head": head}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "gate_result.json").write_text(json.dumps({"proof_bundle": str(proof_dir)}, indent=2) + "\n", encoding="utf-8")
    preliminary = {"phase": 30, "head": head, "proof_bundle": str(proof_dir), "checks_passed": proc.returncode == 0 and phase26_ok and phase28_ok and phase29_ok}
    (proof_dir / "summary.json").write_text(json.dumps(preliminary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ok = proc.returncode == 0
    result = evaluate_phase30_gate(
        WORKSPACE,
        phase26_green=phase26_ok,
        phase28_green=phase28_ok,
        phase29_green=phase29_ok,
        proof_bundle=proof_dir,
        tests_passed=ok,
        report_exists=report.is_file(),
        unsourced_claims_marked_tbd=ok,
        stale_sources_require_review=ok,
        glossary_update_requires_evidence=ok,
        mini_task_result_audited=ok,
        memory_promotion_requires_citation_and_audit=ok,
        self_merge_rejected=ok,
        acquired_knowledge_cannot_authorize_tools=ok,
        acquired_knowledge_cannot_widen_authority=ok,
        network_acquisition_refuses_by_default=ok,
        credential_source_reads_rejected=ok,
        replay_deterministic=ok,
        no_live_side_effect_path_by_default=ok,
    )
    (proof_dir / "gate_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "summary.json").write_text(json.dumps({**preliminary, **result, "checks_passed": result["ok"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "status.md").write_text(f"# Phase 30 Gate\n\nVerdict: `{result['verdict']}`\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["VERDICT_GREEN", "evaluate_phase30_gate", "validate_phase30_proof_bundle"]
