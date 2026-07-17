#!/usr/bin/env python3
"""
Run a DAG from a JSON file.

Usage:
  python -m hg_core.run_dag <path-to-dag.json> [--input key=value ...] [--run-dir DIR]
  python -m hg_core.run_dag <path-to-dag.json> --resume RUN_ID [--run-dir DIR]

  hg-run-dag <path-to-dag.json> [--input key=value ...] [--run-dir DIR]
  hg-run-dag <path-to-dag.json> --resume RUN_ID [--run-dir DIR]

Loads the DAG, runs it with TaskGraphExecutor, and prints the run summary.
Optional --input key=value pairs are merged into graph_inputs.
When --run-dir is set, uses StateStore and writes audit artifacts (graph.json, state.json,
summary.json, events.jsonl, state_history/) to that directory.
With --resume RUN_ID, loads persisted state for that run and continues until no ready/running nodes remain.
Use the same --run-dir as the original run when resuming so StateStore finds the state file (base_dir/run_id.json).
"""

import argparse
import json
import sys
from pathlib import Path

from hg_core.task_graph import TaskGraphExecutor, StateStore, load_dag, validate_dag
from hg_core.task_graph.tool_contract_setup import build_default_tool_contract


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a DAG from a JSON file. See docs/specs/dag_executor_contract.md."
    )
    parser.add_argument(
        "dag_path",
        type=Path,
        help="Path to DAG JSON file (e.g. memory/automation/dags/linear_three_steps.json)",
    )
    parser.add_argument(
        "--input",
        "-i",
        action="append",
        dest="inputs",
        metavar="KEY=VALUE",
        help="Graph input (can be repeated). Example: -i topic=memory",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Write audit artifacts (state.json, summary.json, events.jsonl, state_history/) here; when resuming, use same as original run",
    )
    parser.add_argument(
        "--resume",
        type=str,
        metavar="RUN_ID",
        default=None,
        help="Resume a previous run by run_id; load state from StateStore and continue",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate DAG (load + validate_dag); exit 0 if valid, 1 if invalid",
    )
    args = parser.parse_args()

    path = args.dag_path
    if not path.exists():
        print(json.dumps({"ok": False, "error": f"DAG file not found: {path}"}, indent=2), file=sys.stderr)
        sys.exit(1)

    graph_inputs = {}
    for s in args.inputs or []:
        if "=" in s:
            k, v = s.split("=", 1)
            graph_inputs[k.strip()] = v.strip()
        else:
            graph_inputs[s.strip()] = True

    try:
        dag = load_dag(path)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"Failed to load DAG: {e}"}, indent=2), file=sys.stderr)
        sys.exit(1)

    if args.validate:
        result = validate_dag(dag)
        out = {"valid": result.valid, "errors": result.errors}
        print(json.dumps(out, indent=2))
        sys.exit(0 if result.valid else 1)

    overseer = None
    try:
        from hg_overseer.overseer_core.dag_hooks import DAGCheckpointAdapter
        overseer = DAGCheckpointAdapter()
    except Exception:
        pass

    run_dir = Path(args.run_dir) if args.run_dir else None
    if run_dir is not None:
        run_dir.mkdir(parents=True, exist_ok=True)
    base_dir = run_dir.parent if run_dir is not None else None
    store = StateStore(base_dir=base_dir)
    registry, adapter = build_default_tool_contract()

    # Phase 9: optional L10 telemetry sink so GET /events/stream sees timeline events
    telemetry = None
    try:
        from hg_core.task_graph.telemetry import default_telemetry_sink
        from hg_realtime.integrations.run_dag_telemetry import make_l10_telemetry_sink
        base_sink = default_telemetry_sink(overseer=overseer)
        l10_sink = make_l10_telemetry_sink()
        if l10_sink is not None:
            def _composite_telemetry(event_name: str, payload: dict) -> None:
                base_sink(event_name, payload)
                l10_sink(event_name, payload)
            telemetry = _composite_telemetry
        else:
            telemetry = base_sink
    except Exception:
        pass

    executor = TaskGraphExecutor(
        state_store=store,
        overseer=overseer,
        tool_registry=registry,
        tool_adapter=adapter,
        telemetry=telemetry,
    )

    explicit_run_id = None
    if run_dir is not None:
        explicit_run_id = run_dir.name

    if args.resume:
        summary = executor.resume(dag, args.resume, graph_inputs=graph_inputs or None, run_dir=run_dir)
        if not summary.get("ok") and summary.get("error") == "run_not_found":
            print(json.dumps(summary, indent=2), file=sys.stderr)
            sys.exit(2)
    else:
        if run_dir is not None:
            summary = executor.run(
                dag,
                graph_inputs=graph_inputs or None,
                run_id=explicit_run_id,
                run_dir=run_dir,
            )
        else:
            summary = executor.run(dag, graph_inputs=graph_inputs or None)

    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary.get("ok") else 1)


if __name__ == "__main__":
    main()
