"""CT-V1 final milestone acceptance checks (Batch CT-C)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from hg_core.ct_acceptance.reconcile import AcceptanceCheck, _find_obt_strict_green_bundle
from hg_core.pack_closure.proof_bundles import find_latest_green_gate_bundle, load_gate_result

REQUIRED_MILESTONE_VERDICTS = (
    "ct_gates_registered",
    "deferred_inventory_exists",
    "ct_x1_x5_green",
    "doc_claim_chain",
    "command_log_scripts",
    "obt_strict_ct_green",
    "no_open_ct_blockers_in_inventory",
)


def _verdict_map(gate_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in gate_result.get("verdicts", []):
        if isinstance(entry, dict) and entry.get("check"):
            out[str(entry["check"])] = entry
    return out


def run_ct_v1_milestone_checks(
    workspace: Path,
    *,
    fresh_bundle: Path | None = None,
) -> dict[str, Any]:
    """Verify CT-V1 final audit gate evidence (latest green bundle or fresh run)."""
    checks: list[AcceptanceCheck] = []

    gate_script = workspace / "scripts" / "evals" / "ct_v1_final_audit_gate.py"
    checks.append(
        AcceptanceCheck(
            "ct_v1_final_audit_gate_present",
            gate_script.is_file(),
            str(gate_script.relative_to(workspace)).replace("\\", "/"),
        )
    )

    bundle = fresh_bundle or find_latest_green_gate_bundle(workspace, "CT-V1")
    checks.append(
        AcceptanceCheck(
            "ct_v1_proof_bundle_green",
            bundle is not None,
            str(bundle.relative_to(workspace)).replace("\\", "/") if bundle else "no green CT-V1 bundle",
        )
    )

    verdicts_ok = False
    missing_verdicts: list[str] = []
    failed_verdicts: list[str] = []
    if bundle is not None:
        gate_result = load_gate_result(bundle)
        if gate_result and gate_result.get("ok"):
            vmap = _verdict_map(gate_result)
            missing_verdicts = [name for name in REQUIRED_MILESTONE_VERDICTS if name not in vmap]
            failed_verdicts = [
                name for name in REQUIRED_MILESTONE_VERDICTS if name in vmap and not vmap[name].get("ok", False)
            ]
            verdicts_ok = not missing_verdicts and not failed_verdicts
    checks.append(
        AcceptanceCheck(
            "ct_v1_milestone_verdicts_green",
            verdicts_ok,
            f"missing={missing_verdicts} failed={failed_verdicts}",
        )
    )

    matrix_path = bundle / "artifacts" / "final_audit_matrix.json" if bundle else None
    has_matrix = matrix_path is not None and matrix_path.is_file()
    checks.append(
        AcceptanceCheck(
            "ct_v1_final_audit_matrix_present",
            has_matrix,
            str(matrix_path.relative_to(workspace)).replace("\\", "/") if has_matrix and matrix_path else "absent",
            critical=False,
        )
    )

    obt_bundle = _find_obt_strict_green_bundle(workspace / "docs" / "proofs" / "connective_tissue" / "pack04")
    checks.append(
        AcceptanceCheck(
            "obt_strict_green_referenced",
            obt_bundle is not None,
            str(obt_bundle.relative_to(workspace)).replace("\\", "/") if obt_bundle else "no strict green OBT bundle",
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "milestone",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
        "ct_v1_bundle": str(bundle.relative_to(workspace)).replace("\\", "/") if bundle else None,
        "required_verdicts": list(REQUIRED_MILESTONE_VERDICTS),
    }


def invoke_ct_v1_final_audit_gate(workspace: Path, *, timeout_s: int = 900) -> tuple[int, dict[str, Any], Path | None]:
    """Run live CT-V1 final audit gate; return exit code, parsed stdout, latest bundle path."""
    script = workspace / "scripts" / "evals" / "ct_v1_final_audit_gate.py"
    before = find_latest_green_gate_bundle(workspace, "CT-V1")
    before_ts = before.name if before else ""

    cmd = subprocess.run(
        [sys.executable, str(script)],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_s,
    )
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(cmd.stdout or "{}")
    except json.JSONDecodeError:
        parsed = {"parse_error": True, "stdout_tail": (cmd.stdout or "")[-500:]}

    after = find_latest_green_gate_bundle(workspace, "CT-V1")
    fresh = after if after and (before_ts != after.name or cmd.returncode == 0) else after
    return cmd.returncode, parsed, fresh


__all__ = [
    "REQUIRED_MILESTONE_VERDICTS",
    "invoke_ct_v1_final_audit_gate",
    "run_ct_v1_milestone_checks",
]
