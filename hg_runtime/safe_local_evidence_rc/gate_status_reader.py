"""Read latest gate results from proof bundles."""

from __future__ import annotations

import json
from pathlib import Path


def latest_gate_result(root: Path, proof_root_name: str) -> tuple[str, str, dict | None]:
    proof_root = root / "docs/proofs/autonomous_agent_zero" / proof_root_name
    gates = sorted(proof_root.glob("*/gate_result.json"))
    if not gates:
        return "UNKNOWN", "", None
    path = gates[-1]
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("verdict", "UNKNOWN"), str(path.parent.relative_to(root)), data


def read_gate_statuses(root: Path, proof_roots: list[tuple[str, str]]) -> list[dict]:
    rows = []
    for proof_root_name, expected in proof_roots:
        verdict, proof_bundle, gate_data = latest_gate_result(root, proof_root_name)
        rows.append(
            {
                "proof_root": proof_root_name,
                "expected_verdict": expected,
                "gate_verdict": verdict,
                "proof_bundle": proof_bundle,
                "is_green": verdict == expected and verdict.startswith("GREEN"),
                "base_head": gate_data.get("base_head", "") if gate_data else "",
            }
        )
    return rows
