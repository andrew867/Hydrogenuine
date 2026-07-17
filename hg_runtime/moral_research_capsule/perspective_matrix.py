"""Cross-model moral perspective matrix builder."""

from __future__ import annotations

from dataclasses import asdict

from .moral_frame_classifier import classify_moral_frames
from .receipt_classifier import classify_response
from .schemas import FixtureResponse, MatrixCell, ResponseReceipt


def build_perspective_matrix(
    responses: list[FixtureResponse],
    receipts: list[ResponseReceipt] | None = None,
) -> list[MatrixCell]:
    if receipts is None:
        receipts = [classify_response(r) for r in responses]
    receipt_map = {r.response_id: r for r in receipts}

    cells: list[MatrixCell] = []
    for resp in responses:
        receipt = receipt_map.get(resp.response_id)
        if receipt is None:
            continue
        frame = classify_moral_frames(resp)
        from .scenario_suite import get_scenario
        try:
            scenario = get_scenario(resp.scenario_id)
            decision_points = scenario.decision_points
        except KeyError:
            decision_points = ["unknown"]

        for dp in decision_points:
            cells.append(MatrixCell(
                scenario_id=resp.scenario_id,
                decision_point=dp,
                model_id=resp.model_id,
                decision_tendency=receipt.final_decision_tendency,
                primary_moral_frames=frame.primary_frames,
                secondary_moral_frames=frame.secondary_frames,
                social_assumptions=frame.social_assumptions,
                economic_assumptions=frame.economic_assumptions,
                legal_assumptions=frame.legal_assumptions,
                cultural_framing_claims=frame.cultural_framing_claims,
                refusal_state=frame.refusal_state,
                willingness_state=frame.willingness_state,
                uncertainty_state=frame.uncertainty_state,
                asks_for_context=frame.asks_for_context,
                evidence_gaps=frame.evidence_gaps,
                omissions=frame.omissions,
                overclaims=frame.overclaims,
                genericity=frame.genericity,
                source_response_id=resp.response_id,
                receipt_hash=receipt.receipt_hash,
            ))
    return cells


def matrix_cells_all_have_receipts(
    cells: list[MatrixCell], receipts: list[ResponseReceipt]
) -> bool:
    receipt_hashes = {r.receipt_hash for r in receipts}
    return all(c.receipt_hash in receipt_hashes for c in cells)
