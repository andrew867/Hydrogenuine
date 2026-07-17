"""Report scanner — scan directories for forbidden claims across files.

The scanner is NOT authority. It is a guard. Scanning is NOT proof.
"""

from __future__ import annotations

import os

from hg_runtime.public_claims.public_claim_checker_v2 import (
    SCHEMA_VERSION,
    _INVARIANTS,
    check_report_file,
)


def scan_directory(
    directory: str,
    *,
    extensions: tuple = (".md", ".txt"),
    stop_panic: bool = False,
) -> dict:
    """Scan all files in directory matching extensions for forbidden claims.

    Returns a directory scan receipt.
    """
    file_results = []
    files_scanned = 0
    files_with_findings = 0
    total_flagged = 0

    for root, _dirs, files in os.walk(directory):
        for fname in sorted(files):
            if not any(fname.endswith(ext) for ext in extensions):
                continue

            fpath = os.path.join(root, fname)
            files_scanned += 1

            result = check_report_file(fpath, stop_panic=stop_panic)
            file_results.append(result)

            if result.get("flagged_count", 0) > 0 or result.get("blocked", False):
                files_with_findings += 1
            total_flagged += result.get("flagged_count", 0)

    all_clean = total_flagged == 0 and not stop_panic
    operator_review_required = total_flagged > 0 or stop_panic

    return {
        "schema": SCHEMA_VERSION,
        "receipt_type": "directory_scan",
        "directory": directory,
        "files_scanned": files_scanned,
        "files_with_findings": files_with_findings,
        "total_flagged": total_flagged,
        "file_results": file_results,
        "all_clean": all_clean,
        "operator_review_required": operator_review_required,
        **_INVARIANTS,
    }
