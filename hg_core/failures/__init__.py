"""CT-05 unified failure taxonomy and incident model."""

from hg_core.failures.incident import Incident, IncidentLedger
from hg_core.failures.plt_display import format_failure_summary, state_color
from hg_core.failures.precedence import resolve_aggregate_from_reason_codes, resolve_aggregate_state
from hg_core.failures.registry import (
    ReasonCodeRegistry,
    clear_registry_cache,
    display_label_for,
    legacy_migration_map,
    load_registry,
    normalize_reason_code,
    terminal_outcome_from_reason,
    terminal_state_for,
    validate_reason_code,
    validate_terminal_event,
)
from hg_core.failures.types import ReasonCodeRecord, TerminalOutcome, ValidationResult

__all__ = [
    "Incident",
    "IncidentLedger",
    "ReasonCodeRecord",
    "ReasonCodeRegistry",
    "TerminalOutcome",
    "ValidationResult",
    "clear_registry_cache",
    "display_label_for",
    "format_failure_summary",
    "legacy_migration_map",
    "load_registry",
    "normalize_reason_code",
    "resolve_aggregate_from_reason_codes",
    "resolve_aggregate_state",
    "state_color",
    "terminal_outcome_from_reason",
    "terminal_state_for",
    "validate_reason_code",
    "validate_terminal_event",
]
