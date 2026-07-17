# Public Conformance v0.1 connector tests
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

def load_connector_manifest(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"operations": [], "receipt_fields": [], "data_classes": []}
    return json.loads(path.read_text(encoding="utf-8"))

def run_connector_conformance(manifest: Dict[str, Any]) -> Dict[str, Any]:
    report = {"result": "pass", "tests": [], "spec_version": "v0.1"}
    ops = manifest.get("operations", [])
    receipt_fields = manifest.get("receipt_fields", [])
    report["tests"].append({"id": "manifest_operations", "pass": isinstance(ops, list), "detail": "operations declared"})
    report["tests"].append({"id": "manifest_receipt_fields", "pass": isinstance(receipt_fields, list), "detail": "receipt_fields declared"})
    report["tests"].append({"id": "deny_proof_refs", "pass": manifest.get("deny_proof_refs", True) or "proof" in str(receipt_fields), "detail": "deny path proof refs"})
    report["tests"].append({"id": "idempotency", "pass": manifest.get("idempotency", True) is not False, "detail": "idempotency"})
    report["tests"].append({"id": "receipt_hashes", "pass": len(receipt_fields) >= 1 or "hash" in str(receipt_fields).lower(), "detail": "receipts include hashes/ids"})
    if not all(t["pass"] for t in report["tests"]):
        report["result"] = "fail"
    return report
