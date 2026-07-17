"""
Sticky Reality Ch2: Observation pipeline — ingest, provenance, materialized indexes.
"""

from .registry import SignalDefinition, SignalRegistry, load_registry
from .artifacts import write_observation_artifact, write_rationale_artifact
from .ingest import ingest_observation
from .anomaly import detect_anomalies, integrity_rule, expected_range_rule
from .binding import emit_observation_bound
from .api import list_observations, get_observation

__all__ = [
    "SignalDefinition",
    "SignalRegistry",
    "load_registry",
    "write_observation_artifact",
    "write_rationale_artifact",
    "ingest_observation",
    "detect_anomalies",
    "integrity_rule",
    "expected_range_rule",
    "emit_observation_bound",
    "list_observations",
    "get_observation",
]
