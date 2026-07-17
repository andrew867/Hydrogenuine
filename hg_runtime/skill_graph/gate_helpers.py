"""Shared gate helpers for P27/P28 batch."""

from __future__ import annotations

import json
from pathlib import Path


def latest_gate_verdict(root: Path, proof_root_name: str) -> tuple[str, str, bool]:
    proof_root = root / "docs/proofs/autonomous_agent_zero" / proof_root_name
    gates = sorted(proof_root.glob("*/gate_result.json"))
    if not gates:
        return "UNKNOWN", "", False
    path = gates[-1]
    data = json.loads(path.read_text(encoding="utf-8"))
    verdict = data.get("verdict", "UNKNOWN")
    ok = data.get("ok") is True and verdict.startswith("GREEN")
    return verdict, str(path.parent.relative_to(root)), ok
