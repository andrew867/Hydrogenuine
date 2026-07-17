"""
Interop Pack 6: Reference bundle verifier — validates minimal bundle layout and JSON validity.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def verify_ref_bundle(bundle_dir: Path) -> Dict[str, Any]:
    """
    Verify reference bundle directory: bundle.json, events.jsonl, manifests/artifacts_manifest.json.
    Returns {"ok": bool, "errors": list, "warnings": list}.
    """
    bundle_dir = Path(bundle_dir)
    report: Dict[str, Any] = {"ok": True, "errors": [], "warnings": []}
    required = [
        ("bundle.json", "file"),
        ("events.jsonl", "file"),
        ("manifests/artifacts_manifest.json", "file"),
    ]
    for name, kind in required:
        p = bundle_dir / name
        if not p.exists():
            report["errors"].append(f"missing {name}")
            report["ok"] = False
            continue
        if kind == "file" and p.is_dir():
            report["errors"].append(f"{name} should be file")
            report["ok"] = False
    if not report["ok"]:
        return report
    try:
        with open(bundle_dir / "bundle.json", "r", encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        report["errors"].append("bundle.json invalid: " + str(e))
        report["ok"] = False
    try:
        with open(bundle_dir / "manifests" / "artifacts_manifest.json", "r", encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        report["errors"].append("manifests/artifacts_manifest.json invalid: " + str(e))
        report["ok"] = False
    try:
        with open(bundle_dir / "events.jsonl", "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                json.loads(line)
    except Exception as e:
        report["errors"].append("events.jsonl invalid: %s" % e)
        report["ok"] = False
    return report
