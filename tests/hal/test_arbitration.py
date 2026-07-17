"""HAL Phase 1 arbitration unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_hal import (
    ArbitrationCandidate,
    ArbitrationRequest,
    arbitrate,
    arbitration_recorded_draft,
    arbitration_requested_draft,
)
from hg_hal.arbitration import decision_ref_for_result


def _request(**overrides) -> ArbitrationRequest:
    base = ArbitrationRequest(
        request_id="hal_req_1",
        proposal_ref="prop_1",
        candidates=(
            ArbitrationCandidate(
                candidate_id="cand_a",
                action_ref="act_a",
                capability_id="cap.oea_stub_log",
                effect_class="audit_log",
                priority=1,
            ),
        ),
        context_refs=("evt_ctx",),
    )
    if not overrides:
        return base
    return ArbitrationRequest(
        request_id=overrides.get("request_id", base.request_id),
        proposal_ref=overrides.get("proposal_ref", base.proposal_ref),
        candidates=overrides.get("candidates", base.candidates),
        context_refs=overrides.get("context_refs", base.context_refs),
        aep_modulation_refs=overrides.get("aep_modulation_refs", base.aep_modulation_refs),
        aep_max_severity=overrides.get("aep_max_severity", base.aep_max_severity),
        scrutiny_depth_delta=overrides.get("scrutiny_depth_delta", base.scrutiny_depth_delta),
    )


def test_same_request_produces_deterministic_arbitration_result():
    first = arbitrate(_request())
    second = arbitrate(_request())
    assert first.to_payload() == second.to_payload()
    assert first.routing == "ACCEPT"
    assert first.selected_candidate_ref == "act_a"


def test_empty_candidates_no_op():
    result = arbitrate(_request(candidates=()))
    assert result.routing == "NO_OP"
    assert result.reason_code == "queue_empty"


def test_two_candidates_accept_and_defer():
    request = _request(
        candidates=(
            ArbitrationCandidate(
                candidate_id="cand_b",
                action_ref="act_b",
                capability_id="cap.oea_stub_log",
                effect_class="audit_log",
                priority=1,
            ),
            ArbitrationCandidate(
                candidate_id="cand_a",
                action_ref="act_a",
                capability_id="cap.oea_stub_log",
                effect_class="audit_log",
                priority=0,
            ),
        )
    )
    result = arbitrate(request)
    assert result.routing == "ACCEPT"
    assert result.selected_candidate_ref == "act_b"
    assert "act_a" in result.deferred_candidate_refs


def test_aep_scrutiny_blocks_external_write(monkeypatch: pytest.MonkeyPatch):
    request = _request(
        aep_max_severity=8,
        candidates=(
            ArbitrationCandidate(
                candidate_id="cand_ext",
                action_ref="act_ext",
                capability_id="cap.external_write_scaffold",
                effect_class="external_write",
                priority=5,
            ),
        ),
    )
    result = arbitrate(request)
    assert result.routing == "REJECT"
    assert result.reason_code == "aep_scrutiny_blocked"


def test_aep_modulation_cannot_loosen_blocked_outcome():
    low = arbitrate(
        _request(
            aep_max_severity=8,
            scrutiny_depth_delta=0,
            candidates=(
                ArbitrationCandidate(
                    candidate_id="cand_ext",
                    action_ref="act_ext",
                    capability_id="cap.external_write_scaffold",
                    effect_class="external_write",
                ),
            ),
        )
    )
    claimed_loosen = arbitrate(
        _request(
            aep_max_severity=8,
            scrutiny_depth_delta=-5,
            candidates=(
                ArbitrationCandidate(
                    candidate_id="cand_ext",
                    action_ref="act_ext",
                    capability_id="cap.external_write_scaffold",
                    effect_class="external_write",
                ),
            ),
        )
    )
    assert low.routing == "REJECT"
    assert claimed_loosen.routing == "REJECT"


def test_hal_modules_have_no_permit_or_execution_imports():
    forbidden = (
        "PermitBinder",
        "mint_permit",
        "hg_ueak",
        "hg_oea",
        "requests.",
        "httpx.",
        "subprocess.",
    )
    for path in Path("hg_hal").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not reference {token}"


def test_hal_cannot_mint_permit_objects():
    result = arbitrate(_request())
    payload = result.to_payload()
    forbidden = {"permit_id", "permit_ref", "permit_hash", "grant", "allow_permit"}
    assert forbidden.isdisjoint(payload.keys())


def test_arbitration_drafts_have_no_bus_imports():
    request = _request()
    requested = arbitration_requested_draft(request, causal_parents=["evt_p"])
    recorded = arbitration_recorded_draft(
        arbitrate(request), causal_parents=["evt_p"]
    )
    assert requested["type"] == "HAL_ARBITRATION_REQUESTED"
    assert recorded["type"] == "HAL_ARBITRATION_RECORDED"
    assert recorded["payload"]["enforcement"] == "hal_phase1_arbitration_only"


def test_soar_binding_blocks_hal_accept():
    from hg_soar import run_soar

    proposal = {
        "event_id": "evt_p",
        "payload": {
            "proposal_id": "prop_defer",
            "kind": "candidate_action",
            "content": {
                "capability_id": "cap.oea_stub_log",
                "effect_class": "audit_log",
                "memory_stale": True,
            },
        },
    }
    soar_run = run_soar(proposal, context_refs=())
    request = _request().__class__(
        request_id="hal_req_soar_defer",
        proposal_ref="prop_defer",
        candidates=_request().candidates,
        context_refs=(),
        soar_run_ref=soar_run.request_id,
        soar_binding=soar_run.binding,
    )
    result = arbitrate(request)
    assert result.routing == "DEFER"
    assert result.reason_code == "soar_binding_defer"


def test_decision_ref_mapping():
    accept = arbitrate(_request())
    reject = arbitrate(
        _request(
            candidates=(
                ArbitrationCandidate(
                    candidate_id="cand_x",
                    action_ref="act_x",
                    capability_id="cap.external_post",
                    effect_class="external_write",
                ),
            )
        )
    )
    assert decision_ref_for_result(accept) == "dec_hal_accept"
    assert decision_ref_for_result(reject) == "dec_hal_reject"
