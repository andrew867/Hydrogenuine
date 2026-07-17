"""CLI for connector conformance."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from .connector_runner import run_connector_conformance


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m hg_core.conformance.connector_main <manifest.json> [fixture_dir]")
        return 2
    manifest_path = Path(sys.argv[1])
    fixture_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    report = run_connector_conformance(manifest_path, fixture_dir=fixture_dir)
    print(json.dumps(report, indent=2))
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
