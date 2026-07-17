"""Build SLE-RC boundary assertion matrix."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.safe_local_evidence_rc.rc_boundary_assertions import (
    build_default_boundary_assertions,
    build_rc_boundary_failure,
)
from hg_runtime.safe_local_evidence_rc.schemas import (
    BOUNDARY_ASSERTION_IDS,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    record_hash,
)


def build_boundary_matrix(root: Path, *, upstream_green: bool) -> dict:
    assertions = build_default_boundary_assertions()
    failures = []
    for row in assertions:
        if not row["passed"]:
            failures.append(
                build_rc_boundary_failure(
                    failure_id=f"rc-fail-{row['assertion_key']}",
                    assertion_key=row["assertion_key"],
                    reason=row.get("detail") or "assertion_failed",
                )
            )
    if not upstream_green:
        failures.append(
            build_rc_boundary_failure(
                failure_id="rc-fail-upstream_not_green",
                assertion_key="upstream_consolidations_green",
                reason="upstream_consolidation_not_green",
            )
        )
    matrix = {
        "schema_version": "1",
        "record_type": "rc_boundary_matrix_v1",
        "provider_mode": PROVIDER_MODE,
        "assertion_count": len(BOUNDARY_ASSERTION_IDS),
        "passed_count": sum(1 for row in assertions if row["passed"]),
        "failure_count": len(failures),
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "safe_text_markdown_only": True,
        "pdf_ingestion_enabled": False,
        "ocr_ingestion_enabled": False,
        "html_parsing_enabled": False,
        "arbitrary_file_ingestion_enabled": False,
        "upstream_consolidations_green": upstream_green,
    }
    matrix["matrix_hash"] = record_hash(matrix)
    manifest = {
        "schema_version": "1",
        "assertion_count": len(assertions),
        "failure_count": len(failures),
        "manifest_hash": record_hash({"matrix": matrix, "assertions": assertions}),
    }
    return {
        "rc_boundary_matrix": matrix,
        "rc_boundary_assertions": assertions,
        "rc_boundary_failures": failures,
        "rc_boundary_matrix_manifest": manifest,
        "all_passed": not failures,
    }
