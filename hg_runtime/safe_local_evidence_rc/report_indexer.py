"""Index phase reports for SLE-RC audit."""

from __future__ import annotations

from pathlib import Path

COMPONENT_REPORTS = {
    "WMBR": "docs/reports/phases/CAGI_WMBR_TRANCHE_CONSOLIDATION_REPORT.md",
    "AIS": "docs/reports/phases/SAFE_LOCAL_EVIDENCE_ALPHA_REPORT.md",
    "LEB": "docs/reports/phases/LEB_LOCAL_EVIDENCE_BRIDGE_CONSOLIDATION_REPORT.md",
    "ORP": "docs/reports/phases/REVIEWED_LOCAL_EVIDENCE_BETA_REPORT.md",
    "SQP": "docs/reports/phases/SQP_SOURCE_QUALITY_PROVENANCE_CONSOLIDATION_REPORT.md",
    "EWP": "docs/reports/phases/EWP_EVIDENCE_WORKBENCH_PACKET_CONSOLIDATION_REPORT.md",
    "OEC": "docs/reports/phases/OEC_OPERATOR_EVIDENCE_CORPUS_CONSOLIDATION_REPORT.md",
    "OES": "docs/reports/phases/OES_OPERATOR_EVIDENCE_SOAK_CONSOLIDATION_REPORT.md",
    "DIB": "docs/reports/phases/DIB_DOCUMENT_INTAKE_BOUNDARY_CONSOLIDATION_REPORT.md",
    "DTX": "docs/reports/phases/DTX_SAFE_TEXT_DOCUMENT_EXCHANGE_CONSOLIDATION_REPORT.md",
}


def build_report_index(root: Path) -> dict:
    entries = []
    for family, report_path in COMPONENT_REPORTS.items():
        exists = (root / report_path).exists()
        entries.append(
            {
                "component_family": family,
                "report_path": report_path,
                "report_exists": exists,
            }
        )
    return {
        "entry_count": len(entries),
        "entries": entries,
        "all_present": all(row["report_exists"] for row in entries),
    }
