"""P27 skill graph policy builders."""

from __future__ import annotations

from hg_runtime.skill_graph.hashing import with_hash
from hg_runtime.skill_graph.p27_schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    P27_INVARIANTS,
    assert_neutral,
)


def build_skill_graph_policy(*, policy_id: str = "p27-skill-graph-policy-v1") -> dict:
    record = {
        "record_type": "skill_graph_policy_v1",
        "schema_version": "1",
        "policy_id": policy_id,
        "provider_mode": PROVIDER_MODE,
        "explicit_manifest_only": True,
        "memory_source_required": True,
        "provenance_required": True,
        "skill_is_not_authority": True,
        "skill_reuse_is_not_transfer_proof": True,
        "transfer_candidate_is_not_competence": True,
        "automatic_belief_promotion_enabled": False,
        "tool_authorization_enabled": False,
        "live_effects_enabled": False,
        "web_enabled": False,
        "external_provider_enabled": False,
        "pdf_ocr_enabled": False,
        "html_enabled": False,
        "deletion_enabled": False,
        "invariants": P27_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        **{k: False for k in (
            "skill_treated_as_authority",
            "transfer_treated_as_proof",
            "belief_promotion_automatic",
            "authority_granted",
            "tools_authorized",
            "live_external_side_effects_created",
        )},
    }
    with_hash(record, "policy_hash")
    assert_neutral(record)
    return record
