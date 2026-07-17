"""Runtime context shared helpers — bootstrap, presentation, research boundaries."""

from hg_core.runtime_context.config import (
    bcp_enabled,
    bcp_refuse_stale_packet,
    dep_bond_enabled,
    dep_bond_refuse_stale_observation,
    pres_enabled,
    pres_require_authority_badge,
    pro_backburner_guard,
    pro_enabled,
    pro_hardware_allowed,
    pro_refuse_stale_body_state,
    pro_static_fixtures_only,
    pub_enabled,
    pub_require_evidence_for_public,
    res_enabled,
    res_offline_only,
    sim_enabled,
    sim_offline_only,
    sim_refuse_stale_scenario,
)
from hg_core.runtime_context.errors import RuntimeContextValidationError
from hg_core.runtime_context.no_authority import advisory_only_marker, check_runtime_import_fences

__all__ = [
    "RuntimeContextValidationError",
    "advisory_only_marker",
    "bcp_enabled",
    "bcp_refuse_stale_packet",
    "check_runtime_import_fences",
    "dep_bond_enabled",
    "dep_bond_refuse_stale_observation",
    "pres_enabled",
    "pres_require_authority_badge",
    "pro_backburner_guard",
    "pro_enabled",
    "pro_hardware_allowed",
    "pro_refuse_stale_body_state",
    "pro_static_fixtures_only",
    "pub_enabled",
    "pub_require_evidence_for_public",
    "res_enabled",
    "res_offline_only",
    "sim_enabled",
    "sim_offline_only",
    "sim_refuse_stale_scenario",
]
