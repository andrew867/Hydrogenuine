"""Research document builder for moral research capsule."""

from __future__ import annotations

from .schemas import (
    ConflictRecord, EvidenceGapTask, MatrixCell, ResearchDocument,
    SourceRecord, UncertaintyRecord,
)


def build_research_document(
    question: str,
    scenario_count: int,
    model_count: int,
    fixture_response_count: int,
    matrix_cells: list[MatrixCell],
    conflicts: list[ConflictRecord],
    evidence_gaps: list[EvidenceGapTask],
    uncertainty_records: list[UncertaintyRecord],
    source_records: list[SourceRecord],
) -> ResearchDocument:
    scenario_ids = sorted(set(c.scenario_id for c in matrix_cells))
    model_ids = sorted(set(c.model_id for c in matrix_cells))

    active_conflicts = [c for c in conflicts if c.models_on_side_a or c.models_on_side_b]
    conflict_axes = sorted(set(c.axis for c in active_conflicts))

    doc = ResearchDocument(
        document_id="mrc-research-doc-v1",
        question=question,
        scenario_suite_summary=(
            f"{scenario_count} scenarios covering trolley variants, triage, "
            f"whistleblower, family loyalty, bribery, censorship, economic triage, "
            f"and AI harm ranking."
        ),
        model_cohort_summary=(
            f"{model_count} model metadata entries in cohort registry. "
            f"{len(model_ids)} fixture models with responses. "
            f"No live model calls performed."
        ),
        fixture_limitation=(
            f"All {fixture_response_count} responses are deterministic fixtures. "
            f"No live model inference was performed. Results reflect fixture "
            f"archetypes, not real model behavior."
        ),
        perspective_matrix_summary=(
            f"{len(matrix_cells)} matrix cells across {len(scenario_ids)} scenarios "
            f"and {len(model_ids)} fixture models. Each cell links to a response receipt."
        ),
        moral_conflict_map_summary=(
            f"{len(active_conflicts)} active conflict records across axes: "
            f"{', '.join(conflict_axes[:5])}{'...' if len(conflict_axes) > 5 else ''}. "
            f"No adjudication performed. No moral truth claimed."
        ),
        evidence_gaps_summary=(
            f"{len(evidence_gaps)} evidence gap tasks identified. "
            f"None authorize action. None authorize tools. "
            f"All require operator review."
        ),
        uncertainty_ledger_summary=(
            f"{len(uncertainty_records)} uncertainty records. "
            f"Key: fixture-only limitation, model cohort limitation, "
            f"overtraining risk for trolley variants."
        ),
        what_was_observed=(
            f"Fixture models diverge on moral framing: utility-forward models "
            f"tend to minimize aggregate harm; rights-forward models emphasize "
            f"autonomy and consent; stability-forward models emphasize social trust; "
            f"procedural models ask for transparent criteria; refusal models ask "
            f"for context. Some fixtures intentionally overclaim culture or moral certainty."
        ),
        what_was_not_proven=(
            "No moral conclusion was proven. No cultural claim was validated. "
            "No model consensus was treated as truth. No evidence gap was resolved. "
            "No population preference was measured. No legal framework was applied."
        ),
        operator_review_notes=(
            "Operator should review: (1) evidence gap tasks before any research action; "
            "(2) cultural overclaim detections; (3) conflict map for research priorities; "
            "(4) uncertainty ledger for fixture limitations."
        ),
        next_steps=(
            "Plan a controlled comparable local-model moral research soak using "
            "this fixture harness, starting with safe whitelisted 4B-8B local models "
            "only, no remote providers, no live internet, and operator-reviewed "
            "scenario selection."
        ),
    )
    doc.disclaimers = doc.default_disclaimers()
    return doc


def render_research_document_md(doc: ResearchDocument) -> str:
    lines = [
        f"# Cross-Model Moral Research Document",
        "",
        f"**Document ID**: {doc.document_id}",
        f"**Question**: {doc.question}",
        f"**Advisory only**: {doc.advisory_only}",
        "",
        "## Disclaimers",
        "",
    ]
    for d in doc.disclaimers:
        lines.append(f"- {d}")
    lines += [
        "",
        "## Scenario Suite",
        doc.scenario_suite_summary,
        "",
        "## Model Cohort",
        doc.model_cohort_summary,
        "",
        "## Fixture Limitation",
        doc.fixture_limitation,
        "",
        "## Perspective Matrix",
        doc.perspective_matrix_summary,
        "",
        "## Moral Conflict Map",
        doc.moral_conflict_map_summary,
        "",
        "## Evidence Gaps",
        doc.evidence_gaps_summary,
        "",
        "## Uncertainty Ledger",
        doc.uncertainty_ledger_summary,
        "",
        "## What Was Observed",
        doc.what_was_observed,
        "",
        "## What Was NOT Proven",
        doc.what_was_not_proven,
        "",
        "## Operator Review Notes",
        doc.operator_review_notes,
        "",
        "## Next Steps",
        doc.next_steps,
        "",
    ]
    return "\n".join(lines)
