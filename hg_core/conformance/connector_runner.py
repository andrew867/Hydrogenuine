"""Control Surface Pack 5: Connector conformance runner."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def run_connector_conformance(
    manifest_path: Path,
    fixture_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run conformance checks on connector SDK manifest. Returns report with result and tests."""
    manifest_path = Path(manifest_path)
    report: Dict[str, Any] = {"result": "fail", "tests": [], "manifest_path": str(manifest_path)}
    tests: List[Dict[str, Any]] = []
    if not manifest_path.exists():
        tests.append({"id": "manifest:exists", "ok": False, "err": "file not found"})
        report["tests"] = tests
        return report
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        tests.append({"id": "manifest:parse", "ok": False, "err": str(e)})
        report["tests"] = tests
        return report
    tests.append({"id": "manifest:has_operations", "ok": bool(manifest.get("operations"))})
    tests.append({"id": "manifest:has_data_classes", "ok": bool(manifest.get("data_classes"))})
    if fixture_dir and Path(fixture_dir).exists():
        n = len(list(Path(fixture_dir).glob("*.json")))
        tests.append({"id": "fixtures:found", "ok": True, "count": n})
    report["tests"] = tests
    report["result"] = "pass" if all(t.get("ok", False) for t in tests) else "fail"
    return report
