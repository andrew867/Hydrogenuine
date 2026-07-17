"""P28 domain pack record builders."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.hashing import with_hash
from hg_runtime.domain_pack_runtime.schemas import assert_neutral, neutral_flags


def build_domain_pack_record(
    *,
    pack_id: str,
    domain_label: str,
    skill_ids: list[str],
    provenance_refs: list[str],
    boundary_tags: list[str],
    capability_refs: list[str] | None = None,
    risk_refs: list[str] | None = None,
) -> dict:
    record = {
        "record_type": "domain_pack_record_v1",
        "schema_version": "1",
        "pack_id": pack_id,
        "domain_label": domain_label,
        "skill_ids": list(skill_ids),
        "provenance_refs": list(provenance_refs),
        "boundary_tags": list(boundary_tags),
        "capability_refs": list(capability_refs or []),
        "risk_refs": list(risk_refs or ["rc_risk_001", "rc_risk_boundary_tag"]),
        "domain_pack_is_not_permission": True,
        "domain_label_is_not_expertise": True,
        "doctrine_note": "Domain label is not expertise; pack is not permission.",
        **neutral_flags(),
    }
    with_hash(record, "pack_hash")
    assert_neutral(record)
    return record


def build_domain_pack_skill_link(
    *,
    link_id: str,
    pack_id: str,
    skill_id: str,
    domain_label: str,
    provenance_refs: list[str],
) -> dict:
    record = {
        "record_type": "domain_pack_skill_link_v1",
        "schema_version": "1",
        "link_id": link_id,
        "pack_id": pack_id,
        "skill_id": skill_id,
        "domain_label": domain_label,
        "provenance_refs": list(provenance_refs),
        "skill_link_is_not_authority": True,
        "domain_label_is_not_expertise": True,
        **neutral_flags(),
    }
    with_hash(record, "link_hash")
    assert_neutral(record)
    return record


def build_domain_pack_boundary_record(
    *,
    boundary_id: str,
    pack_id: str,
    boundary_tags: list[str],
    refusal_reasons: list[str] | None = None,
) -> dict:
    record = {
        "record_type": "domain_pack_boundary_record_v1",
        "schema_version": "1",
        "boundary_id": boundary_id,
        "pack_id": pack_id,
        "boundary_tags": list(boundary_tags),
        "refusal_reasons": list(refusal_reasons or []),
        "domain_pack_is_not_permission": True,
        "readiness_is_not_deployment_permission": True,
        **neutral_flags(),
    }
    with_hash(record, "boundary_hash")
    assert_neutral(record)
    return record


def build_domain_pack_readiness_record(
    *,
    readiness_id: str,
    pack_id: str,
    readiness_state: str,
    review_notes: list[str] | None = None,
    refusal_reason: str | None = None,
) -> dict:
    record = {
        "record_type": "domain_pack_readiness_record_v1",
        "schema_version": "1",
        "readiness_id": readiness_id,
        "pack_id": pack_id,
        "readiness_state": readiness_state,
        "review_notes": list(review_notes or []),
        "refusal_reason": refusal_reason,
        "readiness_is_not_deployment_permission": True,
        "domain_pack_is_not_permission": True,
        **neutral_flags(),
    }
    with_hash(record, "readiness_hash")
    assert_neutral(record)
    return record
