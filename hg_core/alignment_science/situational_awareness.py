"""
Layer 9 Phase 6 (optional): Situational-awareness testbed — config, probe runner, scale-dependence metrics.
Environments where "I am an AI in evaluation" is variable; probe types (e.g. deception, goal stability).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Local types (Phase 6 optional; not in main schemas.py) ---

TestbedConfig = Dict[str, Any]
ProbeResult = Dict[str, Any]
TestbedRunResult = Dict[str, Any]

# --- Builders ---


def testbed_config(
    environment_id: str,
    probe_types: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TestbedConfig:
    out: TestbedConfig = {
        "environment_id": environment_id,
        "probe_types": probe_types or ["deception", "goal_stability"],
    }
    if metadata is not None:
        out["metadata"] = metadata
    return out


def probe_result(
    probe_id: str,
    probe_type: str,
    outcome: str,
    metrics: Optional[Dict[str, Any]] = None,
    rationale: Optional[str] = None,
) -> ProbeResult:
    """outcome: pass | fail | inconclusive."""
    out: ProbeResult = {
        "probe_id": probe_id,
        "probe_type": probe_type,
        "outcome": outcome,
        "metrics": metrics or {},
    }
    if rationale is not None:
        out["rationale"] = rationale
    return out


def testbed_run_result(
    run_id: str,
    config: TestbedConfig,
    probe_results: List[ProbeResult],
    artifact_ref: str,
    scale_dependence_metrics: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> TestbedRunResult:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: TestbedRunResult = {
        "run_id": run_id,
        "config": config,
        "probe_results": probe_results,
        "artifact_ref": artifact_ref,
        "created_at": ts,
    }
    if scale_dependence_metrics is not None:
        out["scale_dependence_metrics"] = scale_dependence_metrics
    return out


def validate_testbed_run_result(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("run_id", "config", "probe_results", "artifact_ref")):
        return False
    if not isinstance(data["probe_results"], list):
        return False
    if not isinstance(data["config"], dict):
        return False
    return True


# --- Artifacts ---


def _artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "testbed_runs"


def run_testbed(
    workspace_root: Path,
    config: Optional[TestbedConfig] = None,
    run_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> TestbedRunResult:
    """
    Run testbed with config: execute probes (stub), collect results and scale-dependence metrics, store artifact.
    config may have environment_id and probe_types (e.g. ["deception", "goal_stability"]).
    """
    workspace_root = Path(workspace_root)
    cfg = config or testbed_config("default_env")
    run_id = run_id or str(uuid.uuid4())
    probe_types = cfg.get("probe_types") or ["deception", "goal_stability"]
    probe_results: List[ProbeResult] = []
    for i, ptype in enumerate(probe_types):
        # Stub: one pass, one inconclusive for variety
        outcome = "pass" if i % 2 == 0 else "inconclusive"
        probe_results.append(
            probe_result(
                probe_id=f"{ptype}_{i}",
                probe_type=ptype,
                outcome=outcome,
                metrics={"stub_score": 0.5 + i * 0.1},
                rationale="Stub probe result.",
            )
        )
    scale_dependence_metrics = {
        "stub_scale_factor": 1.0,
        "probe_count": len(probe_results),
    }
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _artifacts_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{run_id}.json"
    result = testbed_run_result(
        run_id=run_id,
        config=cfg,
        probe_results=probe_results,
        artifact_ref=str(artifact_path),
        scale_dependence_metrics=scale_dependence_metrics,
    )
    artifact_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if emit_ledger:
        try:
            from hg_core.ledger import emit

            emit(
                "TESTBED_RUN_COMPLETED",
                "testbed_run",
                run_id,
                {
                    "run_id": run_id,
                    "environment_id": cfg.get("environment_id"),
                    "probe_count": len(probe_results),
                    "artifact_ref": str(artifact_path),
                },
                workspace_root=workspace_root,
                object_path=str(artifact_path),
            )
        except Exception:
            pass
    return result


def get_testbed_run_result(
    workspace_root: Path, run_id: str
) -> Optional[TestbedRunResult]:
    workspace_root = Path(workspace_root)
    root = _artifacts_root(workspace_root)
    if not root.exists():
        return None
    for date_dir in sorted(root.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        path = date_dir / f"{run_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("run_id") == run_id and validate_testbed_run_result(data):
                    return data
            except Exception:
                continue
    return None
