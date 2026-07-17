"""ARM-INT autonomic multibus integration tests — modules 6-14, no live behavior."""

from __future__ import annotations

from hg_runtime.autonomic_runtime_multibus import (
    FIXTURE_CLOCK,
    REQUIRED_ARM_BUS_MODULES,
    analyze_all_arm_bus_modules,
    compose_bus_fixture_surfaces,
    validate_arm_bus_receipt_alignment,
    validate_delegation_no_spawn,
    validate_edge_filter_blocks_naked_messages,
    validate_no_bus_to_authority,
    validate_scheduler_no_live_backends,
)


def test_required_arm_bus_modules_count() -> None:
    assert REQUIRED_ARM_BUS_MODULES == (
        "BRS",
        "HRT",
        "RSP",
        "CIR",
        "DBB",
        "ESB",
        "ISB",
        "RDB",
        "ALC",
    )


def test_compose_bus_fixture_surfaces() -> None:
    result = compose_bus_fixture_surfaces(observed_at=FIXTURE_CLOCK)
    surfaces = result["bus_surfaces"]  # type: ignore[index]
    assert result["permission_granted"] is False
    assert result["authority_created"] is False
    assert isinstance(surfaces, dict)
    assert len(surfaces) == len(REQUIRED_ARM_BUS_MODULES)


def test_all_bus_surfaces_recorded() -> None:
    result = compose_bus_fixture_surfaces(observed_at=FIXTURE_CLOCK)
    surfaces = result["bus_surfaces"]  # type: ignore[index]
    assert isinstance(surfaces, dict)
    for module in REQUIRED_ARM_BUS_MODULES:
        surface = surfaces[module]
        assert isinstance(surface, dict)
        assert surface.get("status") == "recorded"
        assert surface.get("permission_granted") is False
        assert surface.get("authority_created") is False


def test_analyze_all_arm_bus_modules() -> None:
    analysis = analyze_all_arm_bus_modules(observed_at=FIXTURE_CLOCK)
    assert analysis["all_modules_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["permission_granted"] is False
    module_analyses = analysis["module_analyses"]  # type: ignore[index]
    assert isinstance(module_analyses, dict)
    for module in REQUIRED_ARM_BUS_MODULES:
        mod_analysis = module_analyses[module]
        assert int(mod_analysis["bundle_count"]) >= 14  # type: ignore[index]


def test_no_bus_to_authority() -> None:
    result = validate_no_bus_to_authority(observed_at=FIXTURE_CLOCK)
    assert result["no_bus_to_authority"] is True
    assert result["permission_granted"] is False
    assert result["authority_created"] is False


def test_edge_filter_blocks_naked_messages() -> None:
    result = validate_edge_filter_blocks_naked_messages()
    assert result["naked_blocked"] is True
    assert result["wrapped_passes"] is True
    assert result["permission_granted"] is False


def test_scheduler_no_live_backends() -> None:
    result = validate_scheduler_no_live_backends()
    assert result["fixture_backend_ok"] is True
    assert result["live_backend_rejected"] is True
    assert result["permission_granted"] is False


def test_delegation_no_spawn() -> None:
    result = validate_delegation_no_spawn(observed_at=FIXTURE_CLOCK)
    assert result["delegation_no_spawn"] is True
    assert result["agent_spawned"] is False
    assert result["permission_granted"] is False


def test_arm_bus_receipt_alignment() -> None:
    alignment = validate_arm_bus_receipt_alignment(observed_at=FIXTURE_CLOCK)
    assert alignment["required_modules_present"] is True
    assert alignment["all_aligned"] is True
    assert alignment["permission_granted"] is False


def test_rdb_spawn_proposal_advisory_only() -> None:
    from hg_runtime.reproduction_delegation_bus import load_rdb_fixtures, process_rdb_bundle

    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-spawn-proposal")
    result = process_rdb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
    assert result.get("agent_spawned") is False


def test_brs_surface_non_authority() -> None:
    surfaces = compose_bus_fixture_surfaces()["bus_surfaces"]  # type: ignore[index]
    brs = surfaces["BRS"]  # type: ignore[index]
    assert brs.get("advisory_only") is True or brs.get("rate_is_advisory_only") is True


def test_alc_surface_no_spawn() -> None:
    surfaces = compose_bus_fixture_surfaces()["bus_surfaces"]  # type: ignore[index]
    alc = surfaces["ALC"]  # type: ignore[index]
    assert alc.get("agent_spawned") is False
    assert alc.get("permission_granted") is False
