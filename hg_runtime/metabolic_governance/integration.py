"""MET-INT — compose metabolic organ fixtures without live behavior."""

from __future__ import annotations

from typing import Any, Callable

from hg_runtime.metabolic_governance.fixtures import analyze_metabolic_fixtures, load_metabolic_fixtures
from hg_runtime.metabolic_governance.types import FIXTURE_CLOCK, REQUIRED_METABOLIC_ORGANS

OrganProcessor = Callable[..., dict[str, object]]
OrganLoader = Callable[[], tuple[dict[str, Any], ...]]


def _organ_registry() -> dict[str, dict[str, object]]:
    from hg_runtime.breathing_regulation_boundary import (
        analyze_brb_fixtures,
        load_brb_fixtures,
        process_brb_bundle,
    )
    from hg_runtime.decommissioning_cemetery_boundary import (
        analyze_dcd_fixtures,
        load_dcd_fixtures,
        process_dcd_bundle,
    )
    from hg_runtime.digestion_assimilation_boundary import (
        analyze_dab_fixtures,
        load_dab_fixtures,
        process_dab_bundle,
    )
    from hg_runtime.growth_expansion_boundary import (
        analyze_gxb_fixtures,
        load_gxb_fixtures,
        process_gxb_bundle,
    )
    from hg_runtime.nutrient_intake_boundary import (
        analyze_nib_fixtures,
        load_nib_fixtures,
        process_nib_bundle,
    )
    from hg_runtime.tool_lifecycle_boundary import (
        analyze_tlb_fixtures,
        load_tlb_fixtures,
        process_tlb_bundle,
    )
    from hg_runtime.waste_disposal_boundary import (
        analyze_wdb_fixtures,
        load_wdb_fixtures,
        process_wdb_bundle,
    )

    return {
        "BRB": {
            "load": load_brb_fixtures,
            "analyze": analyze_brb_fixtures,
            "process": process_brb_bundle,
            "receipt_key": "brb_receipt",
        },
        "NIB": {
            "load": load_nib_fixtures,
            "analyze": analyze_nib_fixtures,
            "process": process_nib_bundle,
            "receipt_key": "nib_receipt",
        },
        "DAB": {
            "load": load_dab_fixtures,
            "analyze": analyze_dab_fixtures,
            "process": process_dab_bundle,
            "receipt_key": "dab_receipt",
        },
        "WDB": {
            "load": load_wdb_fixtures,
            "analyze": analyze_wdb_fixtures,
            "process": process_wdb_bundle,
            "receipt_key": "wdb_receipt",
        },
        "TLB": {
            "load": load_tlb_fixtures,
            "analyze": analyze_tlb_fixtures,
            "process": process_tlb_bundle,
            "receipt_key": "tlb_receipt",
        },
        "DCD": {
            "load": load_dcd_fixtures,
            "analyze": analyze_dcd_fixtures,
            "process": process_dcd_bundle,
            "receipt_key": "dcd_receipt",
        },
        "GXB": {
            "load": load_gxb_fixtures,
            "analyze": analyze_gxb_fixtures,
            "process": process_gxb_bundle,
            "receipt_key": "gxb_receipt",
        },
    }


def compose_organ_fixture_surfaces(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Process first positive fixture per organ — static composition only."""
    registry = _organ_registry()
    surfaces: dict[str, object] = {}
    for organ in REQUIRED_METABOLIC_ORGANS:
        entry = registry[organ]
        load_fn = entry["load"]  # type: ignore[operator]
        process_fn = entry["process"]  # type: ignore[operator]
        bundles = load_fn()
        positive = next(
            (b for b in bundles if not b.get("adversarial_signal")),
            bundles[0],
        )
        result = process_fn(positive, observed_at=observed_at)  # type: ignore[operator]
        surfaces[organ] = result
    return {
        "fixture_composition_only": True,
        "organ_surfaces": surfaces,
        "organ_count": len(surfaces),
        "permission_granted": False,
        "authority_created": False,
    }


def analyze_all_metabolic_organs(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    registry = _organ_registry()
    organ_analyses: dict[str, object] = {}
    for organ in REQUIRED_METABOLIC_ORGANS:
        entry = registry[organ]
        analyze_fn = entry["analyze"]  # type: ignore[operator]
        organ_analyses[organ] = analyze_fn(observed_at=observed_at)  # type: ignore[operator]
    met_analysis = analyze_metabolic_fixtures(observed_at=observed_at)
    all_advisory = all(
        bool(a.get("all_advisory")) and bool(a.get("no_authority_created"))
        for a in organ_analyses.values()
        if isinstance(a, dict)
    )
    return {
        "integration_analysis_only": True,
        "organ_analyses": organ_analyses,
        "met_analysis": met_analysis,
        "all_organs_advisory": all_advisory,
        "met_advisory": met_analysis.get("all_advisory") is True,
        "no_authority_created": all_advisory
        and met_analysis.get("no_authority_created") is True,
        "permission_granted": False,
        "authority_created": False,
    }


def validate_met_organ_receipt_alignment(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.metabolic_governance.evaluator import process_metabolic_bundle

    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-valid-summary")
    met_result = process_metabolic_bundle(bundle, observed_at=observed_at)
    registry = _organ_registry()
    organ_refs = {
        str(row["organ"]): row
        for row in bundle.get("organ_receipts", ())
        if isinstance(row, dict)
    }
    missing = [o for o in REQUIRED_METABOLIC_ORGANS if o not in organ_refs]
    surfaces = compose_organ_fixture_surfaces(observed_at=observed_at)
    organ_surfaces = surfaces.get("organ_surfaces", {})
    aligned: list[str] = []
    if isinstance(organ_surfaces, dict):
        for organ in REQUIRED_METABOLIC_ORGANS:
            surface = organ_surfaces.get(organ)
            if isinstance(surface, dict) and surface.get("status") == "recorded":
                aligned.append(organ)
    return {
        "met_status": met_result.get("status"),
        "met_permission_granted": met_result.get("permission_granted"),
        "required_organs_present": not missing,
        "missing_organs": missing,
        "aligned_recorded_organs": aligned,
        "all_aligned": len(aligned) == len(REQUIRED_METABOLIC_ORGANS) and not missing,
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = [
    "analyze_all_metabolic_organs",
    "compose_organ_fixture_surfaces",
    "validate_met_organ_receipt_alignment",
]
