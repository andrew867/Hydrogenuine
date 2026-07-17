"""Phase 39 soak artifact writer.

Writes a per-scenario evidence folder for operator review. It refuses to write
if any hard-boundary flag is set on the run (the soak would have gone live), and
it never writes applied code — only soak evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.long_run_stability.schemas import BOUNDARY_FLAG_FIELDS, StabilityError, neutral_flags


def write_scenario_artifact(artifact_root: Path, bundle: Mapping[str, Any]) -> Path | None:
    run = bundle.get("run")
    if run is None:
        return None
    if any(run["state"].get(field) for field in BOUNDARY_FLAG_FIELDS):
        raise StabilityError("artifact_writer_refuses_run_with_live_boundary_state")

    folder = Path(artifact_root) / "scenarios" / bundle["name"]
    folder.mkdir(parents=True, exist_ok=True)

    def _dump(name: str, payload: Any) -> None:
        (folder / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _dump("final_state.json", run["state"])
    _dump("checkpoint_manifest.json", bundle["checkpoint_manifest"])
    _dump("invariant_snapshot.json", bundle["invariant_snapshot"])
    _dump("boundary_snapshot.json", bundle["boundary_snapshot"])
    _dump("replay_eval.json", {k: v for k, v in bundle["replay_eval"].items()})
    (folder / "events.jsonl").write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in run["events"]) + ("\n" if run["events"] else ""),
        encoding="utf-8",
    )
    readme = (
        f"# Phase 39 soak scenario: {bundle['name']}\n\n"
        f"Mode: `{bundle['mode']}` — halt: `{bundle['halt_reason']}` — "
        f"tasks processed: {bundle['tasks_processed']}/{bundle['task_count']}.\n\n"
        "This is soak evidence only. No patch was applied, no authority granted, "
        "no tool authorized, no live effect or post created, no external provider called.\n"
    )
    (folder / "README.md").write_text(readme, encoding="utf-8")
    _dump("neutral_flags.json", neutral_flags())
    return folder


__all__ = ["write_scenario_artifact"]
