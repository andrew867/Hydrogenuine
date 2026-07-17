"""One-button truth gate core (CT-04 OBT)."""

from hg_core.truth.classify import classify_subsystems_truth
from hg_core.truth.registry import GateEntry, TruthGateRegistry, default_registry_path, load_registry
from hg_core.truth.report import TruthGateReport, build_report, seal_bundle_hash

__all__ = [
    "GateEntry",
    "TruthGateRegistry",
    "TruthGateReport",
    "build_report",
    "classify_subsystems_truth",
    "default_registry_path",
    "load_registry",
    "seal_bundle_hash",
]
