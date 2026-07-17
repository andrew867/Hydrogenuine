"""Run a set of scenarios into one dated proof bundle with top-level artifacts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.demos.grs_runner.runner import (
    LiveModeUnavailable, _sha256_file, run_scenario,
)
from hg_runtime.demos.grs_runner.scenario_schema import ScenarioError


def run_suite(scenario_paths: list[Path], output_root: Path, ts: str | None = None) -> dict:
    ts = ts or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = output_root / ts
    out.mkdir(parents=True, exist_ok=True)

    results = []
    for i, sp in enumerate(scenario_paths, 1):
        scenario = json.loads(Path(sp).read_text(encoding="utf-8"))
        sub = out / f"scenario_{i}"
        try:
            index = run_scenario(scenario, sub)
            results.append({"scenario_path": str(sp), "subdir": f"scenario_{i}",
                            "status": "completed", "index": index})
        except (ScenarioError, LiveModeUnavailable) as exc:
            # Honest failure: recorded, never masked with fixtures.
            results.append({"scenario_path": str(sp), "subdir": f"scenario_{i}",
                            "status": "failed", "error": f"{type(exc).__name__}: {exc}"})

    (out / "runner_config.json").write_text(json.dumps({
        "runner": "hg_runtime.demos.grs_runner", "schema": "grs_demo_scenario_v1",
        "scenarios": [str(p) for p in scenario_paths],
        "no_silent_fallback": True, "cloud_providers": False,
    }, indent=1), encoding="utf-8")
    (out / "scenario_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")

    completed = [r for r in results if r["status"] == "completed"]
    (out / "proof_index.json").write_text(json.dumps({
        "title": "Reusable GRS Demo Runner — scenario suite",
        "bundle_id": ts,
        "scenarios_total": len(results),
        "scenarios_completed": len(completed),
        "scenario_indexes": [r["index"] for r in completed],
        "gate_result_path": "gate_result.json",
        "claim_boundary_report_path": "claim_boundary_report.md",
        "summary_report_path": "summary_report.md",
        "checksums_path": "checksums.sha256",
    }, indent=1), encoding="utf-8")

    return {"output_dir": str(out), "timestamp": ts, "results": results}


def seal_suite(out: Path) -> None:
    """Top-level checksums + manifest written last (CT sealing order)."""
    files = sorted(p for p in out.rglob("*") if p.is_file()
                   and not (p.parent == out and p.name in {"checksums.sha256", "manifest.json"}))
    lines = [f"{_sha256_file(p)}  {p.relative_to(out).as_posix()}" for p in files]
    (out / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "1", "bundle": "grs_demo_runner_suite",
        "claim": "proof records the path; it does not prove model correctness",
        "file_hashes": {p.relative_to(out).as_posix(): _sha256_file(p)
                        for p in files + [out / "checksums.sha256"]},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
