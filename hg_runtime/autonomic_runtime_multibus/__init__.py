"""Autonomic Runtime Multi-Bus integration — modules 6-14 safe/static."""

from hg_runtime.autonomic_runtime_multibus.integration import (
    analyze_all_arm_bus_modules,
    compose_bus_fixture_surfaces,
    validate_arm_bus_receipt_alignment,
    validate_delegation_no_spawn,
    validate_edge_filter_blocks_naked_messages,
    validate_no_bus_to_authority,
    validate_scheduler_no_live_backends,
)
from hg_runtime.autonomic_runtime_multibus.types import FIXTURE_CLOCK, REQUIRED_ARM_BUS_MODULES

__all__ = [
    "FIXTURE_CLOCK",
    "REQUIRED_ARM_BUS_MODULES",
    "analyze_all_arm_bus_modules",
    "compose_bus_fixture_surfaces",
    "validate_arm_bus_receipt_alignment",
    "validate_delegation_no_spawn",
    "validate_edge_filter_blocks_naked_messages",
    "validate_no_bus_to_authority",
    "validate_scheduler_no_live_backends",
]
