"""SEN-LIVE cluster — governed live sensor ingestion proof gates."""

from hg_core.sen_live.config import (
    sen_fake_sink_only,
    sen_refuse_authority_conversion,
    sen_refuse_live_sensor_connection,
)
from hg_core.sen_live.errors import SenValidationError
from hg_core.sen_live.no_authority import advisory_only_marker, check_sen_import_fences

__all__ = [
    "SenValidationError",
    "advisory_only_marker",
    "check_sen_import_fences",
    "sen_fake_sink_only",
    "sen_refuse_authority_conversion",
    "sen_refuse_live_sensor_connection",
]
