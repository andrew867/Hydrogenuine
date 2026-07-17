"""TEP-D organ emission tests — per-organ wrapped emission, naked fenced, authority semantics."""

from __future__ import annotations

import pytest

from hg_runtime.agency_routing_boundary.tep_emission import run_arb_fixture_emission
from hg_runtime.agent_zero_heart_mind.tep_emission import run_a0_hm_fixture_emission
from hg_runtime.emergent_gap_identifier.tep_emission import run_egi_fixture_emission
from hg_runtime.external_relation_boundary.tep_emission import run_erb_fixture_emission
from hg_runtime.internal_mediation_boundary.tep_emission import run_imb_fixture_emission
from hg_runtime.internal_power_boundary.tep_emission import run_ipb_fixture_emission
from hg_runtime.operator_power_boundary.tep_emission import run_opb_fixture_emission
from hg_runtime.operator_review_intake.tep_emission import run_ori_fixture_emission
from hg_runtime.organism_coherence.tep_emission import run_h8_fixture_emission
from hg_runtime.reproduction_inheritance_boundary.tep_emission import run_rib_fixture_emission
from hg_runtime.translation_envelope_protocol.fixtures import (
    gpp_permit_evidence_fixture,
    naked_scalar_fixture,
    ueak_admission_evidence_fixture,
)
from hg_runtime.translation_envelope_protocol.integration import (
    gpp_fixture_evaluate_permit_request,
    ueak_fixture_evaluate_admission_request,
)
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    NOT_TRANSLATABLE,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    list_fenced_paths,
    refuse_naked_cross_membrane,
    run_tep_d_organ_emission_path,
    wrap_organ_receipt,
)

_ORGAN_RUNNERS = {
    "ORI": run_ori_fixture_emission,
    "OPB": run_opb_fixture_emission,
    "IPB": run_ipb_fixture_emission,
    "ARB": run_arb_fixture_emission,
    "IMB": run_imb_fixture_emission,
    "ERB": run_erb_fixture_emission,
    "EGI": run_egi_fixture_emission,
    "RIB": run_rib_fixture_emission,
    "A0-HM": run_a0_hm_fixture_emission,
    "H8": run_h8_fixture_emission,
}


@pytest.mark.parametrize("organ,runner", list(_ORGAN_RUNNERS.items()))
def test_per_organ_fixture_emission_wrapped(organ: str, runner: object) -> None:
    result = runner()  # type: ignore[operator]
    assert result["has_translation_envelope"] is True
    assert result["authority_created"] is False
    envelope = result["fixture_result"]["translation_envelope"]
    assert envelope["authority_created"] is False
    assert envelope.get("producer_module") == organ or organ in str(envelope.get("producer_module", ""))


def test_naked_scalar_refused_cross_membrane() -> None:
    claim = naked_scalar_fixture()
    result = refuse_naked_cross_membrane(claim, None)
    assert result["status"] == "refused"
    assert result["authority_created"] is False


def test_fence_legacy_naked_path_registers_future_work() -> None:
    entry = fence_legacy_naked_path(
        "test:live:rtc:fixture",
        organ="TEST",
        reason="test fence",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )
    assert entry["status"] == "fenced"
    assert entry["future_work_id"] == FW_QUEUE_TEP_D_LIVE
    assert entry["authority_created"] is False
    assert "test:live:rtc:fixture" in list_fenced_paths()


def test_wrap_organ_receipt_includes_envelope() -> None:
    wrapped = wrap_organ_receipt(
        {"receipt_id": "r1", "status": "recorded"},
        source_organ="IMB",
        claim_type="BOUNDARY_RECEIPT",
    )
    assert "translation_envelope" in wrapped
    assert wrapped["translation_envelope"]["authority_created"] is False


def test_not_translatable_helper() -> None:
    emitted = emit_tep_wrapped_claim(
        source_organ="DRB",
        claim_type="SIMULATION_RESULT",
        claim_id="claim:sim:not-translatable",
        structured_value={"not_history": True},
        translation_status=NOT_TRANSLATABLE,
        not_translatable_reason="simulation is not execution history",
    )
    assert emitted["translation_envelope"]["translation_status"] == NOT_TRANSLATABLE
    assert emitted["authority_created"] is False


def test_gpp_rejects_naked_evidence() -> None:
    result = gpp_fixture_evaluate_permit_request(gpp_permit_evidence_fixture(naked=True))
    assert result["status"] == "rejected"
    assert result["permit_minted"] is False
    assert result["authority_created"] is False


def test_gpp_accepts_wrapped_evidence_for_review() -> None:
    result = gpp_fixture_evaluate_permit_request(gpp_permit_evidence_fixture(naked=False))
    assert result["status"] == "evidence_accepted_for_review"
    assert result["permit_minted"] is False


def test_ueak_rejects_naked_support() -> None:
    result = ueak_fixture_evaluate_admission_request(ueak_admission_evidence_fixture(naked=True))
    assert result["status"] == "rejected"
    assert result["admitted"] is False


def test_ueak_does_not_admit_wrapped_support() -> None:
    result = ueak_fixture_evaluate_admission_request(ueak_admission_evidence_fixture(naked=False))
    assert result["admitted"] is False
    assert result["authority_created"] is False


def test_full_tep_d_organ_emission_path() -> None:
    path = run_tep_d_organ_emission_path()
    assert path["all_organs_wrapped"] is True
    assert path["naked_refused"] is True
    assert path["gpp_naked_rejected"] is True
    assert path["ueak_naked_rejected"] is True
    assert path["live_paths_fenced"] is True
    assert path["no_oea_ter_called"] is True


def test_live_paths_fenced_not_authority() -> None:
    fences = list_fenced_paths()
    assert len(fences) >= 12
    for entry in fences.values():
        assert entry["authority_created"] is False
        assert entry["future_work_id"] == FW_QUEUE_TEP_D_LIVE
