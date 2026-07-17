"""Integrity operation receipts.

Every hash/verify operation is receipted. Tamper evidence only.
No identity signing. No promotion.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def write_integrity_receipts(
    *,
    proof_dir: str,
    manifest: dict,
    verify_result: dict | None = None,
    out_dir: str | None = None,
) -> str:
    target = out_dir or proof_dir
    os.makedirs(target, exist_ok=True)

    receipts = []
    receipts.append({
        "schema_version": "integrity_receipt_v1",
        "event_type": "manifest_created",
        "proof_dir": os.path.basename(proof_dir),
        "file_count": manifest.get("file_count", 0),
        "combined_hash": manifest.get("combined_hash", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tamper_evidence_only": True,
        "identity_signature": False,
        "proof_integrity_is_not_truth": True,
        "promotion_allowed": False,
    })

    if verify_result:
        receipts.append({
            "schema_version": "integrity_receipt_v1",
            "event_type": "verification_completed",
            "verified": verify_result.get("verified", False),
            "files_checked": verify_result.get("files_checked", 0),
            "added": len(verify_result.get("added_files", [])),
            "removed": len(verify_result.get("removed_files", [])),
            "changed": len(verify_result.get("changed_files", [])),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tamper_evidence_only": True,
            "proof_integrity_is_not_truth": True,
        })

    path = os.path.join(target, "proof_integrity_receipts.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in receipts:
            f.write(json.dumps(r) + "\n")
    return path
