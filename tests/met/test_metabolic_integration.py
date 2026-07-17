"""MET-INT metabolic integration tests — compose organ fixtures, no live behavior."""

from __future__ import annotations

from hg_runtime.metabolic_governance.integration import (
    analyze_all_metabolic_organs,
    compose_organ_fixture_surfaces,
    validate_met_organ_receipt_alignment,
)
from hg_runtime.metabolic_governance.types import FIXTURE_CLOCK, REQUIRED_METABOLIC_ORGANS


def test_required_metabolic_organs_count() -> None:
    assert REQUIRED_METABOLIC_ORGANS == ("BRB", "NIB", "DAB", "WDB", "TLB", "DCD", "GXB")


def test_compose_organ_fixture_surfaces() -> None:
    result = compose_organ_fixture_surfaces(observed_at=FIXTURE_CLOCK)
    surfaces = result["organ_surfaces"]  # type: ignore[index]
    assert result["permission_granted"] is False
    assert result["authority_created"] is False
    assert isinstance(surfaces, dict)
    assert len(surfaces) == len(REQUIRED_METABOLIC_ORGANS)


def test_all_organ_surfaces_recorded() -> None:
    result = compose_organ_fixture_surfaces(observed_at=FIXTURE_CLOCK)
    surfaces = result["organ_surfaces"]  # type: ignore[index]
    assert isinstance(surfaces, dict)
    for organ in REQUIRED_METABOLIC_ORGANS:
        surface = surfaces[organ]
        assert isinstance(surface, dict)
        assert surface.get("status") == "recorded"
        assert surface.get("permission_granted") is False
        assert surface.get("authority_created") is False


def test_analyze_all_metabolic_organs() -> None:
    analysis = analyze_all_metabolic_organs(observed_at=FIXTURE_CLOCK)
    assert analysis["all_organs_advisory"] is True
    assert analysis["met_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["permission_granted"] is False
    organ_analyses = analysis["organ_analyses"]  # type: ignore[index]
    assert isinstance(organ_analyses, dict)
    for organ in REQUIRED_METABOLIC_ORGANS:
        organ_analysis = organ_analyses[organ]
        assert int(organ_analysis["bundle_count"]) >= 12  # type: ignore[index]


def test_met_organ_receipt_alignment() -> None:
    alignment = validate_met_organ_receipt_alignment(observed_at=FIXTURE_CLOCK)
    assert alignment["required_organs_present"] is True
    assert alignment["all_aligned"] is True
    assert alignment["met_permission_granted"] is False
    assert alignment["permission_granted"] is False


def test_brb_surface_non_authority() -> None:
    surfaces = compose_organ_fixture_surfaces()["organ_surfaces"]  # type: ignore[index]
    brb = surfaces["BRB"]  # type: ignore[index]
    assert brb.get("breathing_is_advisory_only") is True or brb.get("advisory_only") is True


def test_nib_surface_non_authority() -> None:
    surfaces = compose_organ_fixture_surfaces()["organ_surfaces"]  # type: ignore[index]
    nib = surfaces["NIB"]  # type: ignore[index]
    assert nib.get("permission_granted") is False


def test_dab_surface_proposal_only() -> None:
    surfaces = compose_organ_fixture_surfaces()["organ_surfaces"]  # type: ignore[index]
    dab = surfaces["DAB"]  # type: ignore[index]
    record = dab.get("dab_record")  # type: ignore[union-attr]
    assert isinstance(record, dict)
    assert record.get("proposal_only") is True


def test_wdb_surface_no_deletion() -> None:
    surfaces = compose_organ_fixture_surfaces()["organ_surfaces"]  # type: ignore[index]
    wdb = surfaces["WDB"]  # type: ignore[index]
    assert wdb.get("deletion_performed") is False


def test_tlb_surface_no_tool_removal() -> None:
    surfaces = compose_organ_fixture_surfaces()["organ_surfaces"]  # type: ignore[index]
    tlb = surfaces["TLB"]  # type: ignore[index]
    assert tlb.get("tool_removed") is False


def test_dcd_surface_no_resurrection() -> None:
    surfaces = compose_organ_fixture_surfaces()["organ_surfaces"]  # type: ignore[index]
    dcd = surfaces["DCD"]  # type: ignore[index]
    assert dcd.get("agent_spawned") is False


def test_gxb_surface_no_grant() -> None:
    surfaces = compose_organ_fixture_surfaces()["organ_surfaces"]  # type: ignore[index]
    gxb = surfaces["GXB"]  # type: ignore[index]
    assert gxb.get("permission_granted") is False


def test_integration_no_oea_ter() -> None:
    analysis = analyze_all_metabolic_organs()
    organ_analyses = analysis["organ_analyses"]  # type: ignore[index]
    for organ in REQUIRED_METABOLIC_ORGANS:
        bundle_results = organ_analyses[organ]["bundle_results"]  # type: ignore[index]
        for result in bundle_results:  # type: ignore[union-attr]
            if isinstance(result, dict):
                assert result.get("oea_ter_called") is False


def test_integration_no_live_behavior_flags() -> None:
    surfaces = compose_organ_fixture_surfaces()["organ_surfaces"]  # type: ignore[index]
    for organ in REQUIRED_METABOLIC_ORGANS:
        surface = surfaces[organ]  # type: ignore[index]
        assert surface.get("external_action_taken") is False
        assert surface.get("execution_admitted") is False


def test_met_analysis_includes_all_organs() -> None:
    analysis = analyze_all_metabolic_organs()
    met_analysis = analysis["met_analysis"]  # type: ignore[index]
    assert int(met_analysis["bundle_count"]) >= 12  # type: ignore[index]
    assert met_analysis["all_advisory"] is True  # type: ignore[index]


def test_alignment_missing_organs_empty() -> None:
    alignment = validate_met_organ_receipt_alignment()
    missing = alignment["missing_organs"]  # type: ignore[index]
    assert missing == []


def test_compose_is_fixture_only() -> None:
    result = compose_organ_fixture_surfaces()
    assert result["fixture_composition_only"] is True


def test_analyze_is_integration_only() -> None:
    result = analyze_all_metabolic_organs()
    assert result["integration_analysis_only"] is True
