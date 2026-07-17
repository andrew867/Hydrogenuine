"""Daemon run finalizer — aggregates proof, writes final verdict."""

from __future__ import annotations

import json
from pathlib import Path

from .state import load_state
from .heartbeat import read_heartbeat
from .run_registry import state_dir_for_run


def finalize_run(run_id: str) -> dict:
    sdir = state_dir_for_run(run_id)
    state = load_state(sdir)
    if state is None:
        return {"error": f"No state for {run_id}"}

    hb = read_heartbeat(sdir)
    proof_dir = None
    if hb and hb.get("proof_path"):
        proof_dir = Path(hb["proof_path"])

    final_report_path = proof_dir / "final_report.json" if proof_dir else None
    has_final_report = final_report_path and final_report_path.exists()

    return {
        "run_id": run_id,
        "status": state.status,
        "verdict": state.verdict_so_far,
        "elapsed_hours": state.elapsed_seconds / 3600,
        "cycles": state.cycle_count,
        "seeds_worked": len(state.seeds_worked),
        "boundary_violations": state.boundary_violations,
        "has_final_report": has_final_report,
        "proof_dir": str(proof_dir) if proof_dir else None,
        "output_classifications": state.output_classifications,
        "retry_stats": {
            "attempts": state.retry_attempts,
            "successes": state.retry_successes,
            "failures": state.retry_failures,
        },
    }
