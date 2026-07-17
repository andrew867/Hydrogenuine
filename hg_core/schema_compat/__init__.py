"""Schema / migration / compatibility (CT-09 SCH)."""

from hg_core.schema_compat.registry import SchemaEntry, SchemaRegistry, load_registry
from hg_core.schema_compat.validator import (
    ValidationFinding,
    findings_ok,
    validate_artifact_record,
    validate_registry_artifacts,
)
from hg_core.schema_compat.proof_bundle import validate_ct_proof_bundle_dir
from hg_core.schema_compat.replay_golden import run_golden_replay_matrix
from hg_core.schema_compat.compat import check_event_types_registered

__all__ = [
    "SchemaEntry",
    "SchemaRegistry",
    "ValidationFinding",
    "check_event_types_registered",
    "findings_ok",
    "load_registry",
    "run_golden_replay_matrix",
    "validate_artifact_record",
    "validate_ct_proof_bundle_dir",
    "validate_registry_artifacts",
]
