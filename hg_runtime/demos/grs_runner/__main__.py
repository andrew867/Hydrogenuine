"""CLI: python -m hg_runtime.demos.grs_runner --scenario <config.json> --output <root>

Runs one scenario through the reusable pipeline and writes a scenario proof bundle
under <root>/<scenario_id>/. Never falls back silently; live failures exit non-zero.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hg_runtime.demos.grs_runner.runner import LiveModeUnavailable, run_scenario
from hg_runtime.demos.grs_runner.scenario_schema import ScenarioError


def main() -> int:
    ap = argparse.ArgumentParser(description="Reusable GRS demo runner")
    ap.add_argument("--scenario", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
    out = args.output / scenario.get("scenario_id", "unnamed")
    try:
        index = run_scenario(scenario, out)
    except (ScenarioError, LiveModeUnavailable) as exc:
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}))
        return 1
    print(json.dumps(index, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
