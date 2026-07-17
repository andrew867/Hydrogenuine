"""CLI for benchmark scenario runner."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from .benchmark_runner import run_benchmark_scenario


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m hg_core.conformance.benchmark_main <scenario.json> [bundle_dir]")
        return 2
    scenario_path = Path(sys.argv[1])
    bundle_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    report = run_benchmark_scenario(scenario_path, bundle_dir=bundle_dir)
    print(json.dumps(report, indent=2))
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
