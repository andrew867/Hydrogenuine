"""SLE-RC-2 boundary matrix tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.safe_local_evidence_rc.artifact_index_builder import build_artifact_index
from hg_runtime.safe_local_evidence_rc.boundary_assertion_reader import all_required_assertions_present
from hg_runtime.safe_local_evidence_rc.boundary_matrix import build_boundary_matrix
from hg_runtime.safe_local_evidence_rc.schemas import BOUNDARY_ASSERTION_IDS, PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]


def _matrix():
    upstream = build_artifact_index(ROOT)["all_consolidations_green"]
    return build_boundary_matrix(ROOT, upstream_green=upstream)


def test_sle_rc2_all_boundary_assertions_present():
    layer = _matrix()
    assert all_required_assertions_present(layer["rc_boundary_assertions"])
    assert len(BOUNDARY_ASSERTION_IDS) == 25


def test_sle_rc2_phase19_yellow_assertion_passes():
    layer = _matrix()
    phase19 = next(row for row in layer["rc_boundary_assertions"] if row["assertion_key"] == "phase19_yellow_preserved")
    assert phase19["passed"] is True
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_sle_rc2_phase24_infrastructure_only_assertion_passes():
    layer = _matrix()
    phase24 = next(row for row in layer["rc_boundary_assertions"] if row["assertion_key"] == "phase24_infrastructure_only_preserved")
    assert phase24["passed"] is True
    assert PHASE24_STATUS == "infrastructure_only"


def test_sle_rc2_no_pdf_ocr_html_arbitrary():
    matrix = _matrix()["rc_boundary_matrix"]
    assert matrix["pdf_ingestion_enabled"] is False
    assert matrix["ocr_ingestion_enabled"] is False
    assert matrix["html_parsing_enabled"] is False
    assert matrix["arbitrary_file_ingestion_enabled"] is False
