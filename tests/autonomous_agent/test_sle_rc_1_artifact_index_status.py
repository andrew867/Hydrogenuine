"""SLE-RC-1 artifact index and component status tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_sle_rc_1_artifact_index_gate.py"

_spec = importlib.util.spec_from_file_location("sle_rc1_gate", _GATE_PATH)
sle_rc1_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sle_rc1_gate)

from hg_runtime.safe_local_evidence_rc.artifact_index_builder import build_artifact_index  # noqa: E402
from hg_runtime.safe_local_evidence_rc.component_status_auditor import audit_component_statuses  # noqa: E402
from hg_runtime.safe_local_evidence_rc.schemas import COMPONENT_FAMILIES, PHASE19_VERDICT, PHASE24_STATUS  # noqa: E402


def test_sle_rc1_artifact_index_covers_all_families():
    layer = build_artifact_index(ROOT)
    families = {row["component_family"] for row in layer["entries"]}
    assert set(COMPONENT_FAMILIES) <= families


def test_sle_rc1_does_not_infer_green_from_presence_only():
    audit = audit_component_statuses(ROOT, base_head="test-head")
    assert all(not row["green_inferred_from_presence_only"] for row in audit["rc_component_statuses"])


def test_sle_rc1_preserves_phase19_yellow():
    audit = audit_component_statuses(ROOT, base_head="test-head")
    assert audit["phase19_yellow_preserved"] is True
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_sle_rc1_preserves_phase24_infrastructure_only():
    audit = audit_component_statuses(ROOT, base_head="test-head")
    assert audit["phase24_infrastructure_only_preserved"] is True
    assert PHASE24_STATUS == "infrastructure_only"


def test_sle_rc1_report_index_present():
    layer = build_artifact_index(ROOT)
    assert layer["report_index"]["entry_count"] == len(COMPONENT_FAMILIES)
