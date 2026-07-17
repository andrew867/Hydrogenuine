"""Domain readiness gate evaluation."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_boundary_matrix import build_domain_boundary_matrix
from hg_runtime.domain_pack_runtime.domain_pack_builder import build_domain_packs
from hg_runtime.domain_pack_runtime.domain_readiness import build_readiness_record_for_pack
from hg_runtime.domain_pack_runtime.domain_refusal import build_boundary_record_for_pack, detect_boundary_refusal
from hg_runtime.domain_pack_runtime.hashing import with_hash
from hg_runtime.domain_pack_runtime.schemas import assert_neutral


def evaluate_domain_readiness_gate(repo_root: Path) -> dict:
    layer = build_domain_packs(repo_root)
    readiness_records = []
    refusal_records = []
    for pack in layer["domain_packs"]:
        boundary = build_boundary_record_for_pack(pack)
        refused, _ = detect_boundary_refusal(pack)
        readiness = build_readiness_record_for_pack(pack, boundary_record=boundary, refused=refused)
        readiness_records.append(readiness)
        if readiness["readiness_state"] == "REFUSED_BY_BOUNDARY":
            refusal_records.append(
                {
                    "record_type": "domain_refusal_v1",
                    "schema_version": "1",
                    "pack_id": pack["pack_id"],
                    "refusal_reason": readiness.get("refusal_reason"),
                    "readiness_is_not_deployment_permission": True,
                }
            )
    boundary_matrix = build_domain_boundary_matrix()
    manifest = {
        "record_type": "domain_readiness_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p28-2-domain-readiness",
        "pack_count": len(layer["domain_packs"]),
        "ready_for_review_count": sum(
            1 for row in readiness_records if row["readiness_state"] == "READY_FOR_REVIEW"
        ),
        "not_ready_count": sum(1 for row in readiness_records if row["readiness_state"] == "NOT_READY"),
        "refused_count": sum(1 for row in readiness_records if row["readiness_state"] == "REFUSED_BY_BOUNDARY"),
        "readiness_is_not_deployment_permission": True,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    return {
        **layer,
        "domain_pack_readiness_records": readiness_records,
        "domain_refusal_records": refusal_records,
        "boundary_matrix": boundary_matrix,
        "readiness_manifest": manifest,
    }
