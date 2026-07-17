"""Deterministic SLE-RC-0 schema foundation fixtures."""

from __future__ import annotations

from hg_runtime.safe_local_evidence_rc.rc_artifact_index import build_rc_artifact_index, build_rc_release_risk_record
from hg_runtime.safe_local_evidence_rc.rc_boundary_assertions import build_default_boundary_assertions
from hg_runtime.safe_local_evidence_rc.rc_component_status import build_rc_component_status
from hg_runtime.safe_local_evidence_rc.rc_manifest import build_rc_manifest, build_safe_local_evidence_rc
from hg_runtime.safe_local_evidence_rc.schemas import COMPONENT_CONSOLIDATION, COMPONENT_FAMILIES, RECORD_TYPES


def build_sle_rc0_fixture_records() -> dict:
    rc = build_safe_local_evidence_rc(rc_id="sle-rc-fixture-v1")
    manifest = build_rc_manifest(manifest_id="sle-rc0-manifest-fixture", component_count=len(COMPONENT_FAMILIES))
    statuses = []
    for i, family in enumerate(COMPONENT_FAMILIES, start=1):
        proof_root, expected = COMPONENT_CONSOLIDATION[family]
        statuses.append(
            build_rc_component_status(
                status_id=f"rc-status-{i:03d}",
                component_family=family,
                proof_bundle=f"docs/proofs/autonomous_agent_zero/{proof_root}/fixture",
                gate_verdict=expected,
                expected_verdict=expected,
            )
        )
    assertions = build_default_boundary_assertions()
    artifact_index = build_rc_artifact_index(
        index_id="rc-artifact-index-fixture",
        entries=[{"component_family": s["component_family"], "proof_bundle": s["proof_bundle"]} for s in statuses],
    )
    risk = build_rc_release_risk_record(
        risk_id="rc_risk_phase19_001",
        risk_key="phase19_yellow_preserved",
        severity="medium",
        detail="Phase 19 remains YELLOW due to recorded debug dispatch ledger pollution.",
    )
    return {
        "safe_local_evidence_rc": rc,
        "rc_manifest": manifest,
        "rc_component_statuses": statuses,
        "rc_boundary_assertions": assertions,
        "rc_artifact_index": artifact_index,
        "rc_release_risk_record": risk,
        "record_types": sorted(RECORD_TYPES),
        "component_families": list(COMPONENT_FAMILIES),
    }
