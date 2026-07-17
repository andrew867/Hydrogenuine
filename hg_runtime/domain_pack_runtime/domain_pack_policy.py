"""P28 domain pack policy builders."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.hashing import with_hash
from hg_runtime.domain_pack_runtime.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    P28_INVARIANTS,
    assert_neutral,
)


def build_domain_pack_policy(*, policy_id: str = "p28-domain-pack-policy-v1") -> dict:
    record = {
        "record_type": "domain_pack_policy_v1",
        "schema_version": "1",
        "policy_id": policy_id,
        "provider_mode": PROVIDER_MODE,
        "explicit_manifest_only": True,
        "provenance_required": True,
        "domain_pack_is_not_permission": True,
        "domain_label_is_not_expertise": True,
        "readiness_is_not_deployment_permission": True,
        "skill_link_is_not_authority": True,
        "automatic_belief_promotion_enabled": False,
        "tool_authorization_enabled": False,
        "live_effects_enabled": False,
        "web_enabled": False,
        "external_provider_enabled": False,
        "pdf_ocr_enabled": False,
        "html_enabled": False,
        "deletion_enabled": False,
        "invariants": P28_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        **{k: False for k in (
            "domain_pack_treated_as_permission",
            "domain_label_treated_as_expertise",
            "readiness_treated_as_deployment_permission",
            "skill_link_treated_as_authority",
            "belief_promotion_automatic",
            "authority_granted",
            "tools_authorized",
            "live_external_side_effects_created",
        )},
    }
    with_hash(record, "policy_hash")
    assert_neutral(record)
    return record
