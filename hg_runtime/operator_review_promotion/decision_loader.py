"""Load deterministic ORP-1 ledger inputs from LEB fixtures."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.ais_integration import build_ais_integration
from hg_runtime.local_evidence_bridge.evidence_quarantine_loop import (
    build_loop_fixture_receipts,
    build_retraction_quarantine_loop,
)
from hg_runtime.local_evidence_bridge.evidence_review_queue import build_fixture_targets, build_review_queue


def load_operator_review_inputs(root: Path) -> dict:
    review_queue = build_review_queue(targets=build_fixture_targets(root), fever_level="NORMAL")
    ais = build_ais_integration(root)
    retraction_quarantine = build_retraction_quarantine_loop(build_loop_fixture_receipts())
    return {
        "leb5_review_tasks": review_queue["tasks"],
        "leb5_manifest": review_queue["manifest"],
        "leb6_manifest": ais["manifest"],
        "leb6_health_findings": ais["health"],
        "leb6_quarantine_candidates": ais["quarantine"],
        "leb6_security_findings": ais["security"],
        "leb7_manifest": retraction_quarantine["manifest"],
        "leb7_retractions": retraction_quarantine["retractions"],
        "leb7_quarantines": retraction_quarantine["quarantines"],
    }
