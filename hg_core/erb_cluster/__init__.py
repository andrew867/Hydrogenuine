"""ERB cluster helpers — external relation is not authority."""

from hg_core.erb_cluster.config import (
    erb_enabled,
    erb_refuse_authority_conversion,
    erb_refuse_stale_policy,
    erb_static_fixtures_only,
)
from hg_core.erb_cluster.errors import ERB_ENTITY_RECORDED, ErbValidationError
from hg_core.erb_cluster.no_authority import advisory_only_marker, check_erb_import_fences

__all__ = [
    "ERB_ENTITY_RECORDED",
    "ErbValidationError",
    "advisory_only_marker",
    "check_erb_import_fences",
    "erb_enabled",
    "erb_refuse_authority_conversion",
    "erb_refuse_stale_policy",
    "erb_static_fixtures_only",
]
