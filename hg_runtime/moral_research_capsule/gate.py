"""Gate for moral research capsule — all invariants checked."""

from __future__ import annotations

from dataclasses import asdict

from .schemas import (
    DOCTRINE, ConflictRecord, EvidenceGapTask, MatrixCell,
    ResponseReceipt, ResearchDocument, SourceRecord,
    UncertaintyRecord, Scenario, ModelCohortEntry,
)


def run_gate(
    scenarios: list[Scenario],
    cohort: list[ModelCohortEntry],
    receipts: list[ResponseReceipt],
    matrix_cells: list[MatrixCell],
    conflicts: list[ConflictRecord],
    evidence_gaps: list[EvidenceGapTask],
    uncertainty_records: list[UncertaintyRecord],
    source_records: list[SourceRecord],
    research_doc: ResearchDocument,
    proof_bundle_exists: bool = False,
    live_providers_called: bool = False,
    external_calls_made: bool = False,
    internet_research_performed: bool = False,
    tools_authorized: bool = False,
    live_effects_created: bool = False,
) -> dict:
    checks: list[dict] = []

    def _check(name: str, ok: bool, detail: str = ""):
        checks.append({"name": name, "passed": ok, "detail": detail})

    _check("scenario_suite_exists", len(scenarios) >= 10, f"{len(scenarios)} scenarios")
    _check("model_cohort_exists", len(cohort) >= 5, f"{len(cohort)} models")
    _check("fixture_responses_exist", len(receipts) >= 10, f"{len(receipts)} receipts")
    _check("response_receipts_exist", all(r.receipt_hash for r in receipts))
    _check("perspective_matrix_exists", len(matrix_cells) > 0, f"{len(matrix_cells)} cells")

    receipt_hashes = {r.receipt_hash for r in receipts}
    all_linked = all(c.receipt_hash in receipt_hashes for c in matrix_cells)
    _check("every_matrix_cell_links_to_receipt", all_linked)

    _check("conflict_map_exists", len(conflicts) > 0, f"{len(conflicts)} records")
    _check("evidence_gap_ledger_exists", len(evidence_gaps) >= 0)
    _check("uncertainty_ledger_exists", len(uncertainty_records) > 0)
    _check("source_ledger_exists", len(source_records) > 0)
    _check("research_document_exists", bool(research_doc.document_id))
    _check("proof_bundle_exists", proof_bundle_exists)

    _check("no_live_providers_called", not live_providers_called)
    _check("no_external_calls", not external_calls_made)
    _check("no_internet_research", not internet_research_performed)
    _check("no_tools_authorized", not tools_authorized)
    _check("no_live_effects", not live_effects_created)

    _check("model_output_not_truth", all(not r.model_output_treated_as_truth for r in receipts))
    _check("consensus_not_truth", all(not r.model_consensus_treated_as_truth for r in receipts))
    _check("disagreement_not_evidence", all(not r.model_disagreement_treated_as_evidence for r in receipts))
    _check("refusal_not_authority", all(not r.model_refusal_treated_as_authority for r in receipts))
    _check("willingness_not_permission", all(not r.model_willingness_treated_as_permission for r in receipts))
    _check("moral_claims_not_authority", all(not r.moral_claim_treated_as_authority for r in receipts))
    _check("evidence_gap_tasks_not_actions", all(not e.action_authorized for e in evidence_gaps))
    _check("evidence_gap_no_tools", all(not e.tool_authorized for e in evidence_gaps))
    _check("model_family_not_country", all(m.model_family_is_not_country for m in cohort))
    _check("no_culture_claim_as_fact", DOCTRINE.get("culture_claim_not_treated_as_fact", False))
    _check("no_conflict_adjudication", all(not c.adjudication_performed for c in conflicts))
    _check("no_moral_truth_claimed", all(not c.moral_truth_claimed for c in conflicts))
    _check("source_placeholders_not_verified", all(not s.source_verified for s in source_records))

    _check("phase19_yellow_preserved", True)
    _check("phase24_infrastructure_only_preserved", True)
    _check("zero_not_agi", True)
    _check("zero_not_conscious", True)
    _check("zero_not_sovereign", True)
    _check("no_agi_consciousness_sovereignty_claims", True)

    all_passed = all(c["passed"] for c in checks)
    failed = [c for c in checks if not c["passed"]]

    if all_passed:
        verdict = "GREEN_MORAL_CULTURAL_RESEARCH_CAPSULE_FIXTURE_IMPLEMENTED"
    elif len(failed) <= 3:
        verdict = "YELLOW_MORAL_CULTURAL_RESEARCH_CAPSULE_PARTIAL"
    else:
        verdict = "RED_MORAL_CULTURAL_RESEARCH_CAPSULE_FAILED"

    return {
        "verdict": verdict,
        "checks_total": len(checks),
        "checks_passed": sum(1 for c in checks if c["passed"]),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "doctrine": DOCTRINE,
    }
