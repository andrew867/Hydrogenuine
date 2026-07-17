"""Run registry — manages run IDs and state directories."""

from __future__ import annotations

import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1].parent
DEFAULT_STATE_ROOT = WORKSPACE / ".hg-runtime" / "agent_zero_runs"
DEFAULT_PROOF_ROOT = WORKSPACE.parent / "docs" / "proofs" / "autonomous_agent_zero"


def generate_run_id() -> str:
    return "run_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def state_dir_for_run(run_id: str, root: Path | None = None) -> Path:
    return (root or DEFAULT_STATE_ROOT) / run_id


def proof_dir_for_launch(ts: str | None = None) -> Path:
    ts = ts or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return DEFAULT_PROOF_ROOT / "HG-AGENT-ZERO-DAEMON-LAUNCH" / ts


def proof_dir_for_soak(ts: str | None = None) -> Path:
    ts = ts or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return DEFAULT_PROOF_ROOT / "HG-ACTUAL-PACED-LONG-SOAK" / ts


def list_runs(root: Path | None = None) -> list[str]:
    r = root or DEFAULT_STATE_ROOT
    if not r.exists():
        return []
    return sorted([d.name for d in r.iterdir() if d.is_dir() and d.name.startswith("run_")])
