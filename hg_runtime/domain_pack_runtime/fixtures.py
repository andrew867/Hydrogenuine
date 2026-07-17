"""Deterministic P28-0 schema fixtures."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_pack_policy import build_domain_pack_policy
from hg_runtime.domain_pack_runtime.domain_pack_record import (
    build_domain_pack_boundary_record,
    build_domain_pack_readiness_record,
    build_domain_pack_record,
    build_domain_pack_skill_link,
)
from hg_runtime.domain_pack_runtime.hashing import stable_hash, with_hash
from hg_runtime.domain_pack_runtime.schemas import PHASE19_VERDICT, PHASE24_STATUS, P28_INVARIANTS, assert_neutral


def build_p28_0_layer(repo_root: Path) -> dict:
    policy = build_domain_pack_policy()
    pack = build_domain_pack_record(
        pack_id="pack-fixture-sle_rc",
        domain_label="SLE-RC",
        skill_ids=["skill-fixture-001"],
        provenance_refs=["rc_artifact_index.json", "rc_boundary_matrix.json"],
        boundary_tags=["release_candidate_not_deployment", "evidence_not_truth"],
        capability_refs=["cap-sle_rc"],
        risk_refs=["rc_risk_001", "rc_risk_boundary_tag"],
    )
    link = build_domain_pack_skill_link(
        link_id="link-fixture-001",
        pack_id=pack["pack_id"],
        skill_id="skill-fixture-001",
        domain_label="SLE-RC",
        provenance_refs=pack["provenance_refs"],
    )
    boundary = build_domain_pack_boundary_record(
        boundary_id="boundary-fixture-001",
        pack_id=pack["pack_id"],
        boundary_tags=pack["boundary_tags"],
    )
    readiness = build_domain_pack_readiness_record(
        readiness_id="readiness-fixture-001",
        pack_id=pack["pack_id"],
        readiness_state="READY_FOR_REVIEW",
        review_notes=["fixture_pack_ready_for_operator_review"],
    )
    records = [policy, pack, link, boundary, readiness]
    manifest = {
        "record_type": "domain_pack_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p28-0-schema-fixture",
        "repo_root": str(repo_root),
        "record_count": len(records),
        "invariants": P28_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "explicit_manifest_only": True,
        "domain_pack_treated_as_permission": False,
        "readiness_treated_as_deployment_permission": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    replay = {
        "record_type": "domain_pack_replay_v1",
        "schema_version": "1",
        "replay_preserves_record_hashes": True,
        "receipt_chain_root": stable_hash({"hashes": [stable_hash(r) for r in records]}),
    }
    return {
        "policy": policy,
        "domain_packs": [pack],
        "domain_pack_skill_links": [link],
        "domain_pack_boundaries": [boundary],
        "domain_pack_readiness_records": [readiness],
        "manifest": manifest,
        "replay": replay,
        "records": records,
    }
