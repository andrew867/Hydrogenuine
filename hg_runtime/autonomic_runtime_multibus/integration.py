"""ARM-INT — compose autonomic bus modules 6-14 without live behavior."""

from __future__ import annotations

from typing import Any, Callable

from hg_runtime.autonomic_runtime_multibus.edge_filter import (
    filter_naked_message,
    make_fixture_envelope,
)
from hg_runtime.autonomic_runtime_multibus.scheduler_policy import validate_scheduler_fixture
from hg_runtime.autonomic_runtime_multibus.types import FIXTURE_CLOCK, REQUIRED_ARM_BUS_MODULES

OrganProcessor = Callable[..., dict[str, object]]
OrganLoader = Callable[[], tuple[dict[str, Any], ...]]


def _organ_registry() -> dict[str, dict[str, object]]:
    from hg_runtime.agent_lifecycle_controller import (
        analyze_alc_fixtures,
        load_alc_fixtures,
        process_alc_bundle,
    )
    from hg_runtime.bus_rate_supervisor import (
        analyze_brs_fixtures,
        load_brs_fixtures,
        process_brs_bundle,
    )
    from hg_runtime.circulatory_resource_bus import (
        analyze_cir_fixtures,
        load_cir_fixtures,
        process_cir_bundle,
    )
    from hg_runtime.data_blob_bus import (
        analyze_dbb_fixtures,
        load_dbb_fixtures,
        process_dbb_bundle,
    )
    from hg_runtime.external_sensory_bus import (
        analyze_esb_fixtures,
        load_esb_fixtures,
        process_esb_bundle,
    )
    from hg_runtime.heartbeat_liveness_transport import (
        analyze_hrt_fixtures,
        load_hrt_fixtures,
        process_hrt_bundle,
    )
    from hg_runtime.intuition_salience_bus import (
        analyze_isb_fixtures,
        load_isb_fixtures,
        process_isb_bundle,
    )
    from hg_runtime.reproduction_delegation_bus import (
        analyze_rdb_fixtures,
        load_rdb_fixtures,
        process_rdb_bundle,
    )
    from hg_runtime.respiratory_token_compute_bus import (
        analyze_rsp_fixtures,
        load_rsp_fixtures,
        process_rsp_bundle,
    )

    return {
        "BRS": {
            "load": load_brs_fixtures,
            "analyze": analyze_brs_fixtures,
            "process": process_brs_bundle,
            "receipt_key": "brs_receipt",
        },
        "HRT": {
            "load": load_hrt_fixtures,
            "analyze": analyze_hrt_fixtures,
            "process": process_hrt_bundle,
            "receipt_key": "hrt_receipt",
        },
        "RSP": {
            "load": load_rsp_fixtures,
            "analyze": analyze_rsp_fixtures,
            "process": process_rsp_bundle,
            "receipt_key": "rsp_receipt",
        },
        "CIR": {
            "load": load_cir_fixtures,
            "analyze": analyze_cir_fixtures,
            "process": process_cir_bundle,
            "receipt_key": "cir_receipt",
        },
        "DBB": {
            "load": load_dbb_fixtures,
            "analyze": analyze_dbb_fixtures,
            "process": process_dbb_bundle,
            "receipt_key": "dbb_receipt",
        },
        "ESB": {
            "load": load_esb_fixtures,
            "analyze": analyze_esb_fixtures,
            "process": process_esb_bundle,
            "receipt_key": "esb_receipt",
        },
        "ISB": {
            "load": load_isb_fixtures,
            "analyze": analyze_isb_fixtures,
            "process": process_isb_bundle,
            "receipt_key": "isb_receipt",
        },
        "RDB": {
            "load": load_rdb_fixtures,
            "analyze": analyze_rdb_fixtures,
            "process": process_rdb_bundle,
            "receipt_key": "rdb_receipt",
        },
        "ALC": {
            "load": load_alc_fixtures,
            "analyze": analyze_alc_fixtures,
            "process": process_alc_bundle,
            "receipt_key": "alc_receipt",
        },
    }


def compose_bus_fixture_surfaces(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Process first positive fixture per bus module — static composition only."""
    registry = _organ_registry()
    surfaces: dict[str, object] = {}
    for module in REQUIRED_ARM_BUS_MODULES:
        entry = registry[module]
        load_fn = entry["load"]  # type: ignore[operator]
        process_fn = entry["process"]  # type: ignore[operator]
        bundles = load_fn()
        positive = next(
            (b for b in bundles if not b.get("adversarial_signal")),
            bundles[0],
        )
        result = process_fn(positive, observed_at=observed_at)  # type: ignore[operator]
        surfaces[module] = result
    return {
        "fixture_composition_only": True,
        "bus_surfaces": surfaces,
        "module_count": len(surfaces),
        "permission_granted": False,
        "authority_created": False,
    }


def analyze_all_arm_bus_modules(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    registry = _organ_registry()
    module_analyses: dict[str, object] = {}
    for module in REQUIRED_ARM_BUS_MODULES:
        entry = registry[module]
        analyze_fn = entry["analyze"]  # type: ignore[operator]
        module_analyses[module] = analyze_fn(observed_at=observed_at)  # type: ignore[operator]
    all_advisory = all(
        bool(a.get("all_advisory")) and bool(a.get("no_authority_created"))
        for a in module_analyses.values()
        if isinstance(a, dict)
    )
    return {
        "integration_analysis_only": True,
        "module_analyses": module_analyses,
        "all_modules_advisory": all_advisory,
        "no_authority_created": all_advisory,
        "permission_granted": False,
        "authority_created": False,
    }


def validate_no_bus_to_authority(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Prove no bus module output grants authority."""
    analysis = analyze_all_arm_bus_modules(observed_at=observed_at)
    module_analyses = analysis.get("module_analyses", {})
    violations: list[str] = []
    if isinstance(module_analyses, dict):
        for module, mod_analysis in module_analyses.items():
            if not isinstance(mod_analysis, dict):
                violations.append(f"{module}:invalid_analysis")
                continue
            if mod_analysis.get("all_advisory") is not True:
                violations.append(f"{module}:not_advisory")
            if mod_analysis.get("no_authority_created") is not True:
                violations.append(f"{module}:authority_created")
            if mod_analysis.get("permission_granted") is True:
                violations.append(f"{module}:permission_granted")
    return {
        "no_bus_to_authority": not violations,
        "violations": violations,
        "permission_granted": False,
        "authority_created": False,
    }


def validate_edge_filter_blocks_naked_messages() -> dict[str, object]:
    naked = {"payload": "unwrapped bus traffic", "notes": "no tep envelope"}
    wrapped = {
        "payload": "tep-wrapped traffic",
        "tep_envelope": make_fixture_envelope(
            source="arm:fixture:brs",
            target="arm:fixture:hrt",
            replay_identity="arm-fixture-001",
        ),
    }
    naked_result = filter_naked_message(naked)
    wrapped_result = filter_naked_message(wrapped)
    return {
        "naked_blocked": naked_result.get("naked_message_blocked") is True
        and naked_result.get("status") == "blocked",
        "wrapped_passes": wrapped_result.get("naked_message_blocked") is False
        and wrapped_result.get("status") == "filtered",
        "permission_granted": False,
        "authority_created": False,
    }


def validate_scheduler_no_live_backends() -> dict[str, object]:
    fixture_profile = {"backend": "fixture_static", "live_invocation": False}
    live_profile = {"backend": "vllm://localhost:8000", "live_invocation": True}
    fixture_result = validate_scheduler_fixture(fixture_profile)
    live_result = validate_scheduler_fixture(live_profile)
    return {
        "fixture_backend_ok": fixture_result.get("status") == "validated",
        "live_backend_rejected": live_result.get("status") == "rejected",
        "permission_granted": False,
        "authority_created": False,
    }


def validate_delegation_no_spawn(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Prove RDB delegation bus never spawns agents."""
    from hg_runtime.reproduction_delegation_bus import load_rdb_fixtures, process_rdb_bundle

    bundles = load_rdb_fixtures()
    spawn_violations: list[str] = []
    for bundle in bundles:
        result = process_rdb_bundle(bundle, observed_at=observed_at)
        if result.get("agent_spawned") is True:
            spawn_violations.append(str(bundle.get("bundle_id")))
        receipt = result.get("rdb_receipt")
        if isinstance(receipt, dict) and receipt.get("agent_spawned") is True:
            spawn_violations.append(f"receipt:{bundle.get('bundle_id')}")
    return {
        "delegation_no_spawn": not spawn_violations,
        "spawn_violations": spawn_violations,
        "permission_granted": False,
        "authority_created": False,
        "agent_spawned": False,
    }


def validate_arm_bus_receipt_alignment(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    registry = _organ_registry()
    aligned: list[str] = []
    misaligned: list[str] = []
    for module in REQUIRED_ARM_BUS_MODULES:
        entry = registry[module]
        load_fn = entry["load"]  # type: ignore[operator]
        process_fn = entry["process"]  # type: ignore[operator]
        receipt_key = str(entry["receipt_key"])
        bundles = load_fn()
        positive = next((b for b in bundles if not b.get("adversarial_signal")), bundles[0])
        result = process_fn(positive, observed_at=observed_at)  # type: ignore[operator]
        receipt = result.get(receipt_key)
        if (
            result.get("status") == "recorded"
            and isinstance(receipt, dict)
            and receipt.get("permission_granted") is False
            and receipt.get("authority_created") is False
        ):
            aligned.append(module)
        else:
            misaligned.append(module)
    return {
        "required_modules_present": len(aligned) == len(REQUIRED_ARM_BUS_MODULES),
        "all_aligned": not misaligned,
        "aligned_recorded_modules": aligned,
        "misaligned_modules": misaligned,
        "permission_granted": False,
        "authority_granted": False,
    }


__all__ = [
    "analyze_all_arm_bus_modules",
    "compose_bus_fixture_surfaces",
    "validate_arm_bus_receipt_alignment",
    "validate_delegation_no_spawn",
    "validate_edge_filter_blocks_naked_messages",
    "validate_no_bus_to_authority",
    "validate_scheduler_no_live_backends",
]
