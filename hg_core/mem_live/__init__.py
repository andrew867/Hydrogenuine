"""MEM-LIVE cluster — governed live memory mutation proof gates."""

from hg_core.mem_live.config import (
    mem_fake_sink_only,
    mem_refuse_authority_conversion,
    mem_refuse_durable_writes,
)
from hg_core.mem_live.errors import MemValidationError
from hg_core.mem_live.no_authority import advisory_only_marker, check_mem_import_fences

__all__ = [
    "MemValidationError",
    "advisory_only_marker",
    "check_mem_import_fences",
    "mem_fake_sink_only",
    "mem_refuse_authority_conversion",
    "mem_refuse_durable_writes",
]
