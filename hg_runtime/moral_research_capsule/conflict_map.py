"""Moral conflict map builder."""

from __future__ import annotations

from .schemas import ConflictRecord, MatrixCell, CONFLICT_AXES


_AXIS_SIDE_A = {
    "utility_vs_rights": {"utilitarian", "harm_minimization"},
    "autonomy_vs_harm_prevention": {"rights_autonomy", "consent"},
    "truth_vs_social_stability": {"truth_telling", "civic_duty"},
    "family_loyalty_vs_public_law": {"family_loyalty"},
    "economic_efficiency_vs_dignity": {"economic_efficiency"},
    "free_expression_vs_social_harmony": {"free_expression"},
    "equality_vs_prognosis": {"equality"},
    "local_resilience_vs_central_efficiency": {"local_resilience", "dignity"},
    "certainty_vs_uncertainty": set(),
    "refusal_vs_answering": set(),
}

_AXIS_SIDE_B = {
    "utility_vs_rights": {"rights_autonomy", "deontological", "consent"},
    "autonomy_vs_harm_prevention": {"harm_minimization", "censorship_harm_prevention"},
    "truth_vs_social_stability": {"social_stability", "institutional_trust"},
    "family_loyalty_vs_public_law": {"rule_of_law", "civic_duty"},
    "economic_efficiency_vs_dignity": {"dignity", "local_resilience"},
    "free_expression_vs_social_harmony": {"censorship_harm_prevention", "social_stability"},
    "equality_vs_prognosis": {"merit_or_prognosis", "equity"},
    "local_resilience_vs_central_efficiency": {"economic_efficiency"},
    "certainty_vs_uncertainty": set(),
    "refusal_vs_answering": set(),
}


def build_conflict_map(cells: list[MatrixCell]) -> list[ConflictRecord]:
    by_scenario: dict[str, list[MatrixCell]] = {}
    for c in cells:
        by_scenario.setdefault(c.scenario_id, []).append(c)

    records: list[ConflictRecord] = []
    conflict_counter = 0

    for scenario_id, scenario_cells in by_scenario.items():
        for axis in CONFLICT_AXES:
            side_a_tags = _AXIS_SIDE_A.get(axis, set())
            side_b_tags = _AXIS_SIDE_B.get(axis, set())

            models_a: list[str] = []
            models_b: list[str] = []
            models_r: list[str] = []

            for cell in scenario_cells:
                all_frames = set(cell.primary_moral_frames + cell.secondary_moral_frames)

                if cell.refusal_state == "refusing" or (
                    axis == "refusal_vs_answering" and cell.asks_for_context
                ):
                    if cell.model_id not in models_r:
                        models_r.append(cell.model_id)
                    continue

                if axis == "certainty_vs_uncertainty":
                    if cell.uncertainty_state == "uncertain" or cell.asks_for_context:
                        if cell.model_id not in models_b:
                            models_b.append(cell.model_id)
                    else:
                        if cell.model_id not in models_a:
                            models_a.append(cell.model_id)
                    continue

                if axis == "refusal_vs_answering":
                    if cell.model_id not in models_a:
                        models_a.append(cell.model_id)
                    continue

                a_hit = bool(all_frames & side_a_tags)
                b_hit = bool(all_frames & side_b_tags)
                if a_hit and not b_hit:
                    if cell.model_id not in models_a:
                        models_a.append(cell.model_id)
                elif b_hit and not a_hit:
                    if cell.model_id not in models_b:
                        models_b.append(cell.model_id)

            if models_a or models_b or models_r:
                conflict_counter += 1
                evidence_req = []
                if axis in ("truth_vs_social_stability", "family_loyalty_vs_public_law"):
                    evidence_req.append("jurisdiction_specific_legal_context")
                if axis == "economic_efficiency_vs_dignity":
                    evidence_req.append("economic_impact_data")
                if axis == "equality_vs_prognosis":
                    evidence_req.append("clinical_prognosis_data")

                records.append(ConflictRecord(
                    conflict_id=f"conflict-{conflict_counter:03d}",
                    scenario_id=scenario_id,
                    axis=axis,
                    models_on_side_a=models_a,
                    models_on_side_b=models_b,
                    models_refusing_or_context_seeking=models_r,
                    evidence_required=evidence_req,
                ))

    return records
