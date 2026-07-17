"""Evidence gap ledger — tasks are NOT actions, NOT authorized."""

from __future__ import annotations

from .moral_frame_classifier import classify_moral_frames
from .schemas import EvidenceGapTask, FixtureResponse


_GAP_TEMPLATES = {
    "economic_claims_without_data": {
        "gap_type": "economic_claim_unsourced",
        "required_evidence_kind": "economic_impact_study",
        "suggested_source_kind": "government_statistics_or_academic_study",
        "jurisdiction_or_population_needed": "specific_jurisdiction_required",
    },
    "cultural_claims_without_evidence": {
        "gap_type": "cultural_claim_unsourced",
        "required_evidence_kind": "cross_cultural_survey_or_ethnography",
        "suggested_source_kind": "peer_reviewed_research",
        "jurisdiction_or_population_needed": "specific_population_required",
    },
    "population_claim_without_survey": {
        "gap_type": "population_claim_unsourced",
        "required_evidence_kind": "representative_survey_data",
        "suggested_source_kind": "nationally_representative_survey",
        "jurisdiction_or_population_needed": "specific_population_required",
    },
}


def build_evidence_gap_ledger(
    responses: list[FixtureResponse],
) -> list[EvidenceGapTask]:
    tasks: list[EvidenceGapTask] = []
    counter = 0

    for resp in responses:
        frame = classify_moral_frames(resp)
        for gap_key in frame.evidence_gaps:
            template = _GAP_TEMPLATES.get(gap_key, {})
            counter += 1
            tasks.append(EvidenceGapTask(
                task_id=f"egap-{counter:04d}",
                scenario_id=resp.scenario_id,
                model_id=resp.model_id,
                claim_text=f"Model {resp.model_id} made claim classified as {gap_key}",
                gap_type=template.get("gap_type", gap_key),
                required_evidence_kind=template.get("required_evidence_kind", "unspecified"),
                suggested_source_kind=template.get("suggested_source_kind", "unspecified"),
                jurisdiction_or_population_needed=template.get("jurisdiction_or_population_needed", "unspecified"),
                action_authorized=False,
                tool_authorized=False,
                operator_review_required=True,
            ))

    for resp in responses:
        frame = classify_moral_frames(resp)
        for overclaim in frame.overclaims:
            counter += 1
            tasks.append(EvidenceGapTask(
                task_id=f"egap-{counter:04d}",
                scenario_id=resp.scenario_id,
                model_id=resp.model_id,
                claim_text=f"Overclaim: {overclaim}",
                gap_type="overclaim_requiring_evidence",
                required_evidence_kind="primary_source_or_survey",
                suggested_source_kind="peer_reviewed_or_government_source",
                jurisdiction_or_population_needed="depends_on_claim",
                action_authorized=False,
                tool_authorized=False,
                operator_review_required=True,
            ))

    return tasks
