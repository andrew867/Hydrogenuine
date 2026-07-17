"""P30 knowledge acquisition policy builder."""

from __future__ import annotations

from hg_runtime.knowledge_acquisition_loop.hashing import with_hash
from hg_runtime.knowledge_acquisition_loop.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    P30_INVARIANTS,
    assert_neutral,
)


def build_knowledge_acquisition_policy(*, policy_id: str = "p30-knowledge-acquisition-policy-v1") -> dict:
    record = {
        "record_type": "knowledge_acquisition_policy_v1",
        "schema_version": "1",
        "policy_id": policy_id,
        "provider_mode": PROVIDER_MODE,
        "live_web_enabled": False,
        "external_provider_enabled": False,
        "arbitrary_ingestion_enabled": False,
        "pdf_ocr_enabled": False,
        "html_parsing_enabled": False,
        "automatic_belief_promotion_enabled": False,
        "operator_review_required": True,
        "evidence_required": True,
        "source_quality_required": True,
        "provenance_required": True,
        "sandbox_only": True,
        "fixture_only": True,
        "acquired_claim_is_not_truth": True,
        "acquisition_result_is_not_belief": True,
        "source_is_not_authority": True,
        "source_quality_is_not_truth": True,
        "provenance_is_not_authority": True,
        "acquisition_task_is_not_action": True,
        "invariants": P30_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "acquired_claim_treated_as_truth": False,
        "acquisition_result_treated_as_belief": False,
        "belief_promotion_automatic": False,
        "authority_granted": False,
        "tools_authorized": False,
        "live_external_side_effects_created": False,
    }
    with_hash(record, "policy_hash")
    assert_neutral(record)
    return record
