"""CLI: python -m hg_runtime.demos.proofkit_tamper_demo --source-bundle <p> --output <p> --public-safe"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .harness import run_demo
from .reports import seal_bundle, write_reports


def main() -> int:
    ap = argparse.ArgumentParser(description="Proofkit tamper public demo")
    ap.add_argument("--source-bundle", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True,
                    help="Output root; a UTC-timestamped bundle dir is created inside")
    ap.add_argument("--public-safe", action="store_true")
    args = ap.parse_args()

    result = run_demo(args.source_bundle.resolve(), args.output.resolve(),
                      public_safe=args.public_safe)
    out = Path(result["output_dir"])
    write_reports(out, result)
    seal_bundle(out)

    print(json.dumps({
        "demo": "proofkit_tamper_demo",
        "output_dir": result["output_dir"],
        "baseline_ok": result["baseline_ok"],
        "tamper_cases_matched": f"{result['tamper_cases_matched']}/{result['tamper_cases_total']}",
        "source_bundle_unchanged": result["source_bundle_unchanged"],
    }, indent=1))
    ok = (result["baseline_ok"] and result["source_bundle_unchanged"]
          and result["tamper_cases_matched"] == result["tamper_cases_total"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
