"""PLT failure display labels from registry (CT-05)."""

from __future__ import annotations

from hg_core.failures.registry import ReasonCodeRegistry, display_label_for, load_registry, validate_reason_code


def format_failure_summary(raw_reason: str, registry: ReasonCodeRegistry | None = None) -> dict[str, str]:
    reg = registry or load_registry()
    result = validate_reason_code(raw_reason, registry=reg)
    if not result.ok or result.record is None:
        return {
            "reason_code": str(raw_reason),
            "state": "unknown",
            "display_label": str(raw_reason),
            "retryable": "false",
        }
    return {
        "reason_code": result.record.code,
        "state": result.record.state,
        "display_label": result.record.display_label,
        "retryable": str(result.record.retryable).lower(),
    }


def state_color(state: str, registry: ReasonCodeRegistry | None = None) -> str:
    reg = registry or load_registry()
    if state not in reg.terminal_states:
        return "unknown"
    if state in {"panic", "lockdown", "unsafe", "chain_broken"}:
        return "critical"
    if state in {"denied", "refused", "failed", "timed_out", "replay_mismatch"}:
        return "warning"
    return "info"


__all__ = ["format_failure_summary", "state_color"]
