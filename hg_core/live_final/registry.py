"""LIVE-FINAL registry — canonical live scope gate inventory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class LiveScopeGateEntry:
    tranche_id: str
    gate_script: str
    audit_doc: str
    feature_check_import: str
    feature_check_fn: str
    test_dir: str | None
    required_for_final: bool = True


LIVE_SCOPE_PRIOR_GATES: tuple[LiveScopeGateEntry, ...] = (
    LiveScopeGateEntry(
        tranche_id="OUX-LIVE",
        gate_script="scripts/evals/live_operator_ux_gate.py",
        audit_doc="docs/reports/phases/OUX_LIVE_AUDIT.md",
        feature_check_import="hg_core.oux_live.gate_runner",
        feature_check_fn="run_oux_feature_checks",
        test_dir="tests/oux_live",
    ),
    LiveScopeGateEntry(
        tranche_id="INFER-LIVE",
        gate_script="scripts/evals/live_inference_runtime_gate.py",
        audit_doc="docs/reports/phases/INFER_LIVE_AUDIT.md",
        feature_check_import="hg_core.infer_live.gate_runner",
        feature_check_fn="run_infer_feature_checks",
        test_dir="tests/infer_live",
    ),
    LiveScopeGateEntry(
        tranche_id="MEM-LIVE",
        gate_script="scripts/evals/live_memory_mutation_gate.py",
        audit_doc="docs/reports/phases/MEM_LIVE_AUDIT.md",
        feature_check_import="hg_core.mem_live.gate_runner",
        feature_check_fn="run_mem_feature_checks",
        test_dir="tests/mem_live",
    ),
    LiveScopeGateEntry(
        tranche_id="GMG-LIVE",
        gate_script="scripts/evals/grant_authority_gate.py",
        audit_doc="docs/reports/phases/GMG_LIVE_AUDIT.md",
        feature_check_import="hg_core.gmg_live.gate_runner",
        feature_check_fn="run_gmg_feature_checks",
        test_dir="tests/gmg_live",
    ),
    LiveScopeGateEntry(
        tranche_id="OEA-TER-LIVE",
        gate_script="scripts/evals/live_oea_ter_bridge_gate.py",
        audit_doc="docs/reports/phases/OEA_TER_LIVE_AUDIT.md",
        feature_check_import="hg_core.oea_ter_live.gate_runner",
        feature_check_fn="run_oea_ter_feature_checks",
        test_dir="tests/oea_ter_live",
    ),
    LiveScopeGateEntry(
        tranche_id="SRP-LIVE",
        gate_script="scripts/evals/live_srp_apply_gate.py",
        audit_doc="docs/reports/phases/SRP_LIVE_AUDIT.md",
        feature_check_import="hg_core.srp_live.gate_runner",
        feature_check_fn="run_srp_feature_checks",
        test_dir="tests/srp_live",
    ),
    LiveScopeGateEntry(
        tranche_id="SEN-LIVE",
        gate_script="scripts/evals/live_sensor_ingestion_gate.py",
        audit_doc="docs/reports/phases/SEN_LIVE_AUDIT.md",
        feature_check_import="hg_core.sen_live.gate_runner",
        feature_check_fn="run_sen_feature_checks",
        test_dir="tests/sen_live",
    ),
    LiveScopeGateEntry(
        tranche_id="PUB-EXT-LIVE",
        gate_script="scripts/evals/live_publication_external_action_gate.py",
        audit_doc="docs/reports/phases/PUB_EXT_LIVE_AUDIT.md",
        feature_check_import="hg_core.pub_ext_live.gate_runner",
        feature_check_fn="run_pub_ext_feature_checks",
        test_dir="tests/pub_ext_live",
    ),
    LiveScopeGateEntry(
        tranche_id="REB-RESTORE-LIVE",
        gate_script="scripts/evals/live_reentry_restore_gate.py",
        audit_doc="docs/reports/phases/REB_RESTORE_LIVE_AUDIT.md",
        feature_check_import="hg_core.reb_restore_live.gate_runner",
        feature_check_fn="run_reb_restore_feature_checks",
        test_dir="tests/reb_restore_live",
    ),
    LiveScopeGateEntry(
        tranche_id="RIB-SPAWN-LIVE",
        gate_script="scripts/evals/live_reproduction_spawn_gate.py",
        audit_doc="docs/reports/phases/RIB_SPAWN_LIVE_AUDIT.md",
        feature_check_import="hg_core.rib_spawn_live.gate_runner",
        feature_check_fn="run_rib_spawn_feature_checks",
        test_dir="tests/rib_spawn_live",
    ),
    LiveScopeGateEntry(
        tranche_id="ALOOP-LIVE",
        gate_script="scripts/evals/long_running_autonomous_loop_gate.py",
        audit_doc="docs/reports/phases/ALOOP_LIVE_AUDIT.md",
        feature_check_import="hg_core.aloop_live.gate_runner",
        feature_check_fn="run_aloop_feature_checks",
        test_dir="tests/aloop_live",
    ),
)


def load_feature_check(entry: LiveScopeGateEntry) -> Callable[[], dict[str, object]]:
    import importlib

    module = importlib.import_module(entry.feature_check_import)
    fn = getattr(module, entry.feature_check_fn)
    return fn


__all__ = ["LIVE_SCOPE_PRIOR_GATES", "LiveScopeGateEntry", "load_feature_check"]
