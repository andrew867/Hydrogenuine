"""Domain pack boundary matrix."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.schemas import PHASE19_VERDICT, PHASE24_STATUS


def build_domain_boundary_matrix() -> dict:
    return {
        "domain_pack_is_not_permission": True,
        "domain_label_is_not_expertise": True,
        "readiness_is_not_deployment_permission": True,
        "skill_link_is_not_authority": True,
        "tool_authorization": False,
        "live_effects": False,
        "web": False,
        "external_providers": False,
        "pdf_ocr": False,
        "html": False,
        "arbitrary_ingestion": False,
        "automatic_belief_promotion": False,
        "deployment_permit": False,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
    }
