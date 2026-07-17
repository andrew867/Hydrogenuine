"""
Interop Pack 6: Demo starter kit — scripted scenario: export toy bundle, verify, run invariant checker.
Run from repo root: python -m hg_core.interop.ref_baselines.demo_starter [output_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(out_dir: str) -> int:
    out = Path(out_dir)
    from hg_core.interop.ref_baselines import export_toy_bundle, verify_ref_bundle, run_invariant_checker
    print("Exporting toy bundle to %s ..." % out)
    export_toy_bundle(out)
    print("Verifying bundle ...")
    verify_report = verify_ref_bundle(out)
    if not verify_report.get("ok"):
        print("Verification failed:", verify_report.get("errors"))
        return 2
    print("Verification OK.")
    print("Running invariant checker ...")
    inv_report = run_invariant_checker(out / "events.jsonl")
    report_path = out / "invariant_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(inv_report, f, indent=2)
    print("Invariant report written to %s" % report_path)
    print("Overall invariants: %s" % ("PASS" if inv_report.get("ok") else "FAIL"))
    return 0 if inv_report.get("ok") else 1


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "demo_bundle_out"
    sys.exit(main(out_dir))
