"""OIR refusal reason codes."""

REFUSED_AUTHORITY_CONVERSION = "oir.refused.authority_conversion"
REFUSED_UNKNOWN_REGIME = "oir.refused.unknown_regime"
REFUSED_DESTRUCTIVE_REPULSIVE = "oir.refused.destructive_repulsive"
REFUSED_GATE_BYPASS = "oir.refused.gate_bypass"
REFUSED_DURABLE_SINK = "oir.refused.durable_sink"
REFUSED_SECRET_LEAK = "oir.refused.secret_leak"

OIR_INTERACTION_RECORDED = "oir.advisory.interaction_recorded"

__all__ = [
    "OIR_INTERACTION_RECORDED",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_DESTRUCTIVE_REPULSIVE",
    "REFUSED_DURABLE_SINK",
    "REFUSED_GATE_BYPASS",
    "REFUSED_SECRET_LEAK",
    "REFUSED_UNKNOWN_REGIME",
]
