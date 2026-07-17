"""Substrate regate checks for Phase 35 entry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

PHASE336_ROOT = ROOT / "docs/proofs/autonomous_agent_zero/PHASE-33-6-LOCAL-MULTI-ORGAN-INFERENCE-BUS"
PHASE36_ROOT = ROOT / "docs/proofs/autonomous_agent_zero/PHASE-36-AUTONOMOUS-PROPOSAL-SOAK"
PHASE34_ROOT = ROOT / "docs/proofs/autonomous_agent_zero/PHASE-34-ECONOMIC-TASK-BENCHMARK-SUITE"
PHASE19_REPORT = ROOT / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_19_EXTERNAL_ACTION_AUDIT_INCIDENT_REPORT.md"


def _latest_gate(root: Path) -> tuple[Path | None, dict[str, Any]]:
    gates = sorted(root.glob("*/gate_result.json"))
    if not gates:
        return None, {"verdict": "UNKNOWN", "ok": False}
    path = gates[-1]
    return path.parent, json.loads(path.read_text(encoding="utf-8"))


def load_substrate_status() -> dict[str, Any]:
    p336_dir, p336 = _latest_gate(PHASE336_ROOT)
    p36_dir, p36 = _latest_gate(PHASE36_ROOT)
    _, p34 = _latest_gate(PHASE34_ROOT)
    phase19_verdict = "UNKNOWN"
    if PHASE19_REPORT.is_file():
        for line in PHASE19_REPORT.read_text(encoding="utf-8").splitlines():
            if line.startswith("**Verdict:**"):
                phase19_verdict = line.split("`")[1] if "`" in line else line.split(":", 1)[-1].strip()
                break
    return {
        "phase33_6_verdict": p336.get("verdict", "UNKNOWN"),
        "phase33_6_ok": p336.get("verdict") == "GREEN_LOCAL_MULTI_ORGAN_INFERENCE_BUS",
        "phase33_6_proof_dir": str(p336_dir) if p336_dir else None,
        "phase36_verdict": p36.get("verdict", "UNKNOWN"),
        "phase36_ok": p36.get("verdict") == "GREEN_AUTONOMOUS_PROPOSAL_SOAK_READY_WITH_P33_6_REPAIRED",
        "phase36_proof_dir": str(p36_dir) if p36_dir else None,
        "phase34_verdict": p34.get("verdict", "UNKNOWN"),
        "phase19_verdict": phase19_verdict,
        "phase19_yellow_preserved": "YELLOW_PHASE19" in phase19_verdict,
        "phase24_infrastructure_only": True,
    }


def require_substrate_green() -> dict[str, Any]:
    status = load_substrate_status()
    failures: list[str] = []
    if not status["phase33_6_ok"]:
        failures.append("phase35_gate_refuses_without_p33_6_green")
    if not status["phase36_ok"]:
        failures.append("phase35_gate_refuses_without_p36_green")
    if not status["phase19_yellow_preserved"]:
        failures.append("phase19_yellow_not_preserved")
    return {"ok": not failures, "failures": failures, **status}


__all__ = ["load_substrate_status", "require_substrate_green"]
