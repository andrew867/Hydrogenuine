"""Document extraction receipts.

Every extraction is receipted. Extraction failure is preserved.
No promotion. No hiding errors.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def write_extraction_receipt(receipt: dict, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "document_extraction_receipts.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(receipt) + "\n")
    return path


def write_extraction_summary(receipts: list[dict], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    succeeded = sum(1 for r in receipts if r.get("status") == "succeeded")
    failed = sum(1 for r in receipts if r.get("status") == "error")
    yellow = sum(1 for r in receipts if "yellow" in r.get("status", "").lower())

    summary = {
        "schema_version": "document_extraction_summary_v1",
        "total_documents": len(receipts),
        "succeeded": succeeded,
        "failed": failed,
        "yellow": yellow,
        "total_chars_extracted": sum(r.get("chars_extracted", 0) for r in receipts),
        "ocr_used_count": sum(1 for r in receipts if r.get("ocr_used")),
        "extraction_is_not_truth": True,
        "promotion_allowed": False,
        "operator_review_required": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    path = os.path.join(out_dir, "extraction_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return path
