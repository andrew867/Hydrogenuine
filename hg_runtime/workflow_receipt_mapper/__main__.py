"""CLI: python -m hg_runtime.workflow_receipt_mapper --intake <intake.json> --output <dir>

Pure analysis — never calls external services, never performs workflow effects.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hg_runtime.workflow_receipt_mapper.mapper import map_workflow
from hg_runtime.workflow_receipt_mapper.schema import IntakeError


def main() -> int:
    ap = argparse.ArgumentParser(description="Workflow receipt mapper")
    ap.add_argument("--intake", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    intake = json.loads(args.intake.read_text(encoding="utf-8"))
    out = args.output / intake.get("workflow_id", "unnamed")
    try:
        m = map_workflow(intake, out)
    except IntakeError as exc:
        print(json.dumps({"error": "IntakeError", "detail": str(exc)}))
        return 1
    print(json.dumps({"workflow_id": m["workflow_summary"]["workflow_id"],
                      "map_id": m["map_id"],
                      "publicability": m["publicability"]["status"],
                      "runner_projection": m["runner_projection"]["status"],
                      "output_dir": str(out)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
