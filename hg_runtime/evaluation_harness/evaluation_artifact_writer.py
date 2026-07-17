"""P31 evaluation artifact writer — writes evaluation results to proof bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_evaluation_artifacts(
    proof_dir: Path,
    run_summary: dict[str, Any],
    fixtures: list[dict[str, Any]],
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "evaluation_summary.json", {
        "total": run_summary["total"],
        "passed": run_summary["passed"],
        "failed": run_summary["failed"],
        "deferred": run_summary["deferred"],
        "refused": run_summary["refused"],
        "coverage": run_summary["coverage"],
        "score_is_not_truth": True,
        "score_is_not_competence": True,
    })
    write_json(proof_dir / "coverage.json", run_summary["coverage"])
    results = [r.get("result", r) for r in run_summary.get("results", [])]
    write_jsonl(proof_dir / "results.jsonl", results)
    if run_summary.get("refusals"):
        write_jsonl(proof_dir / "refusals.jsonl", run_summary["refusals"])
    write_json(proof_dir / "fixtures_index.json", {
        "fixture_count": len(fixtures),
        "fixture_ids": [f["task_id"] for f in fixtures],
    })
