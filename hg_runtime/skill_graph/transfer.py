"""Advisory analogical transfer proposal helpers."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.skill_graph.schemas import SkillGraphError, validate_transfer_candidate


def create_transfer_candidate(
    skill_payload: Mapping[str, Any],
    *,
    target_domain: str,
    similarity_only: bool = False,
) -> dict[str, Any]:
    if similarity_only:
        raise SkillGraphError("surface_similarity_not_proof")
    source_skill_id = str(skill_payload.get("skill_id") or "unrecorded")
    return validate_transfer_candidate(
        {
            "source_skill_id": source_skill_id,
            "source_domain": str(skill_payload.get("domain", "")),
            "target_domain": target_domain,
            "analogy": "procedure shape may transfer only after verification",
            "evidence_refs": list(skill_payload.get("evidence_refs", [])),
            "verification_requirements": ["focused target-domain test", "operator review"],
            "negative_transfer_refs": [],
            "status": "candidate",
            "claim_boundary": "advisory_only",
            "authority_refs": list(skill_payload.get("authority_refs", [])),
        }
    )


__all__ = ["create_transfer_candidate"]
