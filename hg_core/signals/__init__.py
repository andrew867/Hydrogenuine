"""Pack 15: Latent signal schema and storage. Versioned signals_json; signal groups A–F."""

from hg_core.signals.schema import (
    SIGNALS_JSON_SCHEMA_VERSION,
    build_signals_json,
    signal_groups_doc,
)

__all__ = [
    "SIGNALS_JSON_SCHEMA_VERSION",
    "build_signals_json",
    "signal_groups_doc",
]
