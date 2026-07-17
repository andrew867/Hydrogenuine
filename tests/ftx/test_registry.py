"""CT-05 FTX registry tests."""

from __future__ import annotations

import pytest

from hg_core.failures.registry import (
    clear_registry_cache,
    load_registry,
    normalize_reason_code,
    validate_reason_code,
    validate_terminal_event,
)


@pytest.fixture(autouse=True)
def _reset() -> None:
    clear_registry_cache()


def test_ftx_u1_registry_load_and_hash() -> None:
    registry = load_registry()
    assert registry.schema == "reason_codes_v1"
    assert registry.registry_hash.startswith("sha256:")
    assert "refused" in registry.terminal_states


def test_ftx_u2_unregistered_code_refused() -> None:
    result = validate_reason_code("totally.unknown.code")
    assert not result.ok
    assert "unknown_reason_code" in result.reason


def test_ftx_u3_terminal_event_missing_fields() -> None:
    result = validate_terminal_event({"state": "refused"})
    assert not result.ok


def test_legacy_alias_normalizes() -> None:
    assert normalize_reason_code("TER_JAIL_VIOLATION") == "ter.refused.jail_violation"


def test_iam_dynamic_denied_pattern() -> None:
    canonical = normalize_reason_code("denied.unregistered_operator")
    assert canonical == "iam.denied.unregistered_operator"
